import os
from flask import Flask, jsonify
from supabase import create_client
from dotenv import load_dotenv

# Load env vars
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Initialize Flask & Supabase
app = Flask(__name__)
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


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


if __name__ == "__main__":
    app.run(debug=True)
