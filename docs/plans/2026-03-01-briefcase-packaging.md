# Briefcase Packaging & GitHub Actions CI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace PyInstaller with Briefcase for cross-platform packaging (Windows .exe/installer, macOS .app/.dmg, Linux Flatpak) and set up GitHub Actions CI to build on all three platforms.

**Architecture:** Add `[tool.briefcase]` config to the existing `pyproject.toml`, generate platform icon sets from the existing `assets/icons/app-icon-256.png`, replace both `.github/workflows/ci.yml` and `release.yml` with Briefcase-based workflows. No changes to application code — only packaging and CI.

**Tech Stack:** Briefcase (BeeWare), GitHub Actions, PySide6, Flatpak (Linux)

---

## Pre-requisites: Commit & Branch

### Task 0: Commit current work and create briefcase branch

This task happens in the current session before the plan is handed off.

**Step 1: Stage and commit all current changes on initial-branch**

```bash
git add src/album_print_flow/app.py \
        src/album_print_flow/printing/flows/queue_controller.py \
        src/album_print_flow/printing/main_window_queue_entrypoints.py \
        src/album_print_flow/printing_helpers.py \
        src/album_print_flow/sources/flows/album_url.py \
        src/album_print_flow/ui/location_lookup_flow.py \
        src/album_print_flow/ui/main_window_misc_entrypoints.py \
        src/album_print_flow/ui/main_window_state_init.py \
        src/album_print_flow/ui/photo_entry_flow.py \
        src/album_print_flow/ui/preview_flow.py \
        src/album_print_flow/printing/flows/cups_job_poll.py
git commit -m "feat: CUPS job polling and queue controller improvements"
```

**Step 2: Push initial-branch**

```bash
git push origin initial-branch
```

**Step 3: Create and switch to briefcase branch**

```bash
git checkout -b feature/briefcase-packaging
```

---

## Part 1: Briefcase Configuration

### Task 1: Generate Briefcase icon set from existing app icon

Briefcase requires icons at specific sizes for each platform. It looks for them at the path specified in `icon` config (without extension), and auto-selects the right file per platform.

**Files:**
- Source: `assets/icons/png/app-icon-256.png` (existing)
- Create: `assets/icons/png/app-icon-16.png`
- Create: `assets/icons/png/app-icon-32.png`
- Create: `assets/icons/png/app-icon-48.png`
- Create: `assets/icons/png/app-icon-64.png`
- Create: `assets/icons/png/app-icon-128.png`
- Create: `assets/icons/app-icon.icns` (macOS — generated from PNGs)
- Create: `assets/icons/app-icon.ico` (Windows — generated from PNGs)

**Step 1: Write a Python script to generate all icon sizes**

Create `scripts/generate_icons.py`:

```python
"""Generate icon files for Briefcase packaging from source PNG."""
from pathlib import Path

from PIL import Image

SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]
SRC = Path("assets/icons/png/app-icon-1024.png")
OUT_DIR = Path("assets/icons/png")


def main() -> None:
    img = Image.open(SRC).convert("RGBA")
    for size in SIZES:
        resized = img.resize((size, size), Image.LANCZOS)
        out = OUT_DIR / f"app-icon-{size}.png"
        resized.save(out, "PNG")
        print(f"  {out}")

    # Windows .ico (multi-size)
    ico_sizes = [16, 32, 48, 256]
    ico_images = [img.resize((s, s), Image.LANCZOS) for s in ico_sizes]
    ico_path = Path("assets/icons/app-icon.ico")
    ico_images[0].save(ico_path, format="ICO", sizes=[(s, s) for s in ico_sizes])
    print(f"  {ico_path}")


if __name__ == "__main__":
    main()
```

**Step 2: Run the script**

```bash
python scripts/generate_icons.py
```

Expected: PNG files at all sizes plus `app-icon.ico` created.

Note: `.icns` for macOS is handled automatically by Briefcase during `briefcase create macOS` — it converts PNGs. No manual `.icns` needed.

**Step 3: Verify the icon files exist**

```bash
ls -la assets/icons/png/
ls -la assets/icons/app-icon.ico
```

**Step 4: Commit**

```bash
git add scripts/generate_icons.py assets/icons/
git commit -m "chore: generate icon set for Briefcase packaging"
```

---

### Task 2: Add Briefcase configuration to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add `[tool.briefcase]` sections to `pyproject.toml`**

Append after the existing `[tool.ruff.lint]` section. Keep ALL existing setuptools/ruff/black/isort config unchanged.

