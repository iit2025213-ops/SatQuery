"""Quick check: latest gee_assets and jobs from Supabase"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url  = os.environ["SUPABASE_URL"]
key  = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
sb   = create_client(url, key)

# --- Latest 5 jobs ---
print("\n=== Latest Jobs ===")
jobs = sb.table("jobs").select("job_id,status,final_answer,created_at").order("created_at", desc=True).limit(5).execute()
for j in jobs.data:
    ans = (j.get("final_answer") or "")[:120]
    print(f"  [{j['status']}] {j['job_id'][:8]}... | {j['created_at'][:19]} | {ans}")

# --- Latest 5 gee_assets ---
print("\n=== Latest GEE Assets ===")
assets = sb.table("gee_assets").select("gee_asset_id,source,cloudinary_url,status,created_at").order("created_at", desc=True).limit(5).execute()
for a in assets.data:
    url_short = (a.get("cloudinary_url") or "None")[:80]
    print(f"  [{a['status']}] {a['source']} | {a['created_at'][:19]} | {url_short}")

print()
