#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage:
  scripts/release-tag.sh <stable|rc|beta|alpha> <version> [number]

Examples:
  scripts/release-tag.sh rc 0.1.0 1       # v0.1.0-rc.1
  scripts/release-tag.sh beta 0.1.0 2     # v0.1.0-beta.2
  scripts/release-tag.sh stable 0.1.0     # v0.1.0
EOF
}

error() {
  echo "[ERROR] $*" >&2
}

info() {
  echo "[INFO] $*"
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

kind="$1"
version="$2"
number="${3:-}"

if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  error "Version must be in semver format: X.Y.Z"
  exit 1
fi

case "$kind" in
  stable)
    tag="v${version}"
    ;;
  rc|beta|alpha)
    if [[ -z "$number" || ! "$number" =~ ^[0-9]+$ ]]; then
      error "${kind} requires numeric sequence, e.g. 1"
      exit 1
    fi
    tag="v${version}-${kind}.${number}"
    ;;
  *)
    usage
    exit 1
    ;;
esac

if [[ -n "$(git status --porcelain)" ]]; then
  error "Working tree is not clean. Commit/stash changes before tagging."
  exit 1
fi

if git rev-parse "$tag" >/dev/null 2>&1; then
  error "Tag already exists: $tag"
  exit 1
fi

info "Creating tag: $tag"
git tag "$tag"

if ! git remote get-url origin >/dev/null 2>&1; then
  error "Remote 'origin' is not configured. Tag created locally only: $tag"
  exit 1
fi

info "Pushing tag to origin: $tag"
git push origin "$tag"

info "Done. release.yml will build and publish for tag $tag"