```toml
# ── Briefcase packaging ──────────────────────────────────────────────

[tool.briefcase]
project_name = "Album Print Flow"
bundle = "se.clearminds"
version = "1.0.0"
url = "https://github.com/clearminds/album-print-flow"
license.file = "LICENSE"
author = "Clearminds"
author_email = "info@clearminds.se"

[tool.briefcase.app.album-print-flow]
formal_name = "Album Print Flow"
description = "Crop, stamp and print photo albums"
icon = "assets/icons/png/app-icon"
sources = ["src/album_print_flow"]
requires = [
    "Pillow>=11.0.0",
    "PySide6>=6.8.0",
    "pyipp>=0.17.2",
    "google-auth>=2.40.0",
    "google-auth-oauthlib>=1.2.2",
    "keyring>=25.6.0",
    "pillow-heif>=0.18.0",
    "rawpy>=0.25.1",
    "requests>=2.32.5",
]

[tool.briefcase.app.album-print-flow.macOS]
requires = []

[tool.briefcase.app.album-print-flow.linux]
requires = []

[tool.briefcase.app.album-print-flow.linux.flatpak]
flatpak_runtime = "org.kde.Platform"
flatpak_runtime_version = "6.7"
flatpak_sdk = "org.kde.Sdk"

[tool.briefcase.app.album-print-flow.windows]
requires = []
```

Key decisions:
- `sources = ["src/album_print_flow"]` — tells Briefcase where the package lives
- `icon` path is without extension — Briefcase picks `.png`, `.ico`, or `.icns` per platform
- Linux Flatpak uses KDE runtime (not GNOME) because PySide6/Qt needs the KDE platform for proper Qt support
- Platform-specific `requires = []` means "no additional deps beyond the main list"

**Step 2: Verify TOML is valid**

```bash
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb')); print('valid')"
```

Expected: `valid`

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add Briefcase packaging configuration"
```

---

### Task 3: Add Briefcase entry point adapter

Briefcase expects the app entry to follow a specific pattern. The existing `main.py` returns an int, but Briefcase for GUI apps expects the module to have a `main()` callable. The current `__main__.py` does `raise SystemExit(main())` which is fine for CLI but needs a small check.

**Files:**
- Read: `src/album_print_flow/__main__.py` (existing — likely fine as-is)
- Read: `src/album_print_flow/main.py` (existing — likely fine as-is)

**Step 1: Verify the entry point works with Briefcase**

Briefcase calls `from album_print_flow.main import main; main()` for the app. Check the current `main.py`:

```python
# Current src/album_print_flow/main.py:
from .app import run_application

def main() -> int:
    return run_application()
```

This is compatible — Briefcase will call `main()` and the int return is harmless. No changes needed.

**Step 2: Test locally with `briefcase dev`**

```bash
pip install briefcase
briefcase dev
```

Expected: The app launches normally. If it crashes, check the error output — most likely a missing dependency or icon path issue.

**Step 3: Commit only if changes were needed**

If no code changes were required, skip this commit.

---

## Part 2: GitHub Actions CI

### Task 4: Replace CI workflow with Briefcase-based dev build

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Replace `.github/workflows/ci.yml` with Briefcase workflow**

```yaml
name: Dev Build

on:
  push:
    branches:
      - "development"
      - "feature/*"
    tags:
      - "v*-dev*"
  pull_request:
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

env:
  FORCE_COLOR: "1"

defaults:
  run:
    shell: bash

jobs:
  ci:
    name: Build (${{ matrix.target }})
    runs-on: ${{ matrix.runs-on }}
    strategy:
      fail-fast: false
      matrix:
        target: ["Windows", "macOS", "Flatpak"]
        include:
          - target: "Windows"
            output-format: "app"
            runs-on: "windows-latest"

          - target: "macOS"
            output-format: "app"
            runs-on: "macos-latest"

          - target: "Flatpak"
            platform: "Linux"
            output-format: "Flatpak"
            runs-on: "ubuntu-latest"
            pre-command: >-
              sudo apt-get update &&
              sudo apt-get -y install flatpak flatpak-builder

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Briefcase
        run: python -m pip install -U pip setuptools wheel briefcase

      - name: Platform setup
        run: ${{ matrix.pre-command || 'echo ok' }}

      - name: Build
        run: |
          briefcase create \
            ${{ matrix.platform || matrix.target }} \
            ${{ matrix.output-format }} \
            --no-input --log
          briefcase build \
            ${{ matrix.platform || matrix.target }} \
            ${{ matrix.output-format }} \
            --no-input --log

      - name: Package
        run: |
          briefcase package \
            ${{ matrix.platform || matrix.target }} \
            ${{ matrix.output-format }} \
            --update --adhoc-sign --no-input --log

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: dev-build-${{ matrix.target }}-${{ github.run_number }}
          path: dist/
          retention-days: 7

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: logs-${{ matrix.target }}
          path: logs/
```

**Step 2: Verify YAML syntax**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('valid')"
```

If PyYAML not installed, just visually verify the indentation is correct.

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: replace PyInstaller with Briefcase for dev builds"
```

---

### Task 5: Replace release workflow with Briefcase-based release

**Files:**
- Modify: `.github/workflows/release.yml`

**Step 1: Replace `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags:
      - "v*"
      - "!v*-dev*"

permissions:
  contents: write

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}

env:
  FORCE_COLOR: "1"

defaults:
  run:
    shell: bash

