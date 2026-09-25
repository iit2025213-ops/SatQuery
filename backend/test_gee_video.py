import asyncio
import os
import httpx
from dotenv import load_dotenv
import pathlib

# Load environment variables
env_path = pathlib.Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path)

from app.gee.connector import GEEConnector
from app.storage.cloudinary_client import CloudinaryClient

async def main():
    print("🌍 Initializing GEE Connector & Cloudinary...")
    
    key_path = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH")
    project_id = os.environ.get("GEE_PROJECT_ID")
    
    if not key_path or not project_id:
        print("❌ Error: GEE credentials missing from .env")
        return
        
    connector = GEEConnector(key_path, project_id)
    
    # Initialize Cloudinary client
    cloudinary_client = CloudinaryClient(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET")
    )
    
    await connector.authenticate()
    print("✅ Authenticated with Google Earth Engine")
    
    # Bengaluru Lake Polygon
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
    
    print("⏳ Requesting a 3-year timelapse video for random polygon (Bengaluru Lake)...")
    
    try:
        timeline_data = await connector.get_timeline_data(aoi_geojson, months=36)
        
        video_url = timeline_data.get("video_url")
        if video_url:
            print("\n🎉 SUCCESS! GEE Video generated successfully!")
            print(f"🎬 Temporary GEE URL: {video_url}")
            
            print("\n📥 Downloading video from GEE...")
            async with httpx.AsyncClient() as http_client:
                vid_resp = await http_client.get(video_url, timeout=45.0)
                
                if vid_resp.status_code == 200:
                    print("☁️ Uploading to Cloudinary for permanent storage...")
                    vid_upload_res = await cloudinary_client.upload_bytes(
                        vid_resp.content, 
                        "timeline_animation", 
                        "test_terminal_job", 
                        "timelapse.gif"
                    )
                    cloudinary_vid_url = vid_upload_res["url"]
                    print("\n🚀 FINAL CLOUDINARY URL (Permanent):")
                    print(cloudinary_vid_url)
                else:
                    print(f"❌ Failed to download from GEE. Status Code: {vid_resp.status_code}")
        else:
            print("\n⚠️ Operation completed, but no video_url was returned.")
            
    except Exception as e:
        print(f"\n❌ Error generating video: {e}")

if __name__ == "__main__":
    asyncio.run(main())
