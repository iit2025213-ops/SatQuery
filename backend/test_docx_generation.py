import asyncio
import os
import pathlib
from dotenv import load_dotenv

# Load environment variables
env_path = pathlib.Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path)

from app.gee.connector import GEEConnector
from app.storage.cloudinary_client import CloudinaryClient
from app.utils.doc_generator import DocGenerator
from openai import AsyncOpenAI
from supabase import create_client

async def main():
    print("🚀 Starting Terminal-First DOCX Pipeline Test...\n")
    
    # 1. Initialize Clients
    key_path = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH")
    project_id = os.environ.get("GEE_PROJECT_ID")
    connector = GEEConnector(key_path, project_id)
    await connector.authenticate()
    print("✅ Authenticated with GEE")
    
    cloudinary_client = CloudinaryClient(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET")
    )
    
    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(sb_url, sb_key)
    
    # Assuming Azure OpenAI from the `.env` configuration we fixed earlier
    openai_client = AsyncOpenAI(
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        base_url=os.environ.get("AZURE_OPENAI_ENDPOINT")
    )
    
    # Create a mock job so we have a valid job_id for the database
    job_res = supabase.table("jobs").select("*").limit(1).execute()
    job_id = job_res.data[0]["job_id"] if job_res.data else "test-job-id"
    user_id = job_res.data[0]["user_id"] if job_res.data else "test-user-id"

    # 2. Run GEE Pipeline
    aoi_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.6150, 12.9800],
                [77.6250, 12.9800],
                [77.6250, 12.9900],
                [77.6150, 12.9900],
                [77.6150, 12.9800]
            ]
        ]
    }
    
    print("⏳ Running GEE Timeline Analysis (36 months)...")
    timeline_data = await connector.get_timeline_data(aoi_geojson, months=36)
    if not timeline_data:
        print("❌ GEE returned no data. Check AOI.")
        return
        
    print(f"✅ GEE analysis success! Extracted {len(timeline_data.get('frames', []))} frames.")
    
    # 3. Generate OpenAI Summary
    print("⏳ Requesting OpenAI Vision Analysis...")
    content = [{"type": "text", "text": "You are a geospatial AI analyst. Provide a professional analysis of the temporal data provided."}]
    
    for idx, frame in enumerate(timeline_data["frames"]):
        stats_text = (
            f"Date: {frame['date']} | "
            f"NDVI: {frame.get('ndvi_mean', 'N/A')} | "
            f"NDWI: {frame.get('ndwi_mean', 'N/A')} | "
            f"NDBI: {frame.get('ndbi_mean', 'N/A')} | "
            f"NBR: {frame.get('nbr_mean', 'N/A')}"
        )
        content.append({"type": "text", "text": stats_text})
        
    response = await openai_client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": content}],
        max_tokens=1000
    )
    ai_summary = response.choices[0].message.content.strip()
    print("✅ OpenAI generation success!\n")
    
    # 3.5 Fetch Index Images for embedding
    index_images = {}
    latest_frame = timeline_data["frames"][-1] if timeline_data.get("frames") else None
    scene_id = latest_frame.get("scene_id") if latest_frame else None
    
    if scene_id:
        print(f"⏳ Fetching Index Image overlays for latest scene ({scene_id})...")
        indices = ["NDVI", "NDWI", "NDBI", "NBR"]
        
        async def fetch_index_img(idx_name):
            try:
                url = await connector.compute_index_thumbnail_url(scene_id, aoi_geojson, idx_name, dimensions=512)
                if url:
                    import httpx
                    async with httpx.AsyncClient() as http_client:
                        resp = await http_client.get(url, timeout=30.0)
                        if resp.status_code == 200:
                            return idx_name, resp.content
            except Exception as e:
                print(f"Failed to fetch {idx_name}: {e}")
            return idx_name, None
            
        tasks = [fetch_index_img(idx) for idx in indices]
        results = await asyncio.gather(*tasks)
        for idx_name, img_bytes in results:
            if img_bytes:
                index_images[idx_name] = img_bytes
                
        print(f"✅ Fetched {len(index_images)} index images to embed in the DOCX!\n")
    
    # 4. Generate DOCX
    print("⏳ Generating DOCX Document in memory...")
    docx_bytes = DocGenerator.generate_timeline_docx(
        ai_summary=ai_summary, 
        timeline_data=timeline_data, 
        video_url=timeline_data.get("video_url"),
        index_images=index_images
    )
    
    file_size_kb = len(docx_bytes) / 1024
    print(f"✅ DOCX Generated successfully! (File Size: {file_size_kb:.2f} KB)")
    
    # Save locally for verification
    local_path = pathlib.Path.cwd() / "test_output.docx"
    with open(local_path, "wb") as f:
        f.write(docx_bytes)
    print(f"💾 Saved locally to: {local_path}")
    
    # 5. Upload to Cloudinary
    print("☁️ Uploading DOCX to Cloudinary...")
    upload_res = await cloudinary_client.upload_bytes(
        docx_bytes, 
        artifact_type="timeline_report_docx", 
        job_id=job_id, 
        filename="temporal_report.docx",
        resource_type="raw"
    )
    
    cloudinary_url = upload_res["url"]
    print(f"✅ Uploaded to Cloudinary: {cloudinary_url}")
    
    # 6. Save to Supabase
    print("💾 Saving Document record to Supabase...")
    new_doc = {
        "job_id": job_id,
        "doc_type": "timeline_report_docx",
        "format": "docx",
        "cloudinary_public_id": upload_res["cloudinary_public_id"],
        "cloudinary_url": cloudinary_url
    }
    
    supabase.table("documents").insert(new_doc).execute()
    print("✅ Successfully inserted into 'documents' table.")
    
    print("\n🎉 END-TO-END PIPELINE SUCCESSFUL!")
    print(f"Please open {local_path} on your machine and verify its contents.")

if __name__ == "__main__":
    asyncio.run(main())
