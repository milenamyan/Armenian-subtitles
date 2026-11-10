# Put HaySub online

For **videos uploaded to HaySub itself**, use [VIDEO_HOSTING.md](VIDEO_HOSTING.md)
in addition to this server setup. Those viewers open a `/watch/...` website link
and need no extension or Chrome Web Store installation. The extension steps below
remain relevant for subtitles displayed over videos on other websites.

## What is ready and what needs your accounts

The code now provides a public read-only subtitle catalog, an extension library
picker, and owner-only upload/translation/rename/publication tools. It is **not
online yet**. You need a GitHub account, a hosting account, and a Chrome Web Store
developer account. No hosting or store purchase/submission has been made here.

The first release lets viewers search and choose prepared Armenian subtitles or
use local SRT/VTT files. Viewers do not create paid translations. Only you sign
in to the website to manage the library. A subtitle is private until you publish
it. Match a translation to the exact movie release/episode; it is not automatic
film recognition.

Local verification: **170 Python tests and 64 JavaScript checks passed**. These
cover owner authentication/CSRF, private-to-public publication, import validation,
catalog downloads, extension selection, offline/quota failures and safe packages.
They are not evidence of Chrome Web Store approval or a working public deployment.

## 1. Prepare the hosting files on Windows

From this project folder, run:

```powershell
.\.venv\Scripts\python.exe scripts\build_release.py
.\.venv\Scripts\python.exe scripts\export_library.py
```

This creates:

- `dist/haysub-server-source.zip`: hosting source, with no `.env`, API key,
  database, source subtitle cache or local translations.
- `dist/owner-translations.zip`: your completed Armenian SRT files for importing
  on the hosted owner page. **Keep this ZIP yourself. It is not the extension.**

You can leave your existing local HaySub running as before. Its `.env` is not
changed by these scripts. Do not set public mode on your local HTTP server;
public owner login requires HTTPS secure cookies.

## 2. Create the code repository

1. Create a **private** GitHub repository such as `haysub-server`.
2. Extract `haysub-server-source.zip` into a new folder.
3. On GitHub, choose **Add file → Upload files**, then upload the extracted
   contents, preserving the `app`, `static`, `scripts` and `docs` folders.
4. Commit the files. `Dockerfile` and `render.yaml` must be at the repository root.

Upload only this source package, never the entire original project folder. In
particular, do not upload `.env`, `data/haysub.sqlite3`, or owner-translations.zip.

## 3. Create the hosted server on Render

