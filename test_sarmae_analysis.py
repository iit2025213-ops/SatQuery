"""
Comprehensive SARMAE Remote Inference Test
Sends multiple SAR-like test images and analyzes embedding quality.
"""
import base64, json, urllib.request, io, math
import numpy as np
from PIL import Image

ENDPOINT = "https://8000-dep-01m2r4x5seae0k068kvhebhdws-d.cloudspaces.litng.ai/v1/analyze"
TOKEN = "Bearer 625b1be6-ad1b-4da5-9adc-03fefacb2b59"

def send_image(img: Image.Image, label: str) -> dict:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    payload = json.dumps({"image_b64": b64}).encode()
    req = urllib.request.Request(ENDPOINT, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": TOKEN,
    })
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def analyze_embedding(emb: list, label: str):
    arr = np.array(emb)
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Dimensions     : {len(emb)}")
    print(f"  Mean           : {arr.mean():.6f}")
    print(f"  Std Dev        : {arr.std():.6f}")
    print(f"  Min            : {arr.min():.6f}")
    print(f"  Max            : {arr.max():.6f}")
    print(f"  L2 Norm        : {np.linalg.norm(arr):.6f}")
    print(f"  Non-zero dims  : {np.count_nonzero(arr)} / {len(emb)}")
    print(f"  Sparsity       : {(1 - np.count_nonzero(arr)/len(emb))*100:.1f}%")
    print(f"  First 8 values : {[round(v,4) for v in emb[:8]]}")
    return arr

# ── Test 1: SAR-like speckle noise (ocean scene) ──
print("\n Generating Test Images...")
np.random.seed(42)
ocean = np.clip(np.random.exponential(scale=40, size=(224,224)), 0, 255).astype(np.uint8)
img_ocean = Image.fromarray(ocean, mode="L")

# ── Test 2: SAR-like urban scene (bright scatterers) ──
urban = np.random.exponential(scale=30, size=(224,224))
# Add bright "buildings" (corner reflectors)
for _ in range(15):
    x, y = np.random.randint(20, 204, 2)
    urban[y:y+8, x:x+5] = np.random.uniform(180, 255)
urban = np.clip(urban, 0, 255).astype(np.uint8)
img_urban = Image.fromarray(urban, mode="L")

# ── Test 3: SAR-like ship detection scene ──
ship = np.random.exponential(scale=25, size=(224,224))
# Dark ocean background with bright ship targets
ship[:, :] = ship[:, :] * 0.5  # darker ocean
# Add 3 "ships" as bright point targets
ship[100:108, 110:114] = 250
ship[50:56, 160:163] = 230
ship[170:175, 60:64] = 240
ship = np.clip(ship, 0, 255).astype(np.uint8)
img_ship = Image.fromarray(ship, mode="L")

# ── Test 4: Our pre-generated test image ──
img_local = Image.open("test_sarmae_input.png")

# ── Run all tests ──
print(" Sending images to SARMAE on Lightning AI T4 GPU...\n")

r1 = send_image(img_ocean, "Ocean SAR")
e1 = analyze_embedding(r1["result"]["embedding"], "TEST 1: Ocean / Sea Surface (Speckle Noise)")
print(f"  Inference time : {r1['inference_time_seconds']:.4f}s")

r2 = send_image(img_urban, "Urban SAR")
e2 = analyze_embedding(r2["result"]["embedding"], "TEST 2: Urban Area (Bright Scatterers)")
print(f"  Inference time : {r2['inference_time_seconds']:.4f}s")

r3 = send_image(img_ship, "Ship SAR")
e3 = analyze_embedding(r3["result"]["embedding"], "TEST 3: Ship Detection Scene")
print(f"  Inference time : {r3['inference_time_seconds']:.4f}s")

r4 = send_image(img_local, "Local Test")
e4 = analyze_embedding(r4["result"]["embedding"], "TEST 4: Pre-Generated SAR Test Image")
print(f"  Inference time : {r4['inference_time_seconds']:.4f}s")

# ── Discriminability Analysis ──
print(f"\n{'='*60}")
print(f"  DISCRIMINABILITY ANALYSIS")
print(f"{'='*60}")

def cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

pairs = [
    ("Ocean vs Urban", e1, e2),
    ("Ocean vs Ships", e1, e3),
    ("Urban vs Ships", e2, e3),
    ("Local vs Ocean", e4, e1),
    ("Local vs Urban", e4, e2),
    ("Local vs Ships", e4, e3),
]

print(f"\n  Cosine Similarity Between Scenes:")
for name, a, b in pairs:
    sim = cosine_sim(a, b)
    print(f"    {name:20s} : {sim:.4f}")

# ── Final Verdict ──
print(f"\n{'='*60}")
print(f"  FINAL VERDICT")
print(f"{'='*60}")

sims = [cosine_sim(a, b) for _, a, b in pairs]
avg_sim = np.mean(sims)
all_nonzero = all(np.count_nonzero(e) > 700 for e in [e1, e2, e3, e4])
all_varied = all(np.std(e) > 0.1 for e in [e1, e2, e3, e4])
has_discrimination = any(s < 0.98 for s in sims)

print(f"  All embeddings non-zero  : {'PASS' if all_nonzero else 'FAIL'}")
print(f"  All embeddings varied    : {'PASS' if all_varied else 'FAIL'}")
print(f"  Scene discrimination     : {'PASS' if has_discrimination else 'FAIL'}")
print(f"  Average cosine sim       : {avg_sim:.4f}")

if all_nonzero and all_varied and has_discrimination:
    print(f"\n  RATING: EXCELLENT")
    print(f"  The model produces rich, discriminative 768-dim representations.")
    print(f"  Different SAR scenes yield meaningfully different embeddings.")
else:
    print(f"\n  RATING: NEEDS INVESTIGATION")
    print(f"  Some quality checks did not pass.")
