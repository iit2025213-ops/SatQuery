import os
import requests
from dotenv import load_dotenv

# Load your .env file
load_dotenv()

# Parse the CLOUDINARY_URL
# Format is usually: cloudinary://API_KEY:API_SECRET@CLOUD_NAME
cloud_url = os.getenv('CLOUDINARY_URL')
if not cloud_url:
    print("CLOUDINARY_URL not found in .env")
    exit()

parts = cloud_url.replace('cloudinary://', '').split('@')
api_key, api_secret = parts[0].split(':')
cloud_name = parts[1]

# Hit the Admin API usage endpoint
url = f"https://{api_key}:{api_secret}@api.cloudinary.com/v1_1/{cloud_name}/usage"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    storage_used_bytes = data['storage']['usage']
    storage_used_mb = storage_used_bytes / (1024 * 1024)
    storage_limit_mb = data['storage']['limit'] / (1024 * 1024)
    
    print(f"Storage Used: {storage_used_mb:.2f} MB")
    print(f"Storage Limit: {storage_limit_mb:.2f} MB")
    print(f"Percentage Used: {data['storage']['used_percent']:.2f}%")
else:
    print("Failed to fetch usage:", response.text)
