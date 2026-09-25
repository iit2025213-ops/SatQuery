import asyncio
from app.main import supabase_client

async def run():
    res = supabase_client.get_admin_client().table('evidence').select('*').limit(1).execute()
    if res.data:
        print("Columns in evidence:")
        print(list(res.data[0].keys()))
    else:
        print("No data in evidence table.")

if __name__ == "__main__":
    asyncio.run(run())
