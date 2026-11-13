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
3. Leave **Root Directory** empty, leave **Build Command** empty, and set
   **Publish Directory** to `catalog-site`. No environment variables are needed.
   If the form requires a build command, use `echo Static catalog ready`.
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

Edit `catalog-site/catalog.json` in GitHub. Add an object to `films`, separating
objects with commas:

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
Only explicit `--export-local` replaces that file from the local SQLite database.
That export reads the database without changing it, includes only published,
ready Cloud-selected films, and excludes bin/private/local-only entries. It
loads the public Cloud base, selected IDs and prefix from the local `.env` but
does not copy that file or its secrets to the website. Do not use export after
making GitHub-only changes unless you intend to replace the list.

To preview, use HTTP rather than opening index.html as a file:

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 --directory catalog-site --bind 127.0.0.1
```

Open http://127.0.0.1:8080/ . For media playback, also allow that local origin in
the R2 CORS policy. Stop the preview with Ctrl+C.
