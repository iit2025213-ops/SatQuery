import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.gee.connector import GEEConnector

async def test_gee():
    print("🌍 Initializing GEE Connector...")
    connector = GEEConnector(
        service_account_key_path=os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH"),
        project_id=os.environ.get("GEE_PROJECT_ID")
    )
    
    # 1. Authenticate
    success = await connector.authenticate()
    if not success:
        print("❌ Authentication failed. Check your credentials in .env")
        return
        
    print("✅ Authenticated successfully!\n")
    
    # Define an AOI over New Delhi
    aoi = {
        "type": "Polygon",
        "coordinates": [
            [[77.0, 28.5], [77.2, 28.5], [77.2, 28.7], [77.0, 28.7], [77.0, 28.5]]
        ]
    }
    
    print("🛰️ Querying Sentinel-2 Imagery over New Delhi (Jan-Jun 2024)...")
    scenes = await connector.query_sentinel2(
        aoi_geojson=aoi,
        date_start="2024-01-01",
        date_end="2024-06-30",
        cloud_cover_max=10
    )
    
    if not scenes:
        print("❌ No scenes found.")
        return
        
    print(f"✅ Found {len(scenes)} scenes!\n")
    
    # Print details of the first scene
    first_scene = scenes[0]
    print("📸 First Scene Details:")
    for key, value in first_scene.items():
        if key != 'band_wavelengths':
            print(f"  - {key}: {value}")
            
    print("\n🖼️ Getting a thumbnail URL for the first scene (True Color)...")
    
    # We can use the raw Earth Engine API to generate a quick visual thumbnail
    import ee
    
    try:
        # Load the image using its ID
        image = ee.Image(first_scene['id'])
        
        # Apply the same cloud mask we use in our connector
        masked_image = connector.apply_sentinel2_cloud_mask(image)
        
        # Select True Color bands (Red, Green, Blue) -> B4, B3, B2
        rgb_image = masked_image.select(['B4', 'B3', 'B2'])
        
        # Get thumbnail URL (max 1024x1024)
        geom = connector.geojson_to_ee_geometry(aoi)
        
        thumb_url = rgb_image.getThumbURL({
            'min': 0,
            'max': 3000,          # Sentinel-2 surface reflectance max visualization value
            'dimensions': 800,    # 800px width
            'region': geom,
            'format': 'png'
        })
        
        print(f"✅ Success! Click this link to view the satellite image:")
        print(f"\n👉 {thumb_url}\n")
        
    except Exception as e:
        print(f"❌ Failed to generate thumbnail: {e}")

if __name__ == "__main__":
    asyncio.run(test_gee())
