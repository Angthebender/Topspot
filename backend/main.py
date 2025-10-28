from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

# Debug: Print environment variables (remove sensitive data)
print("=== ENVIRONMENT VARIABLES ===")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")


# Initialize Supabase client
try:
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Supabase client created successfully")
except Exception as e:
    print(f"❌ Error creating Supabase client: {e}")
    supabase = None

@app.route("/rooftops", methods=["GET"])
def get_rooftops():
    """Get all rooftops with their images"""
    print("\n=== GET ROOFTOPS REQUEST ===")

    try:
        # 1. Query rooftops table
        response = supabase.table("rooftops").select("*").execute()
        rooftops = response.data or []

        rooftops_with_images = []

        # 2. For each rooftop, try fetching its images
        for rooftop in rooftops:
            folder = rooftop.get("name", "").lower().replace(" ", "_")
            try:
                files = supabase.storage.from_("rooftops").list(folder)
                # files is already a list, NOT a response dict
            except Exception as e:
                print(f"Storage list failed for {folder}: {e}")   # <-- will show real error
                files = []

            urls = []
            print(f"Found {len(files)} files in folder '{folder}'")
            for f in files:
                # f is a dict with keys: name, id, updated_at, created_at …
                key = f"{folder}/{f['name']}"
                print(f"Fetching public URL for key: {key}")
                urls.append(
                    supabase.storage.from_("rooftops").get_public_url(key)
                )

            rooftop["images"] = urls
            rooftops_with_images.append(rooftop)
            
        return jsonify({"success": True, "data": rooftops_with_images}), 200

    except Exception as e:
        print(f"❌ Exception in get_rooftops: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_rooftops():
     # ---- 1.  log that we entered this function ----
    print("\n=== SEARCH ROOFTOPS REQUEST ===")
    
    
    # ---- 2.  safety-check: is Supabase client ready? ----
    #         if not, stop early and tell the app “database broken”
    if not supabase:
        print("❌ Supabase client not initialized")
        return jsonify({"success": False, "error": "Database not connected"}), 500
    
    # ---- 3.  read what the user typed in the search box ----
    #         it arrives as  /search?q=sky  ← “sky” is the query
    query = request.args.get('q', '').strip()
    print(f"🔍 Search query: '{query}'")
    
    # ---- 4.  if user sent empty box, just give back *all* rooftops ----
    if not query:
        print("⚠️  Empty search query, returning all rooftops")
        return get_rooftops()
    
    # ---- 5.  try the real search ----
    try:
        # Search in name and location fields
        print("🔄 Performing search query...")
        # ask Supabase:
        #   SELECT * FROM rooftops
        #   WHERE name    ILIKE '%sky%'
        #      OR location ILIKE '%sky%';
        response = supabase.table("rooftops").select("*").or_(
            f"name.ilike.%{query}%,location.ilike.%{query}%"
        ).execute()
        # how many did we get?
        print(f"📏 Search results: {len(response.data) if response.data else 0}")
        # if Supabase itself complained, tell the frontend
        # hasattr is a built-in function to check if an object has a certain attribute so liek if the response has any error
        if hasattr(response, 'error') and response.error:
            print(f"❌ Supabase error: {response.error}")
            return jsonify({"success": False, "error": str(response.error)}), 500
        # grab rows (empty list if nothing)
        rooftops = response.data or []
        print(f"✅ Found {len(rooftops)} rooftops matching '{query}'")
        rooftops_with_images = []
        #trying to get pictures
        for rooftop in rooftops:
            folder = rooftop.get("name", "").lower().replace(" ", "_")
            try:
                files = supabase.storage.from_("rooftops").list(folder)
                # files is already a list, NOT a response dict
            except Exception as e:
                print(f"Storage list failed for {folder}: {e}")   # <-- will show real error
                files = []

            urls = []
            print(f"Found {len(files)} files in folder '{folder}'")
            for f in files:
                # f is a dict with keys: name, id, updated_at, created_at …
                key = f"{folder}/{f['name']}"
                print(f"Fetching public URL for key: {key}")
                urls.append(
                    supabase.storage.from_("rooftops").get_public_url(key)
                )

            rooftop["images"] = urls
            rooftops_with_images.append(rooftop)
        
        # ---- 6.  send the nice answer back to the phone ----
        return jsonify({"success": True, "data": rooftops_with_images}), 200
    # ---- 7.  if *any* random error happens, log it and reply 500 ----    
    except Exception as e:
        print(f"❌ Exception in search_rooftops: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
 
@app.route("/rooftops/nearby", methods=["GET"])
def get_nearby_rooftops():
    """Get rooftops sorted by distance from given coordinates"""
    print("\n=== GET NEARBY ROOFTOPS REQUEST ===")
    
    if not supabase:
        print("❌ Supabase client not initialized")
        return jsonify({"success": False, "error": "Database not connected"}), 500
    
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        limit = request.args.get('limit', 20, type=int)
        
        print(f"📍 User location: lat={lat}, lng={lng}")
        print(f"📏 Limit: {limit}")
        
        if lat is None or lng is None:
            print("❌ Missing latitude or longitude")
            return jsonify({"success": False, "error": "Latitude and longitude are required"}), 400
        
        # Note: This assumes your rooftops table has latitude and longitude columns
        # If not, you'll need to add them to your database schema
        
        # Using PostGIS distance calculation (if you have the extension)
        # This is a more advanced query - for now, we'll return all rooftops
        # and you can implement distance calculation on the frontend
        
        print("🔄 Querying rooftops...")
        response = supabase.table("rooftops").select("*").limit(limit).execute()
        
        if hasattr(response, 'error') and response.error:
            print(f"❌ Supabase error: {response.error}")
            return jsonify({"success": False, "error": str(response.error)}), 500
        
        rooftops = response.data or []
        
        # TODO: Calculate actual distances and sort
        # For now, just return the rooftops as-is
        print(f"✅ Found {len(rooftops)} rooftops")
        
        return jsonify({
            "success": True, 
            "data": rooftops,
            "user_location": {"lat": lat, "lng": lng},
            "note": "Distance calculation not yet implemented - showing all rooftops"
        }), 200
        
    except Exception as e:
        print(f"❌ Exception in get_nearby_rooftops: {e}")
        return jsonify({"success": False, "error": str(e)}), 500




if __name__ == "__main__":
    
    app.run(debug=True, host="0.0.0.0", port=5000)