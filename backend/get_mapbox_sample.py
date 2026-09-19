import urllib.request
import os

MAPBOX_TOKEN = "pk.eyJ1Ijoic3VqYWwtMTIzLTEiLCJhIjoiY210dmttNnowMDd3MTJ5c2RibnRtYXNuaCJ9.V7ubP5bbmr1m72hdJ9YLgA"

# Let's get a high-res image of Sabarmati Riverfront, Ahmedabad
# Longitude, Latitude
lon = 72.5714
lat = 23.0315
zoom = 15.0  # Zoom level (0 is whole world, 22 is zoomed into a blade of grass)
width = 800
height = 800

# Mapbox Static Images API URL (using satellite-v9 style)
url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},{zoom},0/{width}x{height}@2x?access_token={MAPBOX_TOKEN}"

output_file = "mapbox_sabarmati.jpg"

print(f"Downloading Mapbox high-res satellite image to {output_file}...")

try:
    urllib.request.urlretrieve(url, output_file)
    print(f"✅ Success! Image saved as: {os.path.abspath(output_file)}")
    print(f"Go to your file explorer and open this file to see the incredible resolution (0.5m/pixel)!")
except Exception as e:
    print(f"❌ Failed to download: {e}")
