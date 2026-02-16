#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

error() {
  echo "[ERROR] $*" >&2
}

info() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*"
}

if ! command -v git >/dev/null 2>&1; then
  error "git is required"
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  error "Not inside a git repository"
  exit 1
fi

branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
  warn "Current branch is '$branch' (expected: main)"
else
  info "Branch check: main"
fi

if [[ -n "$(git status --porcelain)" ]]; then
  error "Working tree is not clean. Commit/stash changes before tagging."
  exit 1
fi
info "Working tree check: clean"

user_name="$(git config --get user.name || true)"
user_email="$(git config --get user.email || true)"
if [[ -z "$user_name" || -z "$user_email" ]]; then
  error "git user identity is not set. Run:"
  error "  git config --global user.name \"Your Name\""
  error "  git config --global user.email \"you@example.com\""
  exit 1
fi
info "Git identity check: $user_name <$user_email>"

if ! git remote get-url origin >/dev/null 2>&1; then
  error "Remote 'origin' is not configured"
  error "Add one first, e.g.: git remote add origin <repo-url>"
  exit 1
fi
info "Remote check: origin configured"

if [[ -x ".venv/bin/pre-commit" ]]; then
  info "Running pre-commit checks"
  .venv/bin/pre-commit run --all-files
else
  warn "No .venv pre-commit found; skipping automatic checks"
fi

info "Preflight complete"
