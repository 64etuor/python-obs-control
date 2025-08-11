#!/usr/bin/env bash
set -euo pipefail

# This entrypoint optionally does a git clone/pull on startup, then runs the app.
# It assumes the container has network access and the repo URL is passed via REPO_URL.

if [[ -n "${REPO_URL:-}" ]]; then
  echo "[entrypoint] REPO_URL set: ${REPO_URL}"
  workdir="${WORKDIR:-/opt/app-repo}"
  branch="${REPO_BRANCH:-main}"
  mkdir -p "$workdir"
  if [[ -d "$workdir/.git" ]]; then
    echo "[entrypoint] existing repo detected, pulling latest..."
    git -C "$workdir" fetch --all --prune
    git -C "$workdir" checkout "$branch"
    git -C "$workdir" pull --rebase --autostash || true
  else
    echo "[entrypoint] cloning fresh..."
    git clone --depth 1 --branch "$branch" "$REPO_URL" "$workdir"
  fi
  # optional: install/update requirements from the repo
  if [[ -f "$workdir/requirements.txt" ]]; then
    pip install -r "$workdir/requirements.txt"
  fi
  # run from the cloned repo if desired
  if [[ -z "${APP_MODULE:-}" ]]; then APP_MODULE="app.presentation.app_factory:app"; fi
  cd "$workdir"
  exec uvicorn "$APP_MODULE" --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}"
else
  echo "[entrypoint] no REPO_URL, running built-in app"
  if [[ -z "${APP_MODULE:-}" ]]; then APP_MODULE="app.presentation.app_factory:app"; fi
  exec uvicorn "$APP_MODULE" --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}"
fi


