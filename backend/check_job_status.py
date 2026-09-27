import httpx
import sys

job_id = "job_fded9b59deb6"
OUR_BACKEND = "http://localhost:8000"

resp = httpx.post(
    f"{OUR_BACKEND}/api/v1/auth/login",
    json={"email": "avdeshjaiswal735@gmail.com", "password": "12345678"},
)
token = resp.json().get("access_token")

resp = httpx.get(
    f"{OUR_BACKEND}/api/v1/brain/status/{job_id}",
    headers={"Authorization": f"Bearer {token}"}
)
print("FULL RESPONSE:")
print(resp.text)
