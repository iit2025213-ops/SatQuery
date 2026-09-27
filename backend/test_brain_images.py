"""
test_brain_images.py
─────────────────────────
Tests the SatQuery ↔ AI Brain (Render) integration WITH IMAGES.

Strategy:
  1. Login to get a JWT
  2. Upload local image files to the backend (Supabase + Cloudinary) -> get asset_ids
  3. Submit to Brain via backend proxy (/api/v1/brain) with asset_ids
  4. Poll backend (/api/v1/brain/status/...) until complete

Usage:
  python test_brain_images.py --email your@email.com --password secret --img1 image1.png --img2 image2.jpg
"""

import sys
import os
import time
import argparse
import httpx

# ── Config ────────────────────────────────────────────────────────────────────
OUR_BACKEND = "http://localhost:8000"
TIMEOUT     = 600

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
DIM    = "\033[2m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✓{RESET}  {msg}")
def fail(msg):  print(f"  {RED}✗{RESET}  {msg}")
def warn(msg):  print(f"  {YELLOW}⚠{RESET}  {msg}")
def info(msg):  print(f"  {CYAN}→{RESET}  {msg}")
def sep(title=""):
    line = "─" * 60
    if title:
        print(f"\n{BOLD}{CYAN}{line}{RESET}")
        print(f"{BOLD}{CYAN}  {title}{RESET}")
        print(f"{BOLD}{CYAN}{line}{RESET}")
    else:
        print(f"{DIM}{line}{RESET}")

# ── 1. Login ──────────────────────────────────────────────────────────────────
def step_login(email: str, password: str) -> str:
    sep("STEP 1 — Login to SatQuery backend")
    info(f"POST {OUR_BACKEND}/api/v1/auth/login")

    resp = httpx.post(
        f"{OUR_BACKEND}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    if resp.status_code != 200:
        fail(f"Login failed: HTTP {resp.status_code}")
        sys.exit(1)

    token = resp.json().get("access_token")
    if not token:
        fail("No access_token returned")
        sys.exit(1)

    ok("Logged in successfully")
    return token

# ── 2. Upload Asset ───────────────────────────────────────────────────────────
def step_upload(filepath: str, token: str) -> str:
    sep(f"STEP 2 — Upload {filepath}")
    
    if not os.path.exists(filepath):
        fail(f"File not found: {filepath}")
        sys.exit(1)

    filename = os.path.basename(filepath)
    info(f"POST {OUR_BACKEND}/api/v1/assets")

    with open(filepath, "rb") as f:
        files = {"file": (filename, f, "image/jpeg")}
        data  = {"modality": "optical"}
        
        resp = httpx.post(
            f"{OUR_BACKEND}/api/v1/assets",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
            timeout=30,
        )

    if resp.status_code != 200:
        fail(f"Upload failed: HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    asset_id = resp.json().get("asset_id")
    file_url = resp.json().get("file_url")
    ok(f"Uploaded! Asset ID: {asset_id}")
    info(f"Cloudinary URL: {file_url}")
    
    return asset_id

# ── 3. Submit to Brain ────────────────────────────────────────────────────────
def step_submit(token: str, query: str, asset_ids: list) -> str:
    sep("STEP 3 — Submit analysis to Brain (via backend)")
    info(f"POST {OUR_BACKEND}/api/v1/brain")
    info(f"Query: \"{query}\"")
    info(f"Assets: {len(asset_ids)}")

    resp = httpx.post(
        f"{OUR_BACKEND}/api/v1/brain",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": query,
            "asset_ids": asset_ids,
            "messages": [],
            "options": {
                "generate_artifacts": True,
                "include_visualizations": True
            }
        },
        timeout=30,
    )
    
    if resp.status_code != 200:
        fail(f"Submit failed: HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    job_id = resp.json().get("brain_job_id")
    ok(f"Job accepted! brain_job_id = {job_id}")
    return job_id

# ── 4. Poll ───────────────────────────────────────────────────────────────────
def step_poll(token: str, job_id: str):
    sep("STEP 4 — Poll for completion")
    poll_url = f"{OUR_BACKEND}/api/v1/brain/status/{job_id}"
    info(f"GET {poll_url}")

    elapsed = 0
    spinner = ["|", "/", "-", "\\"]
    i = 0

    while elapsed < TIMEOUT:
        time.sleep(4)
        elapsed += 4

        try:
            resp = httpx.get(
                poll_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
        except Exception as e:
            warn(f"Poll error: {e}")
            continue
            
        if resp.status_code != 200:
            warn(f"Poll returned HTTP {resp.status_code}")
            continue

        data = resp.json()
        status = data.get("status")

        spin = spinner[i % len(spinner)]
        i += 1
        print(f"\r  {spin}  status={status:12s}  elapsed={elapsed:4d}s", end="", flush=True)

        if status == "complete":
            print()
            ok(f"Job finished in {elapsed}s")
            
            print(f"\n{BOLD}Final Answer:{RESET}")
            print(data.get("reply", ""))
            
            artifacts = data.get("artifact_ids", [])
            if artifacts:
                print(f"\n{BOLD}Artifacts generated:{RESET}")
                for a in artifacts:
                    print(f" - {a}")
            return
            
        elif status in ("failed", "error"):
            print()
            fail("Job failed!")
            print(data.get("error"))
            return

    print()
    fail("Timed out waiting for completion.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--img1", required=True, help="Path to first local image")
    parser.add_argument("--img2", help="Path to second local image (optional)")
    parser.add_argument("--query", default="Can you describe the changes between these images?")
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}       SatQuery Brain - IMAGE Integration Test{RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════{RESET}")

    token = step_login(args.email, args.password)
    
    asset_ids = []
    asset_ids.append(step_upload(args.img1, token))
    if args.img2:
        asset_ids.append(step_upload(args.img2, token))

    job_id = step_submit(token, args.query, asset_ids)
    step_poll(token, job_id)

if __name__ == "__main__":
    main()
