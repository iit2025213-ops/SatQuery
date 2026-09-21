import asyncio
from app.models.terramind.adapter import TerraMindAdapter

async def main():
    adapter = TerraMindAdapter()
    res = await adapter.predict({
        "asset_uri": "https://raw.githubusercontent.com/rasterio/rasterio/master/tests/data/byte.tif",
        "task": "segmentation"
    })
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