jobs:
  build:
    name: Package (${{ matrix.target }})
    environment: ${{ contains(github.ref_name, '-alpha') || contains(github.ref_name, '-beta') || contains(github.ref_name, '-rc') && 'beta' || 'prod' }}
    runs-on: ${{ matrix.runs-on }}
    strategy:
      fail-fast: false
      matrix:
        target: ["Windows", "macOS", "Flatpak"]
        include:
          - target: "Windows"
            output-format: "app"
            runs-on: "windows-latest"
            artifact-glob: "dist/*.msi"

          - target: "macOS"
            output-format: "app"
            runs-on: "macos-latest"
            artifact-glob: "dist/*.dmg"

          - target: "Flatpak"
            platform: "Linux"
            output-format: "Flatpak"
            runs-on: "ubuntu-latest"
            artifact-glob: "dist/*.flatpak"
            pre-command: >-
              sudo apt-get update &&
              sudo apt-get -y install flatpak flatpak-builder

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Briefcase
        run: python -m pip install -U pip setuptools wheel briefcase

      - name: Platform setup
        run: ${{ matrix.pre-command || 'echo ok' }}

      - name: Create & Build
        run: |
          briefcase create \
            ${{ matrix.platform || matrix.target }} \
            ${{ matrix.output-format }} \
            --no-input --log
          briefcase build \
            ${{ matrix.platform || matrix.target }} \
            ${{ matrix.output-format }} \
            --no-input --log

      - name: Package
        run: |
          briefcase package \
            ${{ matrix.platform || matrix.target }} \
            ${{ matrix.output-format }} \
            --update --adhoc-sign --no-input --log

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: release-${{ matrix.target }}
          path: dist/
          if-no-files-found: error

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: logs-${{ matrix.target }}
          path: logs/

  publish:
    name: Publish GitHub Release
    runs-on: ubuntu-latest
    needs: build

    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          pattern: release-*

      - name: Publish release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            artifacts/**/*.msi
            artifacts/**/*.dmg
            artifacts/**/*.flatpak
          draft: false
          prerelease: ${{ contains(github.ref_name, '-alpha') || contains(github.ref_name, '-beta') || contains(github.ref_name, '-rc') }}
```

**Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: replace PyInstaller with Briefcase for releases"
```

---

### Task 6: Remove PyInstaller from requirements.txt

**Files:**
- Modify: `requirements.txt`

**Step 1: Remove `pyinstaller>=6.12.0` from `requirements.txt`**

The line `pyinstaller>=6.12.0` is no longer needed since we use Briefcase. Remove it — the file should become:

```
Pillow>=11.0.0
PySide6>=6.8.0
pyipp>=0.17.2
google-auth>=2.40.0
google-auth-oauthlib>=1.2.2
keyring>=25.6.0
pillow-heif>=0.18.0
rawpy>=0.25.1
requests>=2.32.5
```

**Step 2: Commit**

```bash
git add requirements.txt
git commit -m "chore: remove pyinstaller dependency (replaced by briefcase)"
```

---

### Task 7: Test locally and push

**Step 1: Install Briefcase locally**

```bash
pip install briefcase
```

**Step 2: Run `briefcase dev` to verify the app starts**

```bash
briefcase dev
```

Expected: The app launches. If there are import errors, fix them (most likely `sources` path issue in `pyproject.toml`).

**Step 3: Try a full local build (Linux)**

```bash
briefcase create linux flatpak --no-input
briefcase build linux flatpak --no-input
```

Expected: Flatpak build completes. This requires `flatpak` and `flatpak-builder` to be installed locally (`sudo dnf install flatpak flatpak-builder` on Fedora).

**Step 4: Push the branch**

```bash
git push -u origin feature/briefcase-packaging
```

**Step 5: Create PR (optional)**

```bash
gh pr create --title "Replace PyInstaller with Briefcase packaging" \
  --body "Adds Briefcase configuration for cross-platform packaging (Windows, macOS, Linux Flatpak) and updates GitHub Actions CI/CD workflows."
```

---

## Platform Build Summary

| Platform | Runner | Output | Signing |
|----------|--------|--------|---------|
| Windows | `windows-latest` | `.msi` installer | `--adhoc-sign` (unsigned, shows SmartScreen warning) |
| macOS | `macos-latest` | `.dmg` with `.app` inside | `--adhoc-sign` (unsigned, shows Gatekeeper warning) |
| Linux | `ubuntu-latest` | `.flatpak` bundle | Not required |

### Future: Code Signing

For production releases without security warnings:
- **Windows**: Needs a code signing certificate (EV cert ~$400/yr). Add `--identity` flag to `briefcase package`.
- **macOS**: Needs an Apple Developer account ($99/yr) + signing identity. Add `--identity "Developer ID Application: ..."` to `briefcase package`. For notarization, add `--notarize`.
- **Linux Flatpak**: No signing needed. For Flathub distribution, submit the app manifest to flathub/flathub.

### Dependency Risk: rawpy

`rawpy` ships binary wheels for Linux x86_64, macOS (x86_64 + arm64), and Windows. However, inside a Flatpak build container the pip install runs in an isolated environment. If `rawpy` fails to install in the Flatpak sandbox:
- **Workaround**: Make rawpy optional (it already has a graceful import pattern like pillow_heif) and fall back to not supporting RAW formats in Flatpak.
- **Better fix**: Add rawpy's native dependency `libraw` to the Flatpak manifest's `finish-args` or `build-options`.
