import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url  = os.environ["SUPABASE_URL"]
key  = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
sb   = create_client(url, key)

res = sb.table("aois").select("area_km2,area_m2,bbox").order("created_at", desc=True).limit(1).execute()
print(res.data)
