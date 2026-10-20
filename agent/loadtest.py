"""N agent sessions ask GKE Agent Sandbox for a sandbox at the same moment.

    python loadtest.py --concurrency 20

With a warm pool of 5, expect two groups: fast claims (warm) and a slower
tail (pool ran dry, pods started from cold). Prints p50/p95/max and saves
loadtest.csv + loadtest.png for slide 11.

Run `kubectl get sandboxwarmpool,sandbox -n agents -w` in another pane to
show the pool draining and refilling while this runs.
"""
import argparse
import csv
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from k8s_agent_sandbox import SandboxClient

POOL = os.getenv("WARM_POOL", "python-sandbox-pool")
NAMESPACE = os.getenv("SANDBOX_NAMESPACE", "agents")


def one_session(i: int, start_at: float) -> dict:
    while time.perf_counter() < start_at:      # line everyone up on the same instant
        time.sleep(0.001)
    t0 = time.perf_counter()
    sandbox = SandboxClient().create_sandbox(warmpool=POOL, namespace=NAMESPACE)
    t_ready = time.perf_counter()
    try:
        out = sandbox.commands.run("echo ok").stdout.strip()
    finally:
        sandbox.terminate()
    t_done = time.perf_counter()
    return {"session": i, "ready_s": round(t_ready - t0, 3),
            "total_s": round(t_done - t0, 3), "output": out}


def pct(values, p):
    values = sorted(values)
    k = max(0, min(len(values) - 1, round(p / 100 * (len(values) - 1))))
    return values[k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=20)
    args = ap.parse_args()

    start_at = time.perf_counter() + 1.0
    rows = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = [ex.submit(one_session, i, start_at) for i in range(args.concurrency)]
        for f in as_completed(futures):
            try:
                row = f.result()
                rows.append(row)
                print(f"session {row['session']:>2}: ready in {row['ready_s']:.2f}s")
            except Exception as e:  # keep going so one failure doesn't kill the demo
                print("session failed:", type(e).__name__, e)

    if not rows:
        raise SystemExit("no successful sessions")

    ready = [r["ready_s"] for r in rows]
    print(f"\n{len(rows)}/{args.concurrency} sessions OK   "
          f"p50={statistics.median(ready):.2f}s  p95={pct(ready, 95):.2f}s  max={max(ready):.2f}s")

    with open("loadtest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["ready_s"]))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ordered = sorted(ready)
        fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
        ax.bar(range(1, len(ordered) + 1), ordered, color="#14a39a")
        ax.axhline(statistics.median(ready), color="#f5b800", linestyle="--", label="p50")
        ax.set_xlabel("Agent session (sorted by wait)")
        ax.set_ylabel("Seconds until sandbox ready")
        ax.set_title(f"{len(rows)} concurrent sandbox claims, warm pool of {os.getenv('POOL_SIZE', '5')}")
        ax.legend()
        fig.tight_layout()
        fig.savefig("loadtest.png")
        print("saved loadtest.csv and loadtest.png")
    except ImportError:
        print("saved loadtest.csv (install matplotlib for the chart)")


if __name__ == "__main__":
    main()
