# SSVT install, GitHub, Render and Android guide

## A. Local Windows run
1. Extract `SSVT_MVP_v1.zip`.
2. Install Python 3.11+ and enable PATH.
3. Open PowerShell in `SSVT_MVP_v1\backend`.
4. Run:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   Copy-Item .env.example .env
   python -m uvicorn app.main:app --reload
   ```
5. Visit `http://127.0.0.1:8000` and API docs at `/docs`.
6. Set the invite code in `.env` before creating a test creator. Default is local-only.
7. Tests: `python -m pytest -q`.

## B. GitHub upload
1. Create a new empty repository in your GitHub account.
2. Extract the ZIP and open a terminal in `SSVT_MVP_v1`.
3. Run `git init`, `git add .`, `git commit -m "SSVT MVP v1"`, `git branch -M main`, `git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git`, then `git push -u origin main`.
4. Never commit `.env`, API keys, databases, or uploaded videos. `.gitignore` excludes these local files.

## C. Render free test deployment
1. Sign in to Render and connect GitHub.
2. Choose New > Blueprint and select the repository containing `render.yaml`, or create a Web Service manually.
3. Manual settings: root directory `backend`, build command `pip install -r requirements.txt`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health path `/api/v1/health`.
4. Keep `SSVT_LLM_ENABLED=false`; do not add a paid API key. Store generated invite/admin values privately.
5. Open the resulting HTTPS `onrender.com` URL.

### Admin moderation
Use API docs `/docs`, endpoint `/api/v1/admin/videos/{video_id}/moderate`, multipart field `status=published`, header `X-Admin-Token` set to your server environment value.

### Critical Render free-tier limitation
Render free web services have ephemeral local files. Local SQLite data and uploaded video files can be lost when the service restarts, redeploys, or sleeps. Free instances also sleep after inactivity. This deployment is for temporary online upload/streaming tests only, not durable public hosting. Do not upload private or important content. Durable online streaming requires an approved persistent video/storage provider; none is selected and no paid usage is enabled.

## D. Online streaming test
1. Register with the invite code and log in.
2. Upload a small MP4/WEBM/MOV under 50 MB.
3. It starts as `pending_review`, not public.
4. Admin changes status to `published` through the endpoint above.
5. Refresh Home; the player uses `/api/v1/videos/{id}/stream`. This is direct file playback, not HLS/adaptive streaming and not 720p transcoding.

## E. LLM chatbot (disabled by default)
The chatbot UI and API are included. No LLM request is sent while `SSVT_LLM_ENABLED=false` or configuration is missing. After selecting a provider and reviewing its terms/pricing, set server-side variables: `SSVT_LLM_ENABLED=true`, `SSVT_LLM_BASE_URL`, `SSVT_LLM_API_KEY`, `SSVT_LLM_MODEL`. Base URL is the provider's OpenAI-compatible API root (without `/chat/completions`). Keep the key in Render environment settings only, never browser JS or GitHub. Do not enable a billable model without separate approval.

## F. Android without Google Play
### Option 1: installable web app
Open the deployed HTTPS URL in Chrome on Android, tap menu (⋮), then `Install app` or `Add to Home screen`. This creates an installable web app/shortcut, not a native APK.

### Option 2: native APK via Capacitor
Requirements: Node.js LTS, Android Studio, Android SDK, and compatible Java toolchain.
1. Open terminal in `SSVT_MVP_v1\android-app`.
2. Run `npm install`.
3. Replace the placeholder URL in `capacitor.config.ts` with the real HTTPS Render URL.
4. Run `npx cap add android`, then `npx cap sync android`, then `npx cap open android`.
5. In Android Studio choose Build > Build Bundle(s) / APK(s) > Build APK(s).
6. Test the APK. Do not share a build with the placeholder URL or before security review.

This bundle contains wrapper source and instructions, not a prebuilt APK. A real APK must be built with Android SDK/Android Studio after the deployed URL is known.

## G. Security status
Prototype only. Before public users, add email verification/recovery, hardened cookie/session design, rate limits, file signature/media probing and duration checks, malware scanning strategy, database backups, audit logs, moderation/copyright process, privacy policy, and persistent storage.

## v1.1 age gate, terms and moderation
- New registrations must provide `date_of_birth`, accept `terms_accepted=true`, and pass the 16+ age calculation.
- Visit `/api/v1/terms` to view the current terms payload.
- Admin Console on the homepage uses the server-side `SSVT_ADMIN_TOKEN` for user/video moderation. Do not expose this token publicly or store it in frontend source code.
- Video trim requires `ffmpeg` installed on the server. It is optional and may be unavailable on a basic free deployment.
- The metadata filter is only a preliminary screen; it cannot reliably detect sexual content from video frames. Keep uploads private/pending until a human moderator reviews them.


## v1.3 user form verification checklist
1. Open `/api/v1/health`; confirm JSON status is `running`.
2. Open `/login`; confirm both form cards load.
3. Submit blank forms and confirm browser validation appears.
4. Submit an invalid invite code and confirm a readable error appears on the signup card.
5. Submit valid test data for an eligible (16+) tester and the configured invite code; confirm the form submits and Creator Studio appears. Do not use a real password during testing.
6. Log out and sign in with the test account; wrong passwords should show an error on the login card.
7. Return to `/`, test Search by clicking the button and by pressing Enter.
8. Verify backend logs and `/api/v1/videos` response. Empty results can be normal when no videos are published.

### Correct Render command for this ZIP
The blueprint uses `rootDir: backend`, so the correct start command is:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
If the Render log says `Could not import module "main"`, compare the service's Root Directory and Start Command with the repository folders before changing environment variables. Signup/login do not require an external AI API key.
