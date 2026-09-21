import base64, json, urllib.request

with open("test_sarmae_input.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

payload = json.dumps({"image_b64": b64}).encode()
req = urllib.request.Request(
    "https://8000-dep-01m2r4x5seae0k068kvhebhdws-d.cloudspaces.litng.ai/v1/analyze",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer 625b1be6-ad1b-4da5-9adc-03fefacb2b59"
    }
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
emb = result["result"]["embedding"]
shape = result["result"]["shape"]
print("Status: OK")
print("Model:", result["model"])
print("Shape:", shape)
print("Embedding length:", len(emb))
print("First 5 values:", emb[:5])
print("Inference time:", round(result["inference_time_seconds"], 4), "s")
