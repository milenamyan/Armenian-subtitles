# Owner-uploaded videos and public viewing

**Video bin: 24 hours.** Removing a video immediately unpublishes it and keeps it
in the owner-only bin for 24 hours. Restore it before the displayed deadline to
keep it; restoration is private and requires publishing again. After the deadline,
the media worker permanently removes its media, subtitle versions, multipart
remnants and metadata. If the worker is offline or storage deletion fails, cleanup
waits/retries rather than falsely claiming that files were deleted. Storage charges
continue until cleanup succeeds. No public deployment was performed.

HaySub can now host your own/permitted videos with prepared Armenian subtitles.
Viewers open a link such as `https://YOUR-SERVER/watch/VIDEO-ID` in Safari or Chrome.
They do not need the extension, Python, an account, an API key or an App Store app.

Nothing was purchased, deployed or made public by implementing this feature.
You must configure private object storage and verify your actual bucket and devices.

## Owner workflow

1. Open `/admin` and sign in with your existing owner password. The existing file
   translator and subtitle library remain available. Local development without
   public mode remains trusted local use; bind Uvicorn to `127.0.0.1`.
2. Find **Upload a video and share a viewing link** below the subtitle library.
   If storage is missing, the page shows exactly what to configure and disables
   video upload. It does not simulate successful storage.
3. Enter a title and select your compatible MP4. The default limit is **12 GiB**
   (12,884,901,888 bytes), sufficient for approximately 10 GB. Uploads use sequential
   **64 MiB** parts directly to S3. HaySub does not receive the video body in its
   normal production API, and neither browser nor Python loads the whole file in RAM.
4. Watch the real byte progress. **Pause upload** stops the current part. To resume
   after a connection interruption or page refresh, click **Resume upload** on the
   saved video and select the same original file. Its size, filename, modification
   date and a SHA-256 of small beginning/end samples must match. This sampled
   fingerprint is a file-selection guard, not a full-file integrity checksum.
   The storage provider's actual part sizes/ETags are verified before completion.
   Unacknowledged or mismatched parts are uploaded again rather than guessed.
5. The worker finalizes the multipart upload, confirms the resulting object size,
   checks MP4 headers and runs ffprobe. This is a separate process, outside web
   request handlers. The row reports `finalizing`, `processing`, `ready` or a useful
   error. No conversion progress is invented; this release does not transcode.
6. In the video row, choose an existing library subtitle (even a private one) or
   upload a prepared Armenian UTF-8 SRT/VTT, then click **Save Armenian track**.
   You can attach it while the video uploads or after inspection. This never
   calls Gemini. English/Russian dialogue must first be translated using the
   existing file translator. Empty cues and music-only annotations are skipped.
7. **Subtitle offset** is per video: `+2` delays text two seconds; `−2` shows it
   two seconds earlier. A fresh escaped WebVTT copy is stored under this video's
   private prefix. The library source and tracks on other videos are unchanged.
   Cue overlaps and timing are retained during conversion; cues shifted entirely
   before zero are omitted and a partially negative start is clipped to zero.
8. Once media is ready and its Armenian track is saved, open **Private preview**.
   Check the movie, timing and subtitle language before publishing.
9. Click **Publish and create viewing link**. Copy the visible `/watch/...` link
   to viewers. **Unpublish** immediately prevents new playback authorization.
   Publishing is **unlisted**, not password protection: anyone with the link can
   watch and share it, and authorized viewers can save media they can access.
10. **Move to bin (24 hours)** unpublishes immediately. The video appears in the
    **Video bin** section with its permanent-cleanup deadline. **Restore from bin**
    works before that deadline and restores privately. Repeated removal requests
    do not extend the original deadline. After 24 hours, the worker aborts pending
    multipart uploads, removes the source and every generated track version, then
    removes metadata. Cleanup failures remain visible and retryable. The shared
    subtitle library is not deleted. Bin retention is metadata-based: S3 objects
    stay private at their original keys, avoiding a duplicate 10 GB copy.

The deadline survives restarts and does not depend on a browser tab being open.
Permanent cleanup can run later if the worker was offline/busy or credentials
failed. Already-issued viewing URLs have their usual expiry window. A restored
unfinished upload is also subject to the provider's existing multipart lifecycle
cutoff; completed video objects have no such incomplete-upload cutoff. Older
untagged filesystem archives created before this feature are not automatically
purged, and subtitle/process bins elsewhere in the app are unchanged.

