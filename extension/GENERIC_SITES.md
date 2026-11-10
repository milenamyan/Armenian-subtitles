# HaySub on other video sites

Version 1.2 adds click-to-activate subtitle overlays for standard HTML5 videos on
HTTP/HTTPS websites. This includes the type of player used by many film sites,
but **Kinogo and every possible player have not been verified in Chrome**.
YouTube's existing caption/translation flow is preserved.

## Use it

1. Reload HaySub at `chrome://extensions`, then refresh the video page.
2. Start the website's video and click the HaySub icon.
3. Select your matching Armenian SRT/VTT file. It appears near the bottom of the
   video. Playback remains controlled by the original site.
4. If there are multiple videos in the selected frame, select the right player.
5. Use the existing font, color, position and timing-offset controls as needed.

On other sites, local file display is the default: no Python server is needed
for an already-translated file. If you want an English/Russian file translated,
enable **Թարգմանել հայերեն** and run the existing backend at
`http://127.0.0.1:8000`. Only the subtitle file is sent to that backend, not the
site URL or video. Automatic caption retrieval remains **YouTube-only**.

## If no video is detected

Many sites put the actual player in a cross-origin iframe:

1. Click **Գտնել ներկառուցված նվագարկիչները** (Find embedded players).
2. Chrome requests the optional `webNavigation` permission to list the frames
   in this tab. You can decline; direct video overlays still work.
3. Pick the actual player frame, then click **Թույլատրել այս նվագարկիչը**.
4. Approve access to that specific frame's origin. The popup reloads with the
   selected player; choose your subtitle file.

The frame list includes origins/paths, not media stream addresses. Ads may also
have frames; choose the movie player. No scripts are injected indiscriminately
into every frame. If permission is denied or the site forbids extension access,
HaySub reports an error instead of bypassing the restriction.

## Permissions and behavior

- `activeTab` provides temporary access when you click HaySub; `scripting`
  injects the packaged overlay scripts into the chosen page/frame.
- The declared `https://*/*` and `http://*/*` entries are **optional** host
  permissions, not permanent access to all sites at installation. The UI asks
  for only the selected embedded-player origin.
- The only required host access remains the existing loopback backend.
- Subtitle file/offset associations use a hashed identity for the exact top URL,
  selected frame URL and video index. Filenames or domains alone do not identify
  a movie, and the same file must match the video's edition/timing.
- A top-page route change clears a selected child-frame overlay. Replaced media
  is guarded: upload/select the appropriate file again before displaying text.
  An old job's incremental output cannot unlock a changed-video overlay.
- The overlay remains pointer-transparent and uses `video.currentTime` for all
  timing. The page-route watcher has a separate URL-check timer; it does not
  advance subtitle time or modify playback.

Chrome internal pages, extension pages and restricted browser pages are not
supported. Shadow-DOM/nonstandard players, opaque frames and some protected
players may not expose an accessible HTMLVideoElement. Player-container
fullscreen can include the overlay; native `<video>` fullscreen and
Picture-in-Picture cannot show an ordinary sibling DOM overlay.

No cookies are extracted, and no video is downloaded, proxied or decrypted.
This change does not bypass DRM, logins, geo restrictions or player access checks.

## Verification

### Embedded-player recovery (1.2.1)

If the popup says there is no video in this frame while the movie is playing,
HaySub is connected to the outer page rather than the embedded player.
Reload HaySub at `chrome://extensions`, refresh the movie page, start playback,
then click **Գտնել ներկառուցված նվագարկիչները**. Choose the film player frame
and click **Թույլատրել այս նվագարկիչը**. Approve access to that player's domain.
If the selected frame has no video, select another frame; advertising frames
and intermediate wrappers are not the movie player.

Discovery puts already permitted frames containing video first and reconnects
to an available permitted player on reopening. Unapproved domains are not probed.
On manual frame selection, an SRT previously uploaded to the outer page with no
video is copied to the selected player if that player has no saved subtitle file.
It does not overwrite the selected player's existing subtitles.

The recovery changes passed 40 extension tests using Chrome API stand-ins.
Actual Kinogo behavior and permission prompts still require manual Chrome testing.

**35 extension tests and 130 Python tests passed**, including selected-frame
activation, permission denial, generic-page clock sync, source replacement,
cross-frame route cleanup and file-only backend translation. JavaScript syntax
checks also passed. These use controlled DOM/Chrome API stand-ins; no real
Chrome or Kinogo browser verification was performed in this environment.

```powershell
node --test extension/tests/core.test.cjs extension/tests/content.test.cjs extension/tests/popup.test.cjs extension/tests/backend.test.cjs extension/tests/translation-client.test.cjs extension/tests/page-access.test.cjs
.\.venv\Scripts\python -m pytest -q
```

Manual Chrome checks still needed: a direct video page; same/cross-origin iframe
with permission allowed and declined; multiple-player selection; pause, seek,
speed and buffering; player fullscreen; same-page route/media replacement; and
the actual target Kinogo page. Automated DOM/API stand-ins do not verify real
player layout or host permissions in Chrome.

Official references: [activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab),
[scripting](https://developer.chrome.com/docs/extensions/reference/api/scripting),
[optional permissions](https://developer.chrome.com/docs/extensions/reference/api/permissions).
