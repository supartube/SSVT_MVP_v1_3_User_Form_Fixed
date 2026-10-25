# Security checklist before any public deployment

- [ ] Replace local invite/admin/secret values with high-entropy secrets.
- [ ] Never commit `.env`, databases, uploaded videos, or credentials.
- [ ] Replace prototype bearer token/session handling with a reviewed secure HttpOnly cookie/session design.
- [ ] Add rate limits, login abuse controls, email verification and account recovery.
- [ ] Add upload signature inspection, media probing, duration validation, malware scanning strategy and cleanup.
- [ ] Add CSRF protection if cookie sessions are introduced.
- [ ] Configure HTTPS and strict CORS.
- [ ] Add moderation audit logs, copyright reports, appeals and retention/deletion policy.
- [ ] Add database backups and test restore.
- [ ] Verify webhook signatures and replay protection after provider selection.
- [ ] Test concurrent quota enforcement and private playback permissions.
- [ ] Keep paid usage disabled unless separately approved.

## Added v1.1 checks before public launch
- [ ] Replace default admin token and secret key with strong environment secrets.
- [ ] Implement per-team-member scoped permissions (current `team` role is not yet a separate permission boundary).
- [ ] Add email/age verification appropriate to local law; date-of-birth entry alone does not verify age.
- [ ] Add video-frame moderation / human review workflow; keyword metadata filter alone cannot detect prohibited visuals.
- [ ] Legal review of terms, copyright notice, privacy policy, takedown and appeals process.
- [ ] Test FFmpeg trimming on representative formats; stream-copy trimming may be keyframe-approximate.
- [ ] Add rate limiting, stronger session revocation, upload signature probing, malware scanning and persistent object storage.
