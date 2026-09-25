import asyncio
import os
import httpx
from dotenv import load_dotenv
import pathlib
import json

env_path = pathlib.Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path)

async def main():
    print("🔍 Fetching full database schema from Supabase...")
    
    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    # Supabase exposes an OpenAPI spec for the database schema
    openapi_url = f"{sb_url}/rest/v1/"
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(openapi_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch schema: {response.text}")
            return
            
        schema = response.json()
        
        # The schema definitions are inside components.schemas or definitions
        definitions = schema.get("definitions", {})
        
        documents_schema = definitions.get("documents")
        if not documents_schema:
            print("❌ 'documents' table DOES NOT EXIST in this database!")
            # Let's list what tables DO exist
            print("Available tables:")
            for table in definitions.keys():
                print(f" - {table}")
            return
            
        print("✅ Found 'documents' table!")
        properties = documents_schema.get("properties", {})
        print("Columns in 'documents' table:")
        for col_name, details in properties.items():
            col_type = details.get("type", "unknown")
            print(f"  - {col_name} ({col_type})")
            
        print("\nAll done!")

if __name__ == "__main__":
    asyncio.run(main())
