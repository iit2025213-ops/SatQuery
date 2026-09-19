import requests

url = "http://localhost:8000/api/v1/auth/register"
payload = {
    "email": "test@test.com",
    "password": "short",
    "display_name": "test"
}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.json())
