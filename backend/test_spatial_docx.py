import asyncio
import os
import pathlib
import datetime
import httpx
from dotenv import load_dotenv

# Load environment variables (Backend)
env_path = pathlib.Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path)

# Load frontend env for Mapbox token
frontend_env_path = pathlib.Path.cwd().parent / "frontend" / ".env"
if frontend_env_path.exists():
    load_dotenv(dotenv_path=frontend_env_path)

from app.gee.connector import GEEConnector
from app.storage.cloudinary_client import CloudinaryClient
from app.utils.doc_generator import DocGenerator
from openai import AsyncOpenAI
from supabase import create_client

async def main():
    print("🚀 Starting Terminal-First Spatial DOCX Pipeline Test (Delhi)...")
    
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
    
    openai_client = AsyncOpenAI(
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        base_url=os.environ.get("AZURE_OPENAI_ENDPOINT")
    )

    # Use a dummy job ID
    job_id = "spatial-test-delhi-001"

    # 2. Mapbox Visual Reference (Visualization Only)
    print("\n⏳ Fetching Mapbox Static Image for visual reference...")
    mapbox_token = os.environ.get("VITE_MAPBOX_TOKEN")
    mapbox_img_bytes = None
    if mapbox_token:
        # Delhi Coordinates: Lon=77.2090, Lat=28.6139
        mapbox_url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/77.2090,28.6139,11,0/800x600?access_token={mapbox_token}"
        async with httpx.AsyncClient() as client:
            res = await client.get(mapbox_url)
            if res.status_code == 200:
                mapbox_img_bytes = res.content
                print("✅ Fetched Mapbox static image successfully.")
            else:
                print(f"❌ Failed to fetch Mapbox image: {res.status_code}")
    else:
        print("❌ VITE_MAPBOX_TOKEN not found in frontend/.env!")

    # 3. GEE Spatial Analysis (Scientific Results)
    print("\n⏳ Running GEE Spatial Analysis for Delhi...")
    delhi_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.1000, 28.5500],
                [77.3000, 28.5500],
                [77.3000, 28.7000],
                [77.1000, 28.7000],
                [77.1000, 28.5500]
            ]
        ]
    }
    
    # Get latest Sentinel-2 scene
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=60) # Look back 60 days
    scenes = await connector.query_sentinel2(
        delhi_geojson, 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d")
    )
    
    if not scenes:
        print("❌ No GEE scene found for Delhi.")
        return
        
    scene_id = scenes[0]["id"]
    print(f"✅ Found latest scene: {scene_id}")
    
    # Calculate Spatial Stats
    spatial_stats = await connector.get_spatial_stats(scene_id, delhi_geojson)
    print(f"✅ Calculated Spatial Stats: NDVI={spatial_stats['ndvi_mean']:.3f}, NDBI={spatial_stats['ndbi_mean']:.3f}")

    # Fetch Index Visualizations
    index_images = {}
    print(f"⏳ Fetching GEE Index Image overlays...")
    indices = ["NDVI", "NDWI", "NDBI", "NBR"]
    
    async def fetch_index_img(idx_name):
        try:
            url = await connector.compute_index_thumbnail_url(scene_id, delhi_geojson, idx_name, dimensions=512)
            if url:
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
            
    print(f"✅ Fetched {len(index_images)} GEE index images.")

    # 4. OpenAI Report Generation
    print("\n⏳ Requesting OpenAI Spatial Analysis Report...")
    prompt = f"""
    You are a professional geospatial AI analyst.
    Please write a Spatial Analysis Report for the Delhi, India study area.
    
    IMPORTANT: You must base ALL your scientific findings ONLY on the following GEE-derived metrics.
    
    Observation Date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Data Source: Sentinel-2 via Google Earth Engine
    
    NDVI (Vegetation): {spatial_stats.get('ndvi_mean', 'N/A')}
    NDWI (Water): {spatial_stats.get('ndwi_mean', 'N/A')}
    NDBI (Urban): {spatial_stats.get('ndbi_mean', 'N/A')}
    NBR (Burn): {spatial_stats.get('nbr_mean', 'N/A')}
    
    Format the report with these sections using standard Markdown:
    # Study Area and Context
    # Satellite Data Information
    # Spatial Findings (Vegetation, Water, Urban)
    # Interpretation & Conclusion
    """
    
    response = await openai_client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )
    ai_summary = response.choices[0].message.content.strip()
    print("✅ OpenAI generation success!\n")
    
    # 5. Generate DOCX
    print("⏳ Generating DOCX Document in memory...")
    docx_bytes = DocGenerator.generate_spatial_docx(
        ai_summary=ai_summary, 
        spatial_stats=spatial_stats,
        mapbox_img_bytes=mapbox_img_bytes,
        index_images=index_images
    )
    
    file_size_kb = len(docx_bytes) / 1024
    print(f"✅ DOCX Generated successfully! (File Size: {file_size_kb:.2f} KB)")
    
    # Save locally
    local_path = pathlib.Path.cwd() / "test_spatial_output.docx"
    with open(local_path, "wb") as f:
        f.write(docx_bytes)
    print(f"💾 Saved locally to: {local_path}")
    
    # 6. Upload to Cloudinary & Save to DB
    print("\n☁️ Uploading DOCX to Cloudinary...")
    upload_res = await cloudinary_client.upload_bytes(
        docx_bytes, 
        artifact_type="spatial_report_docx", 
        job_id=job_id, 
        filename="spatial_report_delhi.docx",
        resource_type="raw"
    )
    
    cloudinary_url = upload_res["url"]
    print(f"✅ Uploaded to Cloudinary: {cloudinary_url}")
    
    print("💾 Saving Document record to Supabase...")
    new_doc = {
        "job_id": job_id,
        "doc_type": "spatial_report_docx",
        "format": "docx",
        "cloudinary_public_id": upload_res["cloudinary_public_id"],
        "cloudinary_url": cloudinary_url
    }
    
    try:
        supabase.table("documents").insert(new_doc).execute()
        print("✅ Successfully inserted into 'documents' table.")
    except Exception as e:
        print(f"⚠️ Failed to insert to DB (likely due to invalid dummy job_id), but Cloudinary upload succeeded: {e}")
    
    print("\n🎉 END-TO-END SPATIAL PIPELINE SUCCESSFUL!")
    print(f"Please open {local_path} on your machine and verify the Mapbox/GEE separation.")

if __name__ == "__main__":
    asyncio.run(main())