This guide uses [Render](https://render.com/docs/docker). Your SQLite library
requires a persistent disk. Render offers persistent disks on paid services;
check the displayed plan and disk costs before creating the service. The free
ephemeral filesystem would lose your library across redeploys.
See [persistent disk documentation](https://render.com/docs/disks).

1. Sign up/sign in to Render and connect your private GitHub repository.
2. Choose **New → Web Service**, select that repository, and use the **Docker**
   runtime. Name the service, for example `haysub-milena` if available.
3. Select a paid instance supporting a persistent disk. Under Advanced, add a
   disk mounted at **`/var/data`**, initially 1 GB. Keep one instance and one worker.
4. Configure the following environment variables in Render, not in GitHub:

| Variable | Value |
| --- | --- |
| `HAYSUB_PUBLIC` | `1` |
| `HAYSUB_PUBLIC_URL` | The exact HTTPS service address, such as `https://haysub-milena.onrender.com`, no path |
| `HAYSUB_DB` | `/var/data/haysub.sqlite3` |
| `HAYSUB_ADMIN_TOKEN` | A randomly generated owner password of at least 32 characters |
| `HAYSUB_CONTACT_EMAIL` | An email address you are willing to display publicly for support/privacy |
| `GEMINI_API_KEY` | Your own Gemini key, only if you will create new translations online |
| `GEMINI_MODEL` | Your tested Gemini model, only if translating online |

You may use a password manager to generate the owner password. Save it privately;
viewers must never receive it. Neither the key nor password belongs in the extension.

5. Use `/healthz` as the health-check path, and create/deploy the service. Docker
   supplies the startup command and listens on Render's `PORT`. If Render assigns
   a different address than expected, update `HAYSUB_PUBLIC_URL` and redeploy.
   A service whose public URL/password is missing fails closed at startup.
6. Open the HTTPS address. You should see **Published translations**, with no
   management/upload tools. Open `/admin` to sign in with your owner password.

`render.yaml` is also included for a [Blueprint deployment](https://render.com/docs/infrastructure-as-code).
If using a Blueprint, fill its requested secrets, set the actual assigned service
URL, and redeploy. A custom domain is optional; keep the chosen origin stable
because the extension's network permission names that origin.

## 4. Move and publish your translations

1. Extract `dist/owner-translations.zip` on your computer.
2. Open `https://YOUR-SERVER/admin` and sign in.
3. In the library, use **Import Armenian file (no Gemini)** to import each SRT.
   Imported files are validated as Armenian and remain private.
4. Rename each item to a useful film/episode/release title. The ZIP's `titles.json`
   records your original titles if the export filenames include an ID prefix.
5. Click **Publish for viewers** for each translation you want to share. Only
   share subtitle text you are permitted to distribute.
6. To add new translations later, use the existing file translator on `/admin`,
   wait for completion, rename if needed, then publish. Your key/quota pays for
   those owner translation requests. Importing/downloading a prepared file does
   not call Gemini.

Click **Unpublish** to prevent future public downloads. It cannot remove copies
already saved on a viewer's computer. Your private source files and partial
translation jobs are never in the public catalog. Back up the database using
SQLite's backup facility; do not remove the persistent disk when redeploying.

## 5. Verify the real server and build the public extension

Replace the example address below with the actual address from Render:

```powershell
.\.venv\Scripts\python.exe scripts\check_public_server.py https://YOUR-SERVICE.onrender.com
.\.venv\Scripts\python.exe scripts\build_release.py --server-url https://YOUR-SERVICE.onrender.com
```

The first command checks the deployed homepage, health, privacy page, owner
protection, catalog and one published download. It never logs in or calls Gemini.
The second creates **`dist/haysub-chrome-store.zip`**, with:

- Your exact HTTPS server host permission and network policy.
- A public read-only configuration, with owner translation requests disabled.
- Icons and all extension runtime files, with no local API key or database.

This command does **not** publish the ZIP or verify that Chrome accepts it.
Do not share the original development `/extension` folder: it targets localhost.
If the server address changes, rebuild and submit an updated extension.

Before submitting, extract this public ZIP into a separate folder, open
`chrome://extensions`, enable Developer mode, click **Load unpacked**, and select
that extracted folder. Disable the old development HaySub to avoid two overlays.

Manually check in Chrome:

- Turn off your local Python server. On YouTube, search the shared library, choose
  a published Armenian file, close the popup and check subtitles.
- On an embedded-video site, choose the video frame and allow only its domain.
- Check pause, seek, speed, fullscreen, page/video changes and timing offsets.
- Reopen Chrome and verify the saved selection remains. Disconnect the network
  and verify a previously saved file still plays.
- Check malformed local uploads, full storage, unavailable server and empty search.
- In an unsigned browser session, confirm library management and translation
  endpoints are unavailable; private/unpublished translations must not download.
- Rename/unpublish a translation on `/admin`, refresh the extension library and
  confirm the new title/visibility. Existing downloaded copies remain local.

No live Chrome, Kinogo or public hosting check was performed in this workspace.
Docker is installed but its daemon was unavailable, so the Linux container build
also needs verification by the hosting deployment.

## 6. Publish to the Chrome Web Store

1. [Register your Chrome Web Store developer account](https://developer.chrome.com/docs/webstore/register/).
   Google requires a one-time registration fee; complete it yourself.
2. Go to the developer dashboard and create a new item. Upload
   **`dist/haysub-chrome-store.zip`**. Follow the
   [official publishing workflow](https://developer.chrome.com/docs/webstore/publish).
3. Use the draft listing and permission explanations in [STORE_LISTING.md](STORE_LISTING.md).
4. Set website to your server homepage and privacy policy to
   **`https://YOUR-SERVER/privacy`**. Set your public support contact.
5. Supply real screenshots demonstrating your own test subtitle/video and the
   library. Do not submit the earlier private chat screenshots. The generated
   128px icon is in `extension/icons/icon128.png`; an icon and at least one real
   screenshot are required. [Image requirements](https://developer.chrome.com/docs/webstore/images).
6. Answer the store's current privacy/data-use questions accurately: catalog search
   terms and download requests go to your server; settings/subtitles/video
   associations stay locally in the public extension. Hosting sees ordinary
   network request information. Local SRT uploads are not sent for translation
   in this public release. No remote executable code is loaded.
7. Choose public visibility, submit for review and wait for Google's decision.
   Store approval is not guaranteed and no approval time is promised.
8. After publication, copy the actual store listing URL. Set `HAYSUB_STORE_URL`
   to it in Render and redeploy. The public homepage will then show its install link.

## 7. What to send your friends

Send only the **actual published Chrome Web Store listing link**, with the message
in [FRIENDS.md](FRIENDS.md). They click **Add to Chrome**, open their film, choose
HaySub from Chrome's extensions menu, and select your translation. They do not
need Developer mode, Python, a key, your password or access to your owner page.

There is no real install link until the account/deployment/store steps above
are completed. For a small test before store approval, friends can manually load
the extracted **public** ZIP using Developer mode, but that is a tester workflow,
not the final nontechnical installation experience.
