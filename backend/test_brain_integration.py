"""
test_brain_integration.py
─────────────────────────
Tests the SatQuery ↔ AI Brain (Render) integration.

Strategy: Skip the blocking /api/v1/brain proxy. Instead:
  1. Login to get a JWT
  2. Submit directly to Brain → get job_id
  3. Poll Brain directly until complete
  4. Validate result schema

This avoids our backend's long-running endpoint during testing.

Usage:
  python test_brain_integration.py --email YOUR_EMAIL --password YOUR_PASSWORD
"""

import sys
import json
import time
import argparse
import httpx

# ── Config ────────────────────────────────────────────────────────────────────
OUR_BACKEND   = "http://localhost:8000"
BRAIN_URL     = "https://query-brain.onrender.com"

DEFAULT_EMAIL    = ""
DEFAULT_PASSWORD = ""

LOGIN_TIMEOUT  = 60    # seconds for local auth
BRAIN_TIMEOUT  = 30    # seconds per single httpx call to Render
POLL_TIMEOUT   = 900   # total wait seconds for a job (15 min)
POLL_INTERVAL  = 5     # seconds between polls

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

# ── Step 1: Login ─────────────────────────────────────────────────────────────
def step_login(email: str, password: str) -> str:
    sep("STEP 1 — Login to SatQuery backend")
    info(f"POST {OUR_BACKEND}/api/v1/auth/login")

    try:
        resp = httpx.post(
            f"{OUR_BACKEND}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=LOGIN_TIMEOUT,
        )
    except httpx.ReadTimeout:
        fail(f"Login timed out after {LOGIN_TIMEOUT}s — is uvicorn running?")
        sys.exit(1)
    except httpx.ConnectError:
        fail(f"Cannot connect to {OUR_BACKEND} — start uvicorn first")
        sys.exit(1)

    if resp.status_code != 200:
        fail(f"Login failed: HTTP {resp.status_code}")
        print(f"  {DIM}{resp.text[:300]}{RESET}")
        sys.exit(1)

    data  = resp.json()
    token = data.get("access_token")
    if not token:
        fail(f"No access_token in response: {data}")
        sys.exit(1)

    ok(f"Logged in   email={email}")
    ok(f"Token       {token[:48]}…")
    return token


# ── Step 2: Submit directly to Brain ─────────────────────────────────────────
def step_submit_to_brain(query: str, assets: list = None) -> str:
    sep(f"STEP 2 — Submit to Brain directly")
    payload = {
        "query":    query,
        "assets":   assets or [],
        "metadata": {},
    }
    info(f"POST {BRAIN_URL}/api/v1/analyze")
    info(f"Query: \"{query[:80]}\"")

    try:
        resp = httpx.post(
            f"{BRAIN_URL}/api/v1/analyze",
            json=payload,
            timeout=BRAIN_TIMEOUT,
        )
    except Exception as e:
        fail(f"Submit failed: {e}")
        sys.exit(1)

    print(f"  Status: {resp.status_code}")
    if resp.status_code != 200:
        fail(f"Brain /analyze returned HTTP {resp.status_code}")
        print(f"  {DIM}{resp.text[:300]}{RESET}")
        sys.exit(1)

    data   = resp.json()
    job_id = data.get("job_id")
    status = data.get("status")

    if not job_id:
        fail(f"No job_id in response: {data}")
        sys.exit(1)

    ok(f"Job accepted — job_id={job_id}  status={status}")
    return job_id


# ── Step 3: Poll Brain until complete ─────────────────────────────────────────
def step_poll_brain(job_id: str) -> dict:
    sep(f"STEP 3 — Poll Brain for job result")
    poll_url = f"{BRAIN_URL}/api/v1/jobs/{job_id}"
    info(f"GET {poll_url}   (every {POLL_INTERVAL}s, max {POLL_TIMEOUT}s)")
    print()

    elapsed = 0
    spinner = ["|", "/", "─", "\\"]
    i = 0

    while elapsed < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        try:
            resp = httpx.get(poll_url, timeout=BRAIN_TIMEOUT)
        except httpx.ReadTimeout:
            warn(f"Poll timed out at elapsed={elapsed}s, retrying…")
            continue
        except Exception as e:
            warn(f"Poll error: {e} — retrying…")
            continue

        if resp.status_code != 200:
            warn(f"Poll returned HTTP {resp.status_code}, retrying…")
            continue

        data       = resp.json()
        job_status = data.get("status", "")

        spin = spinner[i % len(spinner)]
        i += 1
        print(f"\r  {spin}  status={job_status:12s}  elapsed={elapsed:4d}s", end="", flush=True)

        if job_status == "complete":
            print()
            ok(f"Job complete in {elapsed}s")
            return data.get("result") or {}

        if job_status in ("failed", "error", "cancelled"):
            print()
            fail(f"Job ended with status={job_status}")
            print(f"  {DIM}{json.dumps(data, indent=2)[:400]}{RESET}")
            return {}

    print()
    fail(f"Timed out after {POLL_TIMEOUT}s waiting for job {job_id}")
    return {}


