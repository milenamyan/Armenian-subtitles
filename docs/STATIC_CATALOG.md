# HaySub static catalog on Render

This is a buildless website in `catalog-site/`. Films, posters and permanent public
R2 media links are saved in `catalog.json`, which is deployed with the site. No
Python process, SQLite database, persistent disk, Gemini key or owner password is
needed on the static host. The video bytes remain in R2. R2 storage/delivery and
hosting limits still depend on your accounts.

## First deployment

1. Extract `dist/haysub-static-catalog.zip` to a separate folder. Upload its
   `catalog-site` folder to your GitHub repository, preserving its contents.
   You can also commit the `catalog-site` directory directly from this project.
2. In Render select **New > Static Site**, connect the repository and branch.
3. Leave **Root Directory** empty, set **Build Command** to `node catalog-site/build.cjs`, and set
   **Publish Directory** to `catalog-site`. No environment variables are needed.
   The build writes the deployment timestamp displayed at the top of both pages
   in Yerevan time. For an existing Render site, update this Build Command once;
   every subsequent deployment refreshes the timestamp automatically. If the
   repository contains the catalog files at its root, use `node build.cjs`.
4. Deploy and copy the new HTTPS address. A new service will normally receive a
   different address from the old web service.
5. In Cloudflare R2 > your bucket > Settings > CORS Policy, add the new website
   origin (scheme + hostname, no path or trailing slash) to `AllowedOrigins`.
   Preserve the old origins if you still use them. Allow GET/HEAD and Range.
6. Open the site's root URL in an incognito window. Test each film, Armenian
   captions, seeking, and mobile fullscreen. Direct `.vtt` tracks are preferable
   for native mobile playback; `.srt` tracks are converted to WebVTT in memory.
   No autoplay is forced. Some mobile players require selecting Հայերեն from
   the native caption menu. No real-phone fullscreen verification was performed
   by the automated checks.
7. Optional: in Render **Redirects/Rewrites**, add `/catalog` -> `/` (Redirect,
   status 301) and `/catalog/` -> `/` so those older catalog paths also work on
   the new domain. Old `/watch/ID` addresses are not reused: share new
   `watch.html?id=ID` links. The old service domain will not automatically point
   to the new site. Keep the old service until the new site is verified; manage
   any paid service cancellation yourself afterward.

Official guides: https://render.com/docs/static-sites and
https://developers.cloudflare.com/r2/buckets/cors/

## Add, rename or remove a film

Use your local HaySub owner page as the source of truth. With
`HAYSUB_STATIC_CATALOG_SYNC=1` in the local `.env`, these actions automatically
update `catalog-site/catalog.json` and its public cover images:

- **Add to page** adds a published Cloud video.
- **Publish / Unpublish** sets `"published": true` or `"published": false`.
  Hiding retains the entry, links, title and cover in the file; the website skips
  it in both the catalog and player. JSON does not support comment syntax, so the
  boolean acts as the on/off switch. Never-published private films are excluded.
- Renaming changes its title; saving a cover copies the new image into
  `catalog-site/assets/posters/` with a versioned filename.
- The **ՆՈՐ պիտակ** checkbox immediately saves each film's `is_new` flag.
  Newly added films start checked; previously saved films keep their setting.
  A viewer's browser hides the badge for films that viewer has already opened.
  Checked films display a purple **ՆՈՐ** badge on their poster; unchecking removes
  it. The live static website receives the change with the next catalog deploy.
- Each film's owner-only **Ենթագրերի բարձրություն** controls move the captions
  up/down in its open owner preview. Click **Պահել դիրքը** to save that film's
  height. New videos default to 10%; existing saved positions are preserved.
  It persists in SQLite and exports as `subtitle_height` (0–40 percent
  above the bottom; 0 uses browser placement). Viewers have no height controls.
  The published site uses this value after the changed `catalog-site` files
  are committed and deployed. Device-native players may apply their own
  caption layout rules during native fullscreen.
- Deleting a Cloud entry or moving a managed film to the bin removes its listing
  and generated cover. Restoring a binned film keeps it private until published.

Restart the local Python server after enabling sync. The current library is
exported at startup, after successful owner actions, and when the video list
refreshes. The local page reports a separate export error if writing fails and
retries on refresh. Local-only films without configured public Cloud delivery
are skipped, with a warning. No videos are uploaded to R2 or GitHub by this sync.
Uploaded videos must already exist at their public Cloud links to play remotely.

**The live website updates only after you commit and push the changed
`catalog-site` folder to the GitHub repository connected to Render.** Include
`catalog.json`, new cover files and deleted old cover files. There is no automatic
GitHub push. Avoid editing GitHub's JSON separately: the next local sync replaces
it from your library. Existing permanent media links remain accessible after a
film is removed from the catalog; removing a listing does not revoke R2 access.
Hidden entries remain readable in the publicly hosted JSON file; hiding is a
catalog visibility setting, not private media storage.

For an intentionally manual setup, set `HAYSUB_STATIC_CATALOG_SYNC=0` and edit
`catalog-site/catalog.json` directly. Add an object to `films`, separating objects
with commas:

```json
{
  "id": "my-film-2026",
  "title": "Իմ ֆիլմը",
  "video_url": "https://YOUR-PUBLIC-MEDIA-DOMAIN/data/videos/film.mp4",
  "subtitle_url": "https://YOUR-PUBLIC-MEDIA-DOMAIN/data/subtitles/film/armenian.srt",
  "subtitle_offset": 0
}
```

Use a unique stable ID for each film. Positive offset delays SRT captions. Use
UTF-8 subtitles. A `poster_url` (permanent HTTPS image URL) and `duration` (seconds)
are optional. Keep entries in the order you want them displayed. Removing an
entry removes its listing on the next deploy; it does not delete its R2 objects
or revoke public media links. All manifest contents are public. Never paste
passwords, keys, expiring signed URLs, S3 API endpoints or private film links.

Commit the change; Render redeploys if automatic deploys are enabled. Refresh
the site to see it. GitHub stores the film list across deployments. Browser
watch progress is stored on each device for that website origin; changing the
domain does not carry old browser progress across.

## Build/check a package locally

From the original project folder:

```powershell
.\.venv\Scripts\python.exe scripts\build_static_catalog.py
```

This validates the catalog and packages it, preserving edits in catalog.json.
While local sync is enabled, the running local app automatically replaces the
file from its library. The CLI's explicit `--export-local` can do this on demand.
The export reads the database without changing it, includes ready Cloud-selected
films that are published or were previously published, and excludes bin,
never-published private, and local-only entries. Previously published films that
are now hidden are retained with `"published": false`, including their covers. It
loads the public Cloud base, selected IDs and prefix from the local `.env` but
does not copy that file or its secrets to the website. Do not mix automatic
library sync with independent GitHub-only film edits.

To preview, use HTTP rather than opening index.html as a file:

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 --directory catalog-site --bind 127.0.0.1
```

Open http://127.0.0.1:8080/ . For media playback, also allow that local origin in
the R2 CORS policy. Stop the preview with Ctrl+C.
