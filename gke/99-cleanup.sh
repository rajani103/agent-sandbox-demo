#!/usr/bin/env bash
# Run after the talk so the cluster stops billing.
set -euo pipefail
: "${REGION:=asia-south1}"
: "${CLUSTER:=agent-sandbox-demo}"
gcloud container clusters delete "$CLUSTER" --location="$REGION" --quiet
