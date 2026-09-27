import httpx
import json

job_id = "job_3100e05afc21"
url = f"https://satquery-brain.onrender.com/api/v1/jobs/{job_id}"

resp = httpx.get(url)
with open("job_result.json", "w") as f:
    f.write(resp.text)
