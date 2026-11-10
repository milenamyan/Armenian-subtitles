# Local media library

The configured local workspace keeps one video file per film in `data/videos/`, with no film subfolders. Subtitles live in `data/subtitles/<film name>/armenian.srt` and `data/subtitles/<film name>/original.srt` (or `original.vtt` for a VTT source).

Completed files dropped into `data/videos/` are registered in place. The worker skips files already registered, including videos awaiting deletion, so scans do not create duplicate entries. Browser uploads use temporary multipart storage and move into `data/videos/` after inspection. Finish copying a dropped file before scanning; use a `.part` extension while copying.

Playback captions are generated as WebVTT on request from the saved subtitle cues. No extra playback VTT files or backup movie copies are kept. Compatible original H.264 MP4 files may retain multiple AAC-LC stereo audio tracks in this local layout; browser playback uses its default audio track. Deleting a video from the page moves only its movie file into `data/bin/` and hides it from the list. Its subtitles stay in `data/subtitles/`. To restore it, move the file (do not copy it) from `data/bin/` back into `data/videos/`, keeping the filename. The worker restores the same video entry and its subtitle association automatically, or you can click Scan video folder now. Restored videos remain private. Local bin files are not automatically deleted after 24 hours; keep or remove them yourself.

Enable this layout in `.env`, using your absolute data directory path for both root settings:

```dotenv
HAYSUB_MEDIA_STORAGE=local
HAYSUB_LOCAL_FLAT_LIBRARY=1
HAYSUB_LIBRARY_ROOT=C:/path/to/Armenian-subtitles/data
HAYSUB_LOCAL_MEDIA_DIR=C:/path/to/Armenian-subtitles/data
HAYSUB_LOCAL_VIDEO_FOLDER=C:/path/to/Armenian-subtitles/data/videos
HAYSUB_MEDIA_WORKER_ENABLED=1
```

Keep the configured local media secret and metadata database. The database still holds translation progress and cache data for recovery; it does not require extra subtitle exports. Start the app with `Start HaySub.bat` or `python start.py` to supervise the media worker automatically. This layout applies to local storage, not public S3 hosting.


## Local and Cloud player tags

Local playback stays active. The server generates each player page from the current video and subtitle paths, with a commented Cloud `<source>` or `<track>` directly below its active local tag. All existing video and track attributes are retained. The supplied R2 base is combined with `data/` and the exact media path, with spaces and Armenian filenames URL-encoded.

Use View Page Source on a video preview to see its generated pairs. Generation lives in `app/media_sources.py`, in `source_pair`: the active return keeps local tags enabled; the commented return immediately below it switches the generated tags to Cloud. When changing it later, comment the local return and uncomment the Cloud return. Restart HaySub to reload Python changes. The player follows the active tag's `data-media-source`, including when renewing playback access.

`HAYSUB_CLOUD_BASE_URL` can replace the supplied base URL, and `HAYSUB_CLOUD_PATH_PREFIX` defaults to `data`, matching the uploaded bucket layout. The supplied `r2.cloudflarestorage.com` URL is an S3 API endpoint. For direct public browser playback later, use the bucket's public `r2.dev` URL or a custom domain and configure CORS for the player origin. No credentials are placed in HTML and no Cloud request is made while local tags are active.

Cloud SRT tracks are converted to WebVTT in browser memory, including the video's subtitle offset. Existing Cloud VTT tracks stay native. This adds no subtitle copies on disk. Cloud endpoint reachability and CORS have not been validated; local playback remains independent of them.

For a per-film Cloud test, set `HAYSUB_CLOUD_VIDEO_IDS` to a comma-separated list of hosted video IDs in `.env`. Only those films activate their Cloud tags. Set `HAYSUB_CLOUD_BASE_URL` to the reachable public bucket base URL and restart HaySub. Clear `HAYSUB_CLOUD_VIDEO_IDS` to restore local playback.


## Play pasted URLs

Use the **Cloud video** inputs directly in the hosted-video section. Paste a direct HTTP/HTTPS video URL and an optional SRT/VTT subtitle URL, then click **Load & Play**. The same URL form is also available above every existing video player. URLs are used only in the browser and are not saved into your local library.

The existing native video controls, subtitle appearance, speed selector, fullscreen and subtitle toggle are shared with local playback. SRT and VTT caption URLs are loaded into the native track through an in-memory WebVTT blob. Storage must allow the browser's requests through CORS. If browser autoplay is blocked, use the player's Play button. Retry reloads the chosen URLs while preserving position and speed. Normal local playback stays the default until you explicitly load URLs.


## Add a Cloud video to the page

After the pasted video loads, enter its name and click **Add to page** beneath the URL inputs. This saves the exact loaded video/subtitle links and publishes a clickable video entry, then pauses and hides the preview. Click the saved title or **???????? ??????????** to reopen it in the same page. Changing an input without loading it does not change the saved links. Re-adding the same video URL updates that entry rather than making duplicates.

Clicking a video name loads its video and subtitles into the existing player on the same page and scrolls to the player. No new tab or page is opened. The title still contains its normal viewing link for copying or opening explicitly in another tab. Published Cloud entries also appear under **Videos** on the public home page when public hosting is enabled. Visitors can click the name to watch inline with the saved captions. Previously unlisted managed videos are not added to the public catalogue automatically. Only the signed-in owner can add, rename, unpublish, or remove entries in public mode.

Cloud entries store links only: no video or caption file is downloaded into the local library. Removing a Cloud entry removes its listing, leaving the original storage files intact. A Cloud video without captions can also use a saved Armenian library translation; its caption snapshot is served directly from metadata. URLs must remain accessible and storage CORS must allow the viewing website.

Private previews open the shared player directly beneath the selected video title. The **?????** button pauses and hides it. Selecting another title or private preview moves that player to the new video; only one preview plays at a time.
