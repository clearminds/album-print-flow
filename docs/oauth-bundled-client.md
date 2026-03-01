# Bundled Google OAuth Client

Before creating OAuth Desktop credentials, ensure the Google Cloud project has the
required API enabled:

- Go to APIs & Services -> Library
- Enable **Google Photos Picker API**

If this API is not enabled, Google sign-in may succeed but picker/media requests
will fail when the app calls Google Photos endpoints.

Place your bundled Google OAuth Desktop client JSON at:

- `src/album_print_flow/oauth/google_client_secret.json`

Resolution order used by the app:

1. `ALBUM_PRINTER_GOOGLE_CLIENT_SECRET_FILE` (explicit override)
2. `~/.config/album-print-flow/google_client_secret.json`
3. Bundled file inside app package/resources (`album_print_flow/oauth/google_client_secret.json`)

Do not commit real secrets to public repositories.