Owner sign-in cookies last up to six hours. If a very long upload outlasts the
cookie, sign in again and resume; saved parts remain. SDK upload receipts and
metadata persist in SQLite across server restarts. An interrupted worker job can
wait for its old lease (up to 15 minutes by default) before retrying safely.

## Supported media, honestly

This first release accepts an actual MP4 container with:

- One H.264 video stream, 8-bit `yuv420p`, Baseline/Constrained Baseline/Main/High
  profile, level 4.2 or lower, SDR.
- At most one audio stream: AAC-LC mono/stereo. Silent MP4 is also supported.
- A finite duration greater than zero and no more than 24 hours.

An `.mp4` filename or browser MIME label is not proof of compatibility. Renamed
MKV/MOV files, HEVC, 10-bit/HDR, DTS/AC3 and other unsupported combinations fail
inspection and remain private. Delete a rejected large file when no longer needed
to avoid storage charges. Container/codec inspection is not a full decode of every
frame; damaged payloads or unusual device limitations can still cause playback errors.

Compatible media is delivered unchanged, without re-encoding or a duplicate video
object. A `moov` atom after `mdat` is accepted but warned about because initial
progressive playback can be slower. To remux your own compatible file locally:

```powershell
ffmpeg -i input.mp4 -map 0:v:0 -map 0:a:0? -c copy -movflags +faststart output.mp4
```

For incompatible media, convert locally before upload, for example:

```powershell
ffmpeg -i input.mkv -map 0:v:0 -map 0:a:0? -c:v libx264 -profile:v high -level:v 4.1 -pix_fmt yuv420p -vf "scale=w='min(1920,iw)':h='min(1080,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2" -c:a aac -profile:a aac_low -ac 2 -b:a 160k -movflags +faststart output.mp4
```

