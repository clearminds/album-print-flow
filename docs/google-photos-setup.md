# Google Photos Setup

Follow these steps to configure Google Photos integration for Album Print Flow.

## 1) Create/choose a Google Cloud project

- Open Google Cloud Console.
- Create a project or select an existing one.

## 2) Enable Google Photos Picker API

- Go to APIs & Services -> Library.
- Enable **Google Photos Picker API**.
- If this is not enabled, OAuth sign-in can still appear to work, but picker
  session/media calls will fail with API access errors.

## 3) Configure OAuth consent screen

- Go to APIs & Services -> OAuth consent screen.
- Choose app type (`External` unless your org requires otherwise).
- Fill required fields.
- If app is in testing mode, add your Google account under **Test users**.

## 4) Create OAuth Desktop credentials

- Go to APIs & Services -> Credentials.
- Click **Create Credentials** -> **OAuth client ID**.
- Application type: **Desktop app**.
- Download the JSON.

## 5) Provide client JSON to the app

Preferred location:

- `~/.config/album-print-flow/google_client_secret.json`

Alternative:

- Set `ALBUM_PRINTER_GOOGLE_CLIENT_SECRET_FILE` to your JSON file path.

## 6) Verify setup from app

- In app menu: **File -> Test Google Setup**.
- This checks:
  - OAuth client JSON is present/valid
  - Sign-in/auth flow succeeds
  - Google Photos API endpoint is reachable

## Troubleshooting: API not enabled

If sign-in works but picker load fails:

- Open your selected Google Cloud project.
- Go to APIs & Services -> Library.
- Confirm **Google Photos Picker API** is enabled for that same project.
- Retry **File -> Test Google Setup** in the app.

## 7) First album load and token cache

- Use **Load ... -> Google Photos**.
- First popup shows all added accounts, plus:
  - **Add account...**
  - **Manage accounts...**
- Use **Manage accounts...** to delete accounts.
- The app opens Google Photos Picker in your browser.
- Google Photos Picker does not show album tabs directly (including shared albums).
- To pick from an album, use Picker search and search by album title.
- Select photos/videos there and press **Done**.
- The app polls picker session status and imports selected items.
- Sign in via browser when prompted.
- Token storage:
  - OS keychain/secret manager when available
  - fallback file per account: `~/.config/album-print-flow/google_token_<account>.json`

## Credential file resolution order

1. `ALBUM_PRINTER_GOOGLE_CLIENT_SECRET_FILE`
2. `~/.config/album-print-flow/google_client_secret.json`
3. Bundled resource: `album_print_flow/oauth/google_client_secret.json`

## Notes

- Google album cache: `~/.cache/album-print-flow/google-photos/`
- Source continuity state: `~/.config/album-print-flow/source_state.json`
- Do not commit real OAuth client secrets to the repository.
