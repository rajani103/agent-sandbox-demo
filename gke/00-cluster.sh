#!/usr/bin/env bash
# Run the NIGHT BEFORE. Autopilot cluster creation takes several minutes.
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:=asia-south1}"            # confirm Agent Sandbox is available here
: "${CLUSTER:=agent-demo}"
: "${CLUSTER_VERSION:=1.36.3-gke.1767000}"   # docs minimum; check for a newer one on the day

gcloud config set project "$PROJECT_ID"

gcloud beta container clusters create-auto "$CLUSTER" \
  --location="$REGION" \
  --cluster-version="$CLUSTER_VERSION" \
  --enable-agent-sandbox

gcloud container clusters get-credentials "$CLUSTER" --location="$REGION"

echo "Agent Sandbox enabled?"
gcloud beta container clusters describe "$CLUSTER" --location="$REGION" \
  --format="value(addonsConfig.agentSandboxConfig.enabled)"

kubectl create namespace agents --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f "$(dirname "$0")/10-template.yaml"
kubectl apply -f "$(dirname "$0")/11-warmpool.yaml"

echo "Waiting for the warm pool..."
kubectl get sandboxwarmpool,sandbox,pod -n agents
