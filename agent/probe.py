"""Ask the sandbox what it is. Works on both backends:

    SANDBOX_BACKEND=docker python probe.py
    SANDBOX_BACKEND=gke    python probe.py

Shows: kernel, first kernel log lines (gVisor prints its own), whether a
Kubernetes service account token is mounted, and whether egress works.
"""
import os

from sandbox_agent.backends import run_code

PROBE = r'''
import os, subprocess, urllib.request

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip() or "(no output)"

print("== kernel ==")
print(sh("uname -a"))
print("\n== kernel log (first lines) ==")
print(sh("dmesg 2>&1 | head -n 5"))
print("\n== kubernetes service account token ==")
sa = "/var/run/secrets/kubernetes.io/serviceaccount"
print("PRESENT" if os.path.exists(sa) else "none mounted")
print("\n== egress to https://example.com ==")
try:
    with urllib.request.urlopen("https://example.com", timeout=5) as r:
        print("ALLOWED, HTTP", r.status)
except Exception as e:
    print("BLOCKED:", type(e).__name__, str(e)[:120])
'''

if __name__ == "__main__":
    res = run_code(PROBE, timeout=90)
    print(f"[backend={res.backend}  total={res.seconds:.2f}s  sandbox_ready={res.sandbox_seconds:.2f}s]\n")
    print(res.stdout)
    if res.stderr.strip():
        print("--- stderr ---")
        print(res.stderr)