These commands are suggestions to run on your own permitted media, not server
transcoding. Verify the output; very high frame rates may still exceed the stated
H.264 level. No automatic HDR-to-SDR tone mapping or adaptive-bitrate streaming is
implemented. [FFmpeg reference](https://ffmpeg.org/ffmpeg.html),
[ffprobe reference](https://ffmpeg.org/ffprobe.html).

## Private S3-compatible storage configuration

Create/configure the bucket yourself; this project does not create paid resources.
Use a dedicated **private** bucket or dedicated `haysub-media/` prefix. Disable
public bucket policies, public ACLs and public/CDN object URLs. CORS is not access
control. The bucket must remain private even when a video is published.

Set these variables on the existing server and worker (never frontend/GitHub):

| Setting | Value / purpose |
| --- | --- |
| `HAYSUB_MEDIA_STORAGE` | `s3` |
| `HAYSUB_S3_ENDPOINT` | Provider's HTTPS S3 API endpoint; omit for standard AWS regional S3 |
| `HAYSUB_S3_BUCKET` | Private bucket name |
| `HAYSUB_S3_REGION` | Real AWS/provider region; some compatible providers specify `auto` |
| `HAYSUB_S3_ACCESS_KEY_ID` | Server-only scoped access key |
| `HAYSUB_S3_SECRET_ACCESS_KEY` | Server-only secret key |
| `HAYSUB_S3_SESSION_TOKEN` | Optional, only for temporary credentials |
| `HAYSUB_S3_PREFIX` | `haysub-media` by default; use a dedicated stable prefix |
| `HAYSUB_S3_ADDRESSING_STYLE` | `path` default; use `virtual` if required by your provider |
| `HAYSUB_S3_VERSIONED` | `0` for a bucket with versioning **disabled**; **must be `1` if versioning is enabled** |
| `HAYSUB_MEDIA_MAX_BYTES` | `12884901888` (12 GiB) |
| `HAYSUB_MEDIA_PART_BYTES` | `67108864` (64 MiB); supported 5–512 MiB, at most 10,000 parts |
| `HAYSUB_UPLOAD_URL_SECONDS` | `900` (15-minute owner-authorized part URLs) |
| `HAYSUB_PLAYBACK_TTL_SECONDS` | `14400` (4-hour playback URLs); supported 60–21,600 seconds |
| `HAYSUB_UPLOAD_IDLE_HOURS` | `48` before recorded abandoned uploads are queued for cleanup |

The SDK signs only server-generated object keys. Owner-supplied filenames, MIME
types and remote URLs never determine storage locations or fetch targets. Video
metadata, manifests and small subtitle snapshots go in SQLite; video bytes do not.
There is no endpoint for fetching arbitrary remote videos.

Grant the service credentials least-privilege access to this bucket/prefix:

- Bucket listing for the prefix (`s3:ListBucket`).
- Object put/get/delete (`s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`).
- Multipart creation/part/completion via put permissions, plus
  `s3:ListMultipartUploadParts` and `s3:AbortMultipartUpload`.
- If versioning is enabled: `s3:ListBucketVersions` and `s3:DeleteObjectVersion`.
  The adapter deletes versions and delete markers as well as visible objects.
  With versioning disabled, the adapter does not require version-list APIs, which
  some S3-compatible providers do not implement.
- If you use customer-managed encryption keys, add the provider's required
  decrypt/data-key permissions. This has not been validated against a live KMS setup.

Do not enable object-lock retention for this prefix unless you accept that deletion
will fail until retention expires. Keep bucket versioning configuration and the
`HAYSUB_S3_VERSIONED` flag consistent; otherwise old versions can remain billable.
Changing bucket, endpoint, region or prefix while uploads/videos exist prevents
processing/deletion under the wrong namespace; restore the original configuration
or migrate assets deliberately. Rotating credentials in the same namespace is fine.

### CORS (required for direct upload, seeking and native tracks)

Copy [storage-cors.example.json](storage-cors.example.json), replace its origin with
the exact HTTPS HaySub origin, and apply it in the bucket's CORS settings. Add your
custom origin too if you actually use one. No wildcard origin is needed. Required:

- Methods: `PUT`, `GET`, `HEAD`.
- Allowed request headers: `Content-Type`, `Range`, `If-Range`, `x-amz-*`.
- Exposed response headers: **`ETag`**, `Accept-Ranges`, `Content-Range`,
  `Content-Length`, `Last-Modified`.

For the AWS CLI `put-bucket-cors` API, wrap the example array in a JSON object
under `CORSRules`. Some provider dashboards accept the array directly.
The owner browser reads each part's ETag; without exposed ETag, it pauses with a
setup error rather than claiming completion. `<video crossorigin="anonymous">`
and `<track>` must be allowed to GET from your origin. Playback fetches should
return `Content-Type: video/mp4`, `text/vtt; charset=utf-8` for tracks, and HTTP 206
plus `Content-Range` for valid byte-range requests. The generated playback URLs
request the correct types and `Cache-Control: private, max-age=0`.

See [S3 CORS elements](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ManageCorsUsing.html).

### Abandoned multipart lifecycle (also required)

The worker expires **recorded** idle uploads after 48 hours and aborts them. Also
configure the bucket lifecycle rule in [storage-lifecycle.example.json](storage-lifecycle.example.json)
to abort incomplete multipart uploads after **7 days** under the same prefix.
This catches uploads created just before a crash prevented saving their storage
upload ID. Seven days is an absolute provider lifecycle cutoff, even if a browser
has remained active; finish/resume before then or start again. Do not use a rule
that expires every completed movie after seven days.

[AWS incomplete-multipart lifecycle documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpu-abort-incomplete-mpu-lifecycle-config.html).

## Worker and existing Render deployment

The previous Render setup uses SQLite on `/var/data`. Keep that small persistent
metadata disk and **one web instance / one Uvicorn worker**. Do not put 10 GB videos
on that disk and do not upload them to GitHub or the extension package.

The updated Dockerfile installs FFmpeg/ffprobe. `app.serve` drops root privileges
and supervises one separate `python -m app.media_worker` process alongside the web
process when `HAYSUB_MEDIA_WORKER_ENABLED=1` and storage is configured. Both share
the same metadata database and environment; the worker does not serve HTTP.
This is deliberately not a second Render service with a separate private disk.
Scaling to multiple instances needs a shared database/job queue redesign.

| Worker setting | Default |
| --- | --- |
| `HAYSUB_MEDIA_WORKER_ENABLED` | Docker: `1`; starts the supervised worker when storage is set |
| `HAYSUB_MEDIA_LEASE_SECONDS` | `900`; interrupted claims become retryable after this lease |
| `HAYSUB_FFPROBE` | `ffprobe` or an explicit installed executable path |
| `HAYSUB_FFPROBE_TIMEOUT_SECONDS` | `120`, allowed 10–300 seconds |
| `HAYSUB_FFPROBE_MEMORY_MB` | `512`, allowed 128–2,048 MiB on Linux |

The worker inspects one file at a time. The child process gets Linux address-space,
CPU, output-file and descriptor limits, a 64 MiB per-allocation limit, bounded
probe/analyze settings and a wall-clock timeout. Probe stdout/stderr go to bounded
temporary files rather than accumulating video or unbounded logs in RAM. Signed
URLs and ffprobe stderr are not returned to viewers or application logs. Windows
development has the wall timeout, bounded output reads and FFmpeg allocation
limit, but not Linux `resource` limits; use the Docker/Linux worker in production.
Choose a host with enough RAM for the web app, SDK and bounded probe child; this
may require increasing the old small hosting instance. A 1 GB+ instance is a useful
starting point to validate, not a measured capacity guarantee.

If you launch Uvicorn directly instead of the Docker entry point, start the media
worker separately with the same database/env:

```powershell
.\.venv\Scripts\python.exe -m app.media_worker
```

Do not run both a manually launched worker and the supervised worker. A worker
heartbeat is shown on the owner page; missing workers leave finalization queued,
not falsely ready. Persistent deletion retries and idle cleanup also require it.
No request waits for FFprobe or for local 10 GB file assembly.

## Local development without a bucket

For this Windows project, double-click **Start HaySub.bat** (or run
`.\.venv\Scripts\python.exe start.py`). It loads `.env`, starts the local server
on `127.0.0.1:8000`, and supervises the media worker when enabled. Stop an older
server first if the startup message says one is already running.

With `HAYSUB_LOCAL_VIDEO_FOLDER` set to the project's **videos** folder, drop a
completed video there. The worker scans it automatically, and the page refreshes
its video list every five seconds. You can also click **Scan video folder now**.
Files are **moved** into private managed storage on the same drive, avoiding a
second 10 GB copy. Their original filename becomes the video title. They remain
private until you attach Armenian subtitles and publish. This also applies the
24-hour bin/restore policy to imported videos.

Let copying finish before importing. Files newer than three seconds are deferred;
for slow copies, use a `.part` extension and rename after completion. `.mp4`,
`.m4v`, `.mov`, `.mkv`, `.webm` and `.avi` files appear, but only the supported
H.264/AAC MP4 media passes inspection and can be published. Other formats show
an error rather than pretending to play. Symlinked files are not imported.

Local signed storage URLs and localhost viewing links work only on this computer.
Do not send `127.0.0.1` links to friends as public hosting links.

In your local `.env` (public mode **off**), set:

```dotenv
HAYSUB_PUBLIC=0
HAYSUB_MEDIA_STORAGE=local
HAYSUB_LOCAL_MEDIA_DIR=data/local-media
HAYSUB_LOCAL_MEDIA_SECRET=YOUR-RANDOM-SECRET-AT-LEAST-32-CHARACTERS
HAYSUB_FFPROBE=C:/path/to/ffprobe.exe
```

Install FFmpeg/ffprobe separately on Windows; the executable is not bundled in
this source folder. Start your existing local server and a second terminal with
the media worker command above. The local adapter uses signed, bounded part PUTs
and FileResponse range delivery. It streams small chunks to persistent local
development storage and assembles them in the worker. It is **disabled in public
mode**, and is not the production direct-to-S3 design. Keep `data/local-media/`
out of Git and packages. For real use, choose S3 rather than routing large files
through the local development endpoint.

## Public playback and access expiry

The share page requests playback authorization from HaySub. Only published, ready
videos get new anonymous access; owner previews require the existing owner session.
The response contains expiring signed video and VTT URLs. Browsers read bytes
directly from storage, whose HTTP Range responses support seek without downloading
the entire movie first. No playback video proxy, extension or video account exists.
This implementation signs S3 delivery URLs; it does not configure or sign a separate
CDN distribution. Add a provider-specific private CDN adapter if you need that later.

**Unpublishing prevents new authorization immediately, but previously issued URLs
can still work until expiry (four hours by default), and an already-open download
may continue.** Temporary S3 credentials may expire earlier than the requested TTL.
Deleting objects does not revoke copies already downloaded. Do not describe an
unlisted URL as password protection or DRM.

The player refreshes authorization shortly before URL expiry, preserving playback
position where the browser permits. Refreshing a source during iPhone native
fullscreen may exit fullscreen or require another tap; this needs real-device
verification. A long TTL covering a normal film reduces such refreshes. Lower TTLs
reduce the unpublish grace window but cause more renewals.

The baseline is native `<video controls playsinline>` with an Armenian WebVTT
`<track>`: play/pause, seek, device-native volume and subtitle menus, speed selection,
and fullscreen controls. iPhone volume may be controlled by the device rather than
a web slider. Native fullscreen does not depend on an HTML subtitle overlay.
No claim is made that every browser/player/codec or AirPlay/Picture-in-Picture works.
[Apple Safari delivery guidance](https://developer.apple.com/documentation/webkit/delivering-video-content-for-safari).

## Costs are separate

- **Storage:** the original object size per film plus small generated VTT versions;
  incomplete parts and retained versions also consume storage until cleanup. A
  10 GB film remains about 10 GB in storage, not 10 GB in SQLite.
- **Delivery bandwidth:** charged according to your storage/CDN provider and region.
  As a rough byte estimate, 100 complete transfers of a 10 GB file are about 1 TB,
  before repeat seeks/retries. Partial viewing transfers less. Direct delivery
  avoids routing this traffic through Python but does not make egress free.
- **Requests and hosting:** multipart PUT/LIST/complete, range GETs, track requests,
  metadata hosting and FFprobe worker resources can each have charges.
- **Optional future transcoding:** not implemented and not billed by HaySub here.
  A future converter would add CPU/GPU time, temporary disk, output variants and
  additional stored/delivered bytes. Compatible uploads are reused unchanged.

No numeric price is promised. Check your provider's current storage/request/egress
rates and set its billing alerts yourself. [AWS S3 pricing categories](https://aws.amazon.com/s3/pricing/).

## What has and has not been verified

Automated checks cover owner authentication and CSRF, private/public visibility,
multipart receipts and sizes, resume behavior, invalid media metadata, native-track
page wiring, subtitle escaping/timing/offset isolation, expiry, range responses on
the local adapter, cleanup failures/retries and S3 SDK calls with stubbed responses.
The 10 GiB case verifies multipart planning/limits without allocating or uploading
a 10 GiB file. Synthetic test container bytes are original fixtures, not a claim
that a real movie was probed or played.

The local Windows setup was additionally checked with an original generated
two-second H.264/AAC clip: actual FFprobe inspection, folder import, Armenian
WebVTT, byte-range responses, publication and expired-bin cleanup passed using an
isolated temporary database. Run `python scripts/check_local_video.py` to repeat.
The project-local FFmpeg tools were verified against the publisher's SHA-256.
No live S3 upload, 10 GB transfer, public deployment, Docker build, iPhone Safari
fullscreen or Android Chrome playback was verified by that check.

Before sharing real links, configure the bucket and verify with a small video you
own, then a large one:

1. Upload, pause mid-part, refresh, reselect the same file and resume; inspect that
   network PUTs go to storage and missing parts alone are retried.
2. Complete and verify successful real ffprobe inspection; try unsupported media
   and confirm it cannot publish.
3. Attach Armenian multiline SRT and VTT, overlapping cues and a timing offset.
   Test private preview, then publish and open the link without owner cookies.
4. In Chrome/Safari network tools, verify video seeks produce HTTP 206 and VTT
   requests succeed under the bucket's CORS rules.
5. On a real iPhone and Android phone, test play/pause, seek, speed, native subtitle
   selection and fullscreen. Keep Armenian selected in iPhone's native player menu.
6. Test URL renewal, owner session expiry/resume and unpublish both before and
   after a viewing URL was issued. The old URL's grace period is expected.
7. Delete and inspect the bucket for source, track versions, multipart remnants
   and (if enabled) object versions. Confirm failed cleanup remains visible.
8. Verify ordinary anonymous requests cannot start/ack/finalize uploads, attach
   subtitles, rename, publish, delete or use owner-only preview APIs.

To prepare the updated source package without deploying:

```powershell
.\.venv\Scripts\python.exe scripts\build_release.py
```

The package excludes video files, local media, databases and secrets. Keep the
existing [public-release guide](PUBLISHING.md) for account/domain setup; Chrome Web
Store publication is optional for this hosted-video workflow.
