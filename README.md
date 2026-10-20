# Sandbox demo kit: "Your Agent Just Ran rm -rf"

By Rajani Ekunde and Rishi Mondal.

One Gemini agent, one tool (`run_code`), two places to run that code:
a Docker Sandbox (microVM) on the laptop, or GKE Agent Sandbox (gVisor) on the cluster.
Switch with one setting: `SANDBOX_BACKEND=docker|gke`.

> Not yet run end to end. Everything here is written from the Docker and GKE docs.
> Do the "Verify in rehearsal" list below in your first dry run.

## What's in here

| Path | What it is |
| --- | --- |
| `todo-api/` | Small FastAPI app with 4 tests. Act 1's task: move `storage.py` to SQLite. |
| `gke/00-cluster.sh` | Creates the Autopilot cluster with Agent Sandbox, the template and the warm pool |
| `gke/10-template.yaml` | SandboxTemplate with everything the admission policy requires |
| `gke/11-warmpool.yaml` | Warm pool of 5 |
| `gke/12-claim.yaml` | A manual SandboxClaim, to show the object model |
| `gke/20-privileged-template.yaml` | Same template plus `privileged: true`. Should be rejected |
| `gke/30-egress-deny.yaml` | NetworkPolicy: sandboxes can only reach DNS |
| `gke/99-cleanup.sh` | Deletes the cluster after the talk |
| `agent/sandbox_agent/` | The ADK agent and the two backends |
| `agent/probe.py` | Asks a sandbox what it is: kernel, kernel log, SA token, egress |
| `agent/loadtest.py` | 20 sessions claim sandboxes at once; prints p50/p95, saves a chart |

## Setup (night before)

```bash
# Laptop (Rajani)
brew install docker/tap/sbx            # Windows: winget install Docker.sbx
sbx login
cd todo-api && git init && git add . && git commit -m "start" && cd ..
sbx create --name agent-runner shell   # no path = nothing from the laptop is mounted

# Cluster (Rishi)
export PROJECT_ID=your-project REGION=asia-south1
bash gke/00-cluster.sh

# Agent (both)
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp sandbox_agent/.env.example sandbox_agent/.env   # add your Gemini key
python probe.py                                    # smoke test on GKE
SANDBOX_BACKEND=docker python probe.py             # smoke test on Docker
```

## On stage

### Part 1: Docker Sandboxes (Rajani, ~3 min)

```bash
cd todo-api
sbx run --clone --name todo claude     # agent works on a private clone
#   ask: "Move storage.py to SQLite, keep the same functions, make pytest pass."
sbx policy ls                          # deny by default; show the allowlist
sbx policy allow network pypi.org      # only if pip install was blocked
sbx policy allow network files.pythonhosted.org
git status                             # on the laptop: clean, the agent used a clone
sbx rm todo
```

### Part 2: One agent, two places (Rishi, ~4 min)

```bash
cd agent
SANDBOX_BACKEND=docker python probe.py   # microVM: its own kernel
python probe.py                          # GKE: gVisor's own kernel log, no SA token
adk web                                  # open http://127.0.0.1:8000
#   ask: "Generate 10,000 fake orders across 5 regions with a fixed seed,
#         and give me revenue by region, top 3."
```
In the observer pane: `kubectl get sandboxwarmpool,sandbox -n agents -w`

Then flip `SANDBOX_BACKEND=docker` in `.env`, restart `adk web`, and ask the same question.
Same agent, same answer, different wall around it.

### Part 3: Load test (Rishi, ~2 min)

```bash
python loadtest.py --concurrency 20      # pool of 5: watch it drain and refill
```
Put `loadtest.png` and the p50/p95 on slide 11.

### Part 4: Guardrails (both, ~2 min)

```bash
kubectl apply -f ../gke/20-privileged-template.yaml
kubectl get events -n agents --sort-by=.lastTimestamp | tail   # the rejection
python probe.py                          # egress: ALLOWED
kubectl apply -f ../gke/30-egress-deny.yaml
python probe.py                          # egress: BLOCKED. The agent didn't change.
kubectl delete -f ../gke/20-privileged-template.yaml
```

## Verify in rehearsal

- [ ] `sbx exec -i agent-runner python3 -` works, and the shell image has `python3`. If not, recreate with `-t python:3.12-slim`
- [ ] `sbx run --clone` from `todo-api/` works and `git status` stays clean on the laptop
- [ ] Whether `pip install` is blocked by default; which hosts you need to allow
- [ ] Agent Sandbox is available in your region and the cluster version is new enough
- [ ] Whether the Python SDK needs the agent-sandbox router installed on GKE (`SandboxClient()` connects through a `kubectl port-forward` tunnel by default)
- [ ] `result.stderr` and `result.exit_code` field names in `k8s-agent-sandbox`; adjust `backends.py` if they differ
- [ ] Sandbox pods actually carry the `app: agent-sandbox` label (`kubectl get pods -n agents --show-labels`); if not, fix the NetworkPolicy selector
- [ ] Where the privileged rejection shows up: on `kubectl apply`, in events, or in the warm pool status
- [ ] What happens when the warm pool is empty: a cold start, or an error? `loadtest.py` will tell you
- [ ] Record every part as video in case the Wi-Fi fails

After the talk: `bash gke/99-cleanup.sh` and `sbx rm agent-runner`.

## Sources

- Docker Sandboxes: https://docs.docker.com/ai/sandboxes/ and CLI reference https://docs.docker.com/reference/cli/sbx/
- GKE, enable Agent Sandbox: https://docs.cloud.google.com/kubernetes-engine/docs/how-to/how-install-agent-sandbox
- agent-sandbox Python SDK: https://agent-sandbox.sigs.k8s.io/docs/getting_started/python-sdk-quickstart/
- ADK code interpreter example: https://agent-sandbox.sigs.k8s.io/docs/use-cases/examples/code-interpreter-agent-on-adk/
