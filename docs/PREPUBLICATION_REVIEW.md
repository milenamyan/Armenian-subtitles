# Publication review — 2026-11-11

Status: local preparation completed; no public deployment verified.

## Changes and evidence

- Added frame protection, a limited Content Security Policy, disabled camera/microphone/geolocation permissions, and a no-referrer policy. Headers now also cover authentication and CSRF rejection responses. This CSP is a baseline, not a complete script-source policy.
- Owner APIs, private downloads, publication controls, cookie signatures, CSRF protection, and private-file paths were checked by the public-release tests.
- Updated the Armenian privacy notice to disclose browser viewing progress and direct public cloud links. Public cloud URLs are not access-controlled by HaySub; unpublishing cannot revoke them or delete external files.
- Deployment packaging now includes images and fonts. Local data, logs, credentials, Git metadata, and the virtual environment are excluded by the source-package allowlist. Docker context exclusions also cover local tools and videos.
- Added ignore rules for runtime data and additional environment files. Ignore rules do not remove files already tracked in Git.
- Scanned tracked files and 176 reachable/reflog Git blobs for current configured secret values and common credential patterns; no matches were found. This is not a guarantee against every possible secret format.
- 61 focused Python tests passed (public release, hosted videos, cloud links, viewer). All 84 website JavaScript tests passed. Corrected stale tests for upload deduplication and subtitle position buttons, and isolated local cloud settings from tests.
- A broader Python run was stopped during slow translation/retry tests; a complete suite pass is not claimed. No live browser playback, cloud-bucket permissions audit, dependency vulnerability scan, or public-host penetration test was performed.

## Required deployment configuration

The inspected local environment is development mode. Do not expose that local server directly. The Docker image and Render blueprint enable public mode; retain this setting on the hosted server.

1. Choose the hosting service and HTTPS origin. Configure `HAYSUB_PUBLIC=1`, `HAYSUB_PUBLIC_URL`, a randomly generated `HAYSUB_ADMIN_TOKEN` of at least 32 characters, and a public `HAYSUB_CONTACT_EMAIL`. Store credentials in hosting environment settings.
2. Use persistent storage for `HAYSUB_DB`. The existing blueprint uses `/var/data/haysub.sqlite3`; confirm the hosting plan and disk before deployment. Keep one application instance with this SQLite setup.
3. For managed uploads, configure private S3-compatible storage. The local adapter is development-only. For direct cloud links, verify HTTPS, CORS, availability, and whether public access is intentional. Never place databases, logs, credentials, or private source subtitles in a public bucket.
4. Deploy the clean `dist/haysub-server-source.zip` contents from a new private repository. The existing repository still tracks eight runtime logs, so do not publish it as-is. The deployment ZIP excludes these files and all existing Git history.
5. Import only the intended subtitle files through the owner interface. The clean source package intentionally contains no library database or videos. Set up backups separately.
6. After deployment, run `scripts/check_public_server.py https://YOUR-HOST`, then verify owner sign-in, private/unpublished access denial, a real video and subtitle playback, and the privacy contact address in a browser.

No hosting account, remote repository, bucket permission, or production environment was changed by this review.

## References

- [Render persistent disks](https://render.com/docs/disks)
- [Render web service deployment](https://render.com/docs/web-services)
- [MDN frame-ancestors policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors)

This is a technical review of implemented behavior, not a legal compliance certification.
