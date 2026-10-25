# SSVT — Super Sonic Vedio Tube (MVP v1)

Invite-only video platform prototype with FastAPI, SQLite, local upload storage, moderation, direct playback of approved local files, optional OpenAI-compatible LLM chatbot (disabled by default), PWA install metadata, Render blueprint and Capacitor Android wrapper source.

See `docs/INSTALL_AND_DEPLOY_GUIDE.md`. No video provider is selected, no paid services are activated, and no prebuilt APK is included. Render free filesystem is ephemeral; use only for temporary tests.

## Company, age gate and moderation update (v1.1 prototype)
- Company attribution from the supplied image: **AI Software Innovation Infotech and Hardware Enterprises & Artificial Intelligence**.
- New registrations require a date of birth, minimum age 16, and acceptance of the Terms & Conditions. Terms are available at `/api/v1/terms` and on the website.
- Admin console supports user warnings, block/unblock, soft-delete/reactivation, role labels, video review/publish/reject, download, deletion, optional FFmpeg trimming, and an audit log.
- Metadata screening rejects titles/descriptions that match a small prohibited sexual-content keyword list. This does **not** visually inspect video frames. Every upload still requires human moderation; add specialist video/image moderation before a public launch.
- Admin APIs require `X-Admin-Token: <SSVT_ADMIN_TOKEN>`. Change the default token before deployment. The current team role is a role label only; separate fine-grained team permissions are not production-ready yet.
- Copyright/terms copy is a starter template, not legal advice. Obtain legal review before public launch.


## UI update v1.2
- New public homepage with Recent Videos, Viral/Featured Picks, and category browsing.
- Existing login and signup forms moved to the dedicated `/login` page.
- Category matching currently uses video title/description keywords; actual view/like-based viral ranking is future work.
- Categories currently are client-side labels, not a stored category field in the database.


## UI update v1.3 — User form and interaction reliability
- Reworked the login and creator-registration forms into responsive cards with labels, placeholders, mobile-friendly input sizing, accessible status messages, and loading states.
- Login/register errors now appear beside the relevant form rather than relying only on a global notification.
- Search supports both the Search button and pressing Enter.
- Kept the existing server-side registration rules: invite code required, minimum age 16, terms acceptance, input validation, duplicate-account checks, and hashed passwords. This update does not bypass those rules.
- API keys are not needed for signup/login. AI chat remains optional and disabled by default.

### Render deployment check
The included `render.yaml` expects the repository root directory to be `backend` and the start command to be `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Do not use `uvicorn main:app` for this folder structure. If your Render service has a different Root Directory, match the command to the actual repository layout.

### Important limits
This ZIP is an updated source package, not a claim that the live Render service has been changed. Upload/commit these files to the repository connected to Render, deploy, then test `/api/v1/health`, `/login`, signup, login, and search. Render free local storage is ephemeral; this prototype is not ready for permanent user/video storage.
