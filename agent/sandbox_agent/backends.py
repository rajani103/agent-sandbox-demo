"""One function, two places to run code.

    SANDBOX_BACKEND=docker  -> a Docker Sandbox (microVM) on this laptop, via the sbx CLI
    SANDBOX_BACKEND=gke     -> a GKE Agent Sandbox (gVisor pod) claimed from a warm pool

The agent never knows which one it got. That's the point: the limits live in the
platform, not in the agent's code.
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, asdict


@dataclass
class RunResult:
    backend: str
    stdout: str
    stderr: str
    exit_code: int | None
    seconds: float          # total wall time: get sandbox + run + clean up
    sandbox_seconds: float  # time spent just getting a sandbox ready

    def as_dict(self) -> dict:
        return asdict(self)


def run_code(code: str, timeout: int = 60) -> RunResult:
    backend = os.getenv("SANDBOX_BACKEND", "gke").lower()
    if backend == "docker":
        return _run_docker(code, timeout)
    if backend == "gke":
        return _run_gke(code, timeout)
    raise ValueError(f"unknown SANDBOX_BACKEND={backend!r} (use 'docker' or 'gke')")


# --- Docker Sandboxes (laptop) ------------------------------------------------
# Uses ONE long-lived shell sandbox created beforehand with no workspace mount:
#     sbx create --name agent-runner shell
# Code is piped to python3 over stdin, so nothing from the laptop is mounted in.

def _run_docker(code: str, timeout: int) -> RunResult:
    name = os.getenv("DOCKER_SANDBOX", "agent-runner")
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["sbx", "exec", "-i", name, "python3", "-"],
        input=code, capture_output=True, text=True, timeout=timeout,
    )
    elapsed = time.perf_counter() - t0
    return RunResult("docker", proc.stdout, proc.stderr, proc.returncode, elapsed, 0.0)


# --- GKE Agent Sandbox (cluster) ----------------------------------------------
# A fresh sandbox per call, claimed from the warm pool and terminated afterwards.

def _run_gke(code: str, timeout: int) -> RunResult:
    from k8s_agent_sandbox import SandboxClient

    pool = os.getenv("WARM_POOL", "python-sandbox-pool")
    namespace = os.getenv("SANDBOX_NAMESPACE", "agents")

    t0 = time.perf_counter()
    sandbox = SandboxClient().create_sandbox(warmpool=pool, namespace=namespace)
    t_ready = time.perf_counter()
    try:
        sandbox.files.write("run.py", code)
        result = sandbox.commands.run("python3 run.py")
    finally:
        sandbox.terminate()
    t_end = time.perf_counter()

    return RunResult(
        backend="gke",
        stdout=getattr(result, "stdout", "") or "",
        stderr=getattr(result, "stderr", "") or "",
        exit_code=getattr(result, "exit_code", None),
        seconds=t_end - t0,
        sandbox_seconds=t_ready - t0,
    )