# ── Step 4: Validate result ───────────────────────────────────────────────────
def step_validate_result(result: dict, query_label: str):
    sep(f"STEP 4 — Validate result ({query_label})")

    if not result:
        warn("Empty result — cannot validate")
        return

    answer       = result.get("answer", "")
    confidence   = result.get("confidence")
    artifact_ids = result.get("artifact_ids") or []
    evidence     = result.get("evidence") or []
    step_count   = result.get("step_count")

    # Schema checks
    for field, value in [
        ("answer",        bool(answer)),
        ("confidence",    confidence is not None),
        ("artifact_ids",  artifact_ids is not None),
        ("evidence",      evidence is not None),
        ("step_count",    step_count is not None),
        ("status",        bool(result.get("status"))),
    ]:
        if value:
            ok(f"Field present: {field}")
        else:
            warn(f"Field missing: {field}")

    # Print answer preview
    print()
    print(f"  {BOLD}Answer preview:{RESET}")
    preview = answer[:600] + ("…" if len(answer) > 600 else "")
    for line in preview.splitlines():
        print(f"  {DIM}{line}{RESET}")

    if confidence is not None:
        print(f"\n  {DIM}Confidence: {confidence}{RESET}")
    if step_count is not None:
        print(f"  {DIM}Steps taken: {step_count}{RESET}")
    if artifact_ids:
        ok(f"Artifacts: {artifact_ids}")
    if evidence:
        ok(f"Evidence items: {len(evidence)}")
        for ev in evidence[:3]:
            print(f"  {DIM}  • {ev.get('capability','?')} — {ev.get('type','?')} — {ev.get('status','?')}{RESET}")


# ── Step 5: Test our backend brain proxy (quick health check only) ────────────
def step_backend_proxy_health(token: str):
    sep("STEP 5 — Backend /api/v1/brain proxy health check")
    info("Checking server is alive with a GET to /api/v1/auth/me")

    try:
        resp = httpx.get(
            f"{OUR_BACKEND}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code == 200:
            ok(f"Backend alive — user: {resp.json().get('email', 'n/a')}")
        else:
            warn(f"Backend returned HTTP {resp.status_code}")
    except Exception as e:
        warn(f"Backend health check failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SatQuery Brain integration test")
    parser.add_argument("--email",    default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    args = parser.parse_args()

    if not args.email or not args.password:
        print(f"\n{RED}Provide --email and --password{RESET}\n")
        sys.exit(1)

    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}       SatQuery ↔ Brain Integration Test{RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════{RESET}")
    print(f"  Backend : {OUR_BACKEND}")
    print(f"  Brain   : {BRAIN_URL}")
    print(f"  Max wait: {POLL_TIMEOUT}s per job")
    print()

    # Login
    token = step_login(args.email, args.password)

    # Backend health
    step_backend_proxy_health(token)

    # Query 1 — general
    job1   = step_submit_to_brain("What is NDVI and how does it relate to vegetation health monitoring?")
    result1 = step_poll_brain(job1)
    step_validate_result(result1, "NDVI query")

    # Query 2 — geospatial science
    job2   = step_submit_to_brain("What satellite data sources are best for detecting urban heat islands?")
    result2 = step_poll_brain(job2)
    step_validate_result(result2, "Urban heat islands query")

    sep()
    print(f"\n{BOLD}{GREEN}  All steps complete.{RESET}")
    if not result1.get("answer") and not result2.get("answer"):
        warn("No answers received — check Brain logs on Render.")
    print()


if __name__ == "__main__":
    main()
