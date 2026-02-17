# Third-Party Notices

This file tracks bundled third-party assets and where they come from.

## Bundled Fonts

| Local file | Embedded font name | Upstream source | License |
| --- | --- | --- | --- |
| `src/album_printer/fonts/ClassicMono.ttf` | Liberation Mono (Regular) | Liberation Fonts project (https://github.com/liberationfonts/liberation-fonts) | SIL Open Font License 1.1 |
| `src/album_printer/fonts/PhotoStampMono.ttf` | Noto Sans Mono Bold | Google Noto Fonts (https://github.com/notofonts/noto-fonts) | SIL Open Font License 1.1 |

Notes:

- Font names above were extracted from embedded font metadata (`fc-scan`) on 2026-02-16.
- Keep upstream project links and license details in sync if these font files are replaced.

## Project-Owned Assets

The following files are project-owned branding assets (not third-party):

- `assets/branding/clearminds-head.png`
- `assets/branding/clearminds-wordmark.png`
- `assets/icons/app-icon.svg`
- `assets/icons/png/app-icon-256.png`
- `assets/icons/png/app-icon-512.png`
- `assets/icons/png/app-icon-1024.png`

## Python Dependencies

The project also depends on third-party Python packages installed via `pyproject.toml` and `requirements.txt`.

| Package | Purpose | License (metadata) | Upstream |
| --- | --- | --- | --- |
| `Pillow` | Image loading/editing | UNKNOWN in package metadata (commonly distributed under HPND-style terms) | https://github.com/python-pillow/Pillow |
| `PySide6` | Qt UI framework | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | https://pyside.org |
| `pyipp` | IPP backend integration | MIT | https://github.com/ctalkington/python-ipp |
| `pyinstaller` | Application packaging | GPLv2-or-later with PyInstaller special exception | https://pyinstaller.org |
| `google-auth` | Google OAuth/auth transport | Apache-2.0 | https://github.com/googleapis/google-auth-library-python |
| `google-auth-oauthlib` | OAuth flow helper | Apache-2.0 | https://github.com/GoogleCloudPlatform/google-auth-library-python-oauthlib |
| `requests` | HTTP client | Apache-2.0 | https://requests.readthedocs.io |
| `keyring` | OS secret manager access | UNKNOWN in package metadata | https://github.com/jaraco/keyring |
| `pillow-heif` | HEIC/HEIF decoding | BSD-3-Clause in package metadata (contains classifier inconsistency, see note below) | https://github.com/bigcat88/pillow_heif |
| `rawpy` | RAW photo decoding | UNKNOWN in package metadata (includes MIT classifier) | https://github.com/letmaik/rawpy |

### Verification Workflow

Before a release, re-run a dependency license audit in the project virtual environment and update this file if dependency versions change.
