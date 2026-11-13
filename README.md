# HaySub

## Static public catalog (no server or persistent disk)

The buildless public website is in [`catalog-site/`](catalog-site/). Its film list
is stored in `catalog.json` and videos play directly from public R2 links.
See [Render Static Site setup and catalog updates](docs/STATIC_CATALOG.md).
Run `.\.venv\Scripts\python.exe scripts\build_static_catalog.py` to validate and
package it as `dist/haysub-static-catalog.zip`. Editing this static catalog does
not change the separate local Python app or its library.

## Overlay on other video sites

HaySub 1.2 can be activated on standard HTML5 video pages outside YouTube.
Reload the extension, refresh the site, start the video, click HaySub and choose
a matching subtitle file. The popup can select a video or request access to a
specific embedded-player frame. Already-translated files work without Python;
optional file translation uses the same backend. Automatic caption retrieval
is still YouTube-only. See [other-site instructions and limitations](extension/GENERIC_SITES.md).

This is not a guarantee for every site/player. The actual Kinogo player has not
been tested in Chrome; native video fullscreen/PiP and inaccessible players have
limitations. Broad website permissions are optional and requested per selected
embedded origin, rather than granted for all browsing by default.
Verification: **35 extension tests and 130 Python tests passed**, with JavaScript
syntax checks. Real site/player layout and Chrome permission prompts still need
manual verification; automated checks use DOM and Chrome API stand-ins.

## Cache recovery and persistent resume

File uploads now check saved translations **before starting missing work** and
display the actual restored count immediately. An explicitly compatible older
prompt cache is reused only after exact source/timestamp/context/model matching
and Armenian-text validation. Original cache entries remain intact; reuse records
retain their source version and model. New standalone jobs persist source files
and validated progress in SQLite, so reopening a remembered job after a server
restart restores its progress instead of resetting to zero.

Older in-memory jobs need the exact same SRT uploaded once because their source
was never saved. The page will show how many cues actually match; the historical
1,614-cue file was not available to confirm its exact restored count yet.
See [CACHE_RECOVERY.md](CACHE_RECOVERY.md). A SQLite backup was saved in `data/`
before enabling the new resume workflow. **129 Python tests and 4 file-translator
UI tests passed**, including zero-Gemini cache reuse and restart recovery.

Cue-ID recovery: each Gemini response schema now lists the exact target IDs and
cue count. Missing, duplicate or reordered IDs are still rejected; a malformed
batch switches to individual-cue repair instead of repeating that batch. Each
cue has at most three attempts (including the initial batch attempt), and the
existing 165-second overall chunk deadline remains in force. Single-cue repair
can use more requests per chunk, but validated lines are cached individually in
the partial cache and reused on retry. Valid completed caches are unchanged.

Verification: **119 Python tests passed**, including malformed-ID recovery and
bounded failure with partial-cache preservation. A bounded live Gemini request
using an original test sentence confirmed that the configured model accepts the
exact-ID JSON schema and returns validated Armenian text. This was a schema smoke
test, not a re-run of the user's full failed subtitle chunk.

Standalone job source and progress now persist in SQLite. Only older jobs created
before that change need the same SRT uploaded again for verified cache restoration.

Music-only annotations such as `[Music]`, `[музыка]`, `[երաժշտություն]` and music
symbols are intentionally silent. They are completed locally without a Gemini
target, hidden in web/extension playback and omitted from translated SRT downloads.
Existing cached music labels are filtered too; valid dialogue caches are retained.
Sentences about music and lyrics containing notes are preserved, while standalone
music-label lines in mixed cues are removed from display. Detection uses an exact
English/Russian/Armenian label list, not audio analysis or speech recognition.

The file-translator form now constrains its grid/input widths and wraps long
filenames so the translation button stays within the page. A screenshot showing
`1164 / 1614` and a current chunk at `14s` indicates processing, not an error by
itself. Live Gemini latency can vary. Refresh the page for layout changes and
reload the extension for cached-label display filtering; restart the backend to
apply music-skipping to new translation requests and downloads. If a standalone
file job is lost after restarting, reupload the same file to reuse completed cache.

Verification of this change: **114 Python tests passed**, plus shared web/extension
music tests and the existing JavaScript checks. Music classification, skipping
Gemini, legacy cache filtering, dialogue preservation, export timing and compact
extension completion counts were checked without live Gemini requests. The layout
change has not been visually verified in Chrome in this environment.

```powershell
node --test tests/music.test.cjs
```

## Chrome extension — Armenian subtitles on YouTube

The standalone Manifest V3 extension is in [`extension/`](extension/README.md).
It displays uploaded SRT/VTT files **on top of videos on youtube.com**, using the
video's own playback time. It now connects to the existing local Python backend
for Armenian translation. API keys remain exclusively in the backend `.env`.
Turn off **Թարգմանել հայերեն** for offline display of a file in its original
language. The existing web app and file-download translator remain available.

Windows installation:

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select `C:\Users\Milena Mehrabyan\Desktop\Armenian-subtitles\extension`.
5. Open or refresh a YouTube video, click the HaySub extension icon, and upload
   an SRT/VTT file. Try the original [`extension/sample.srt`](extension/sample.srt).

For translation, start the backend first (stop the existing server with Ctrl+C before restarting to load code changes):

```powershell
.\.venv\Scripts\python start.py
```

Reload HaySub at `chrome://extensions`, allow the added loopback-host permission
if Chrome requests it, and refresh YouTube. With **Թարգմանել հայերեն** enabled,
uploaded English/Russian subtitles are translated into Armenian. If no file is
saved, opening the popup automatically starts YouTube-caption retrieval and
translation. Creator-provided captions are preferred, then automatic captions;
English is preferred within each source, with other available original languages
also supported by the extension path. Machine-translated YouTube tracks are
excluded. A file upload replaces the automatic-caption job and takes priority.

Translated chunks appear as they become ready. The popup can be closed: a
content-page coordinator polls progress while the YouTube tab remains open.
Stop/retry controls are available. Missing or inaccessible captions produce an
error with a file-upload fallback; no speech recognition is implemented.

The popup provides enable/disable, font size, text color, background opacity,
vertical position, per-video timing offset, local storage usage and clear controls.
Positive offsets delay subtitles; negative offsets show them earlier. Settings
and file associations persist locally. See the [extension guide](extension/README.md)
for architecture, limits and the manual Chrome checklist.

The 26 extension tests run with:

```powershell
node --test extension/tests/core.test.cjs extension/tests/content.test.cjs extension/tests/popup.test.cjs extension/tests/backend.test.cjs extension/tests/translation-client.test.cjs
```

These tests passed using Node and DOM/Chrome API stand-ins. A real Chrome session
was unavailable; loading the unpacked extension and visual checks on YouTube must
still be performed manually. The following sections describe the separate web app.

Backend integration verification: the current Python suite passed **85 tests**.
The extension tests cover incremental Armenian results, uploaded-file priority,
automatic caption startup, cancellation, stale-result protection, offline/quota
errors, server-restart recovery and popup-independent polling. No new live Gemini
call or real Chrome integration check was performed in this change.

## Download a translated Armenian subtitle file

Translation validation now repairs individual failed cues instead of retranslating
an otherwise valid chunk. Valid lines are held in a separate partial cache and
merged only after every target cue passes validation; missing or source-language
dialogue is never filled in as a successful Armenian result. Short unrecognizable
phonetic fragments are requested in Armenian script without inventing meaning.
ID order and timestamps remain unchanged. The three-attempt limit still applies.
Manual retries reuse the validated partial cache. The updated prompt has its own
cache version so results from different prompt versions are not mixed.

Verification for this repair: **88 Python tests passed**. The previously failing
cue 30 of `eojK4yj3y2A` was translated and validated in a bounded live Gemini check
in 5.4 seconds. This verifies that cue, not every later cue of the video. Restart
the backend and use the extension's retry button to continue.

At the bottom of the HaySub web page, **Ենթագրերի թարգմանիչ** accepts an SRT or
VTT file without a YouTube URL. Open **http://127.0.0.1:8000/#file-translator**,
choose an English or Russian UTF-8 file (up to 2 MB), and click **Թարգմանել հայերեն**.
The existing backend Gemini configuration is required; API keys stay in `.env`.
The translation uses the same chunk validation, adjacent context, bounded retries
and SQLite cache as video subtitles. The progress bar counts completed cues.

When all cues are translated, click **Ներբեռնել հայերեն SRT** to download
`<original-name>_hy.srt`. The UTF-8 SRT includes a BOM for Windows compatibility
and preserves valid cue timestamps. VTT input is also exported as SRT.
Partial translations cannot be downloaded as a completed Armenian file.
On an error, the retry button resumes missing chunks without repeating completed
work. During the same server session, refreshing the page resumes status polling.
If the server restarts, the remembered job ID restores saved progress; click Retry
to continue. Older jobs without saved source require one matching reupload.

To use the result on YouTube, open the HaySub Chrome extension and select the
downloaded Armenian SRT with translation disabled. The extension can also translate
files and YouTube captions directly through the backend. Restart the Python server after updating the project to load the new
file-translation endpoints.

Verification: **58 Python tests** and **3 new file-translator UI tests** passed,
including cached translation/download, UTF-8 round trip, timestamp boundaries,
VTT export, partial-download rejection, failed-chunk retry, configuration errors,
progress and download-link visibility. These checks used controlled API responses
or existing test caches, not a new live Gemini call or a real browser session.

```powershell
.\.venv\Scripts\python -m pytest -q
node --test tests/file-translator.test.cjs
```

**Uploaded English subtitle files are translated into Armenian using Gemini.**
Upload an `.srt` or `.vtt` file and click the watch button. The uploaded file is
the source; YouTube captions are not retrieved when a file is supplied.
Cue timestamps stay intact. The first translated chunk enables playback and
later chunks continue in the background. Armenian mode displays translations;
bilingual mode adds the uploaded English text. Source mode displays the file
unchanged. Translation, retry and cache also work for uploads reopened from history.
Without Gemini configuration, only source-language display is available.

Uploaded files may contain empty placeholders or zero-duration cues; those are
skipped because they cannot be displayed. Valid cues retain their timestamps.
Negative durations still produce an error identifying the original cue number
and timestamps. A file with no remaining displayable cues is rejected.

Restart the server and refresh the browser after this update. Verified with
47 Python tests and three Node checks, including uploaded-file translation,
history reload, retry, bilingual display, iframe reuse and buffering recovery.

YouTube buffering is reported separately below the video, including the native
player state and loaded percentage. After 15 seconds of buffering a reload button
appears; it recreates the player at the current timestamp without deleting captions
or translations. Adding a new subtitle file to the same video reuses the existing
iframe. Subtitle text is updated only when it changes. No automatic reload loop,
quality-forcing API, video proxy, pause, or seek is used during subtitle polling.
Real embedded playback/network behavior still requires browser verification:
the available tools cannot inspect the user's YouTube iframe network requests.

Տեղային FastAPI հավելված՝ YouTube դիտելու և անգլերեն ենթագրերը արևելահայերեն թարգմանելու համար։ Ենթագրերը ստացվում են YouTube-ից կամ քո վերբեռնած SRT/VTT ֆայլից։ Տեսանյութն ու ձայնը չեն ներբեռնվում։

## Windows PowerShell

Python 3.11 կամ ավելի նոր տարբերակով՝

```powershell
cd "C:\Users\Milena Mehrabyan\Desktop\Armenian-subtitles"
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Այս միջավայրում տեղադրված ճշգրիտ տարբերակները պահպանված են `requirements.lock.txt`-ում։ Դրանք վերարտադրելու համար տեղադրման հրամանում օգտագործիր `-r requirements.lock.txt`։

`.env`-ում լրացրու `GEMINI_API_KEY`։ Հասանելի մոդելները ստուգիր քո բանալիով՝

```powershell
.\.venv\Scripts\python list_models.py
```

Ցուցակից ընտրած մոդելի անունը գրիր `GEMINI_MODEL=` դաշտում։ Մոդելի անունը կանխադրված չէ․ հասանելիությունը կախված է քո հաշվից։ Հավելվածը չի միացնում վճարում և չի ենթադրում անվճար քվոտա։ API օգտագործումը ենթարկվում է քո հաշվի պայմաններին։

```powershell
.\.venv\Scripts\python start.py
```

Բացիր **http://127.0.0.1:8000**։ Կանգնեցնելու համար՝ Ctrl+C։ `.env`-ի փոփոխությունից հետո վերագործարկիր սերվերը։ Առանց բանալու վերբեռնումը, YouTube դիտումը և բնագրի համաժամեցված ցուցադրումը աշխատում են։ Ընտրիր «Միայն բնագիր» ռեժիմը։

## Օգտագործում

Տեղադրիր YouTube URL և սեղմիր դիտման կոճակը։ Եթե ֆայլ չես ընտրել, հավելվածը ֆոնում նախ փնտրում է հեղինակի անգլերեն ենթագրերը, ապա՝ անգլերեն ավտոմատ ենթագրերը։ Կարող ես ընտրել UTF-8 SRT կամ VTT (առավելագույնը 2 MB). քո ֆայլը միշտ ունի առաջնահերթություն, և այդ դեպքում YouTube-ից ենթագրեր չեն հարցվում։ Սխալ վերբեռնված ֆայլը վերադարձնում է սխալ, չի փոխարինվում ավտոմատ աղբյուրով։

Առաջին 12 ենթագրերի թարգմանությունից հետո հավելվածը փորձում է սկսել դիտումը։ Բրաուզերը կարող է պահանջել Play-ի ձեռքով սեղմում։ Հաջորդ հատվածները մշակվում են ֆոնում։ Ժամանակագծով տեղափոխվելիս հաջորդ հարցումը նախապատվություն է տալիս ընտրված հատվածին. արդեն ընթացող հարցումը չի ընդհատվում։ Անպատրաստ հայերեն ենթագրի դեպքում երևում է սպասման հաղորդագրություն, ոչ թե բնագիրը որպես թարգմանություն։ Առանց Gemini կարգավորման ստացված անգլերեն ենթագրերը հասանելի են «Միայն բնագիր» ռեժիմում։

Ենթագրերի բացակայության, YouTube-ի սահմանափակման կամ կապի սխալի դեպքում երևում է պատճառը և «Վերբեռնել ենթագրեր» կոճակը։ Ընտրիր ֆայլ և կրկին սեղմիր դիտման հիմնական կոճակը։ «Կրկնել ենթագրերի ստացումը» կոճակը նոր փորձ է կատարում միայն քո սեղմումով. անվերջ կրկնվող հարցումներ չկան։ HTTP 429-ի դեպքում սպասիր, հետո փորձիր կրկին կամ օգտագործիր ֆայլ։

«Հայերեն + բնագիր», տառաչափը և շեղումը հասանելի են նվագարկիչի ներքևում։ Դրական շեղումը ուշացնում է ենթագրերը։ Տեքստի ժամանակների վրա սեղմելը տեղափոխում է տեսանյութը։ Պատմությունը պահվում է SQLite-ում։ Նախորդ տեսանյութը բացելիս քեշավորված թարգմանությունները վերականգնվում են նույն հերթով։

## Կառուցվածք

Stalled translation protection: each Gemini attempt has a 45-second async deadline in addition to the SDK network timeout. A chunk has a 165-second overall deadline. A timed-out chunk stops with a retryable error while completed chunks remain cached. The progress message shows the active cue range and elapsed seconds. Restart the server after updating to apply these limits to previously stuck jobs.

Live troubleshooting: the configured `gemini-3.8-flash` model repeatedly returned HTTP 503 after the first 12 cues. After confirming account availability with `list_models.py`, cues 13–24 of `lw2oyHjBmGM` were successfully translated and validated using `gemini-3.1-flash-lite` in 3.1 seconds. The local `.env` model was switched to that model. This verifies one previously failing chunk, not uninterrupted translation of the entire movie. Restart the server to load the changed model; translations cached for different models remain separate.

Gemini-ի HTTP 503-ը ծառայության ժամանակավոր ծանրաբեռնվածություն/անհասանելիություն է։ Հավելվածը կատարում է առավելագույնը երեք փորձ՝ 5 և 15 վայրկյան դադարներով։ Եթե չի վերականգնվում, սպասիր և սեղմիր «Կրկնել թարգմանությունը»․ պատրաստ հատվածները պահպանվում են։ 429 սահմանաչափի և բանալու/մոդելի սխալների հաղորդագրությունները տարբերակված են։ 503-ի վերականգնումը, փորձերի սահմանը և քեշի պահպանումը ստուգված են վերահսկվող թեստային պատասխաններով, առանց իրական Gemini հարցումների։

- `app/subtitles.py` — URL-ների ստուգում, SRT/VTT վերլուծում։ Ժամանակային միջակայքը ներառում է սկիզբը և բացառում վերջը։
- `app/captions.py` — yt-dlp Python ինտեգրում (`extract_info(..., download=False)` և `skip_download=True`), անգլերեն VTT ուղիների ընտրություն և միայն ենթագրի տեքստի ստացում։ Տեսանյութի/ձայնի ֆայլ կամ FFmpeg պետք չէ։ YouTube-ի մեքենայական թարգմանված ուղիները բացառվում են։
- `app/translation.py` — պաշտոնական `google-genai` SDK, կառուցվածքային JSON, ID-ների կարգի և հայերեն տեքստի ստուգում։ 429/5xx սխալների համար առավելագույնը երեք փորձ՝ սահմանափակ սպասումով։
- `app/storage.py` — SQLite պատմություն և քեշ։ Քեշի բանալին ներառում է ամբողջ աղբյուրի հատվածը, հարակից համատեքստը, մոդելը և prompt-ի տարբերակը։
- `app/main.py` — FastAPI, վերբեռնում, վիճակի հարցումներ և յուրաքանչյուր դիտման ֆոնային հերթ։
- `static/` — առանց build համակարգի HTML/CSS/JavaScript, պաշտոնական YouTube IFrame API։ Տեքստը ցուցադրվում է `textContent`-ով։

Տվյալները տեղային `data/haysub.sqlite3` ֆայլում են։ Հավելվածը նախատեսված է մեկ օգտվողի տեղային աշխատանքի համար։ Օգտագործիր մեկ Uvicorn worker։ Մի հրապարակիր այն համացանցում առանց նույնականացման և ընդհանուր հարցումների/վերբեռնման սահմանափակումների։

## Ստուգումներ

```powershell
.\.venv\Scripts\python -m pytest -q
node tests/player.test.cjs
node tests/caption-ui.test.cjs
node tests/playback-ui.test.cjs
```

Python թեստերը ստուգում են URL-ները, SRT/VTT, սխալ մուտքերը, քեշի ինքնությունը, թարգմանության պատասխանի վավերացումը և API-ի վերբեռնման հոսքը։ Երկրորդ փուլի թեստերը նաև ստուգում են հեղինակի/ավտոմատ աղբյուրի ընտրությունը, rolling տեքստի մաքրումը, 429/մուտքի/կապի սխալները, ֆոնային առաջընթացը և կրկնափորձը, հին SQLite պատմության պահպանումը, ստացված ենթագրերի անցումը իրական թարգմանության քեշով՝ առանց Gemini հարցման։ Ցանցային ստացումը թեստերում փոխարինված է վերահսկվող պատասխաններով։ Node թեստերը ստուգում են ժամանակների սահմանները, շեղումը, seek-ը, ենթագրերի ստացման ժամանակ ավտոմեկնարկի սպասումը, transcript-ի թարմացումը և ֆայլի առաջարկը։ UI-ի թեստում օգտագործվում է DOM-ի փոքր փոխարինիչ, ոչ իրական բրաուզեր։

Առաջին փուլի սերվերը ստուգվել է Uvicorn-ի տեղային մեկնարկով և գլխավոր էջի HTTP 200 պատասխանով։ Օգտվողը ձեռքով հաստատել է առաջին փուլի YouTube նվագարկումն ու վերբեռնված ենթագրերի ցուցադրումը։ Երկրորդ փուլի համար անցել են 36 Python թեստերը, երկու Node ստուգումները, JavaScript syntax check-ը և `pip check`-ը։ Gemini API-ի իրական հարցում չի կատարվել այս աշխատանքի ընթացքում։ `tests/sample.srt`-ը միայն համաժամեցումը փորձարկելու նմուշ է, ոչ որևէ տեսանյութի իրական ենթագիր։

Ձեռքով ստուգիր՝ իրական տեսանյութ + համապատասխան ենթագրեր, play/pause, առաջ և հետ seek, երկու լեզվով ռեժիմ, շեղում, transcript-ի ժամանակներ։ Բանալիով ստուգիր առաջին հատվածի թարգմանությունը, հետագա առաջընթացը, սխալից հետո retry-ն և կրկնակի դիտման քեշը։ Startup-ի ֆիքսված ժամանակ չի խոստացվում։

## Հաջորդ փուլերը

Երկրորդ փուլն իրականացված է։ Ավտոմատ rolling ենթագրերի հարակից պատուհանների կրկնվող վերջնամասը/սկզբնամասը հեռացվում է, համընկնող ցուցադրման միջակայքները կրճատվում են։ Ժամանակային բացից հետո կրկնվող երկխոսությունը պահպանվում է։ Սա տեքստային հեուրիստիկա է. բառացի կրկնվող խոսքի և YouTube-ի անճշտությունների դեպքում պետք է ձեռքով ստուգել արդյունքը։ Հեղինակի ու վերբեռնված ենթագրերի տեքստն ու ժամանակները չեն նորմալացվում։

Ստացված աղբյուրը և ենթագրերը պահվում են SQLite պատմության մեջ։ Նույն թարգմանության քեշն է օգտագործվում՝ բովանդակություն, ժամանակներ, մոդել և prompt-ի տարբերակ։ Հին բազան թարմացվում է ավտոմատ՝ առանց պատմությունը ջնջելու։

Ստացման փուլը սահմանափակված է 90 վայրկյանով, ցանցային յուրաքանչյուր գործողությունն ունի 15 վայրկյան timeout և սահմանափակ yt-dlp կրկնափորձեր։ Ժամանակի սպառումը դադարեցնում է հերթի սպասումը. ընթացող ցանցային thread-ը կարող է ավարտվել ավելի ուշ, բայց չի փոխում աշխատանքային արդյունքը։ YouTube-ի սահմանափակումները չեն շրջանցվում։ Պաշտոնական YouTube captions API-ն չի օգտագործվում կամայական հանրային ենթագրեր ներբեռնելու համար։ YouTube-ի փոփոխությունների պատճառով երբեմն անհրաժեշտ է թարմացնել yt-dlp-ը՝

```powershell
.\.venv\Scripts\python -m pip install --upgrade yt-dlp
```

Միայն ենթագրերի իրական ստացումը ստուգելու համար (առանց Gemini հարցման)՝

```powershell
.\.venv\Scripts\python check_captions.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Երկրորդ փուլի ընթացքում այս հղումով իրական ստացումը հաջողվել է՝ `source=creator language=en cues=61`։ Իրական ավտոմատ աղբյուրով տեսանյութը, ամբողջական բրաուզերային հոսքը, Gemini-ի նոր հարցումն ու լսվող խոսքի հետ նորմալացված ենթագրերի համապատասխանությունը դեռ ձեռքով ստուգման կարիք ունեն։ Ստուգիր նաև՝ բացակայող ենթագրեր → ֆայլի վերբեռնում, կրկնափորձ, seek, և նույն տեսանյութի կրկնակի դիտումը քեշից։

Ավտոմատ ենթագրերի լրացուցիչ իրական ստուգումը՝ `lw2oyHjBmGM` տեսանյութով հաջողվել է՝ `source=automatic language=en cues=1942`։ Այդ ֆայլը պարունակում էր դատարկ պատուհանները մաքրող իրադարձություններ և դատարկ տողեր հենց ենթագրի տեքստի ներսում։ YouTube-ի ավտոմատ VTT-ի հատվածները այժմ առանձնացվում են ժամանակային տողերով, իսկ դատարկ իրադարձությունները բաց են թողնվում։ Վերբեռնված ֆայլերի խիստ վավերացումը պահպանված է։ Ստացումը փորձարկվել է առանց Gemini հարցման. բրաուզերում այս տեսանյութի թարգմանությունն ու համաժամեցումը դեռ պետք է ձեռքով ստուգել։

Caption coverage caveat for `lw2oyHjBmGM`: a fresh check of the original YouTube VTT confirms that early captions end in a `[music]` window lasting until 29:37.19; the next dialogue cue starts at 29:37.20. There are no caption starts between 2:00 and 3:00, for example. The transcript's jump from the normalized music cue at 1:21 to dialogue at 29:37 comes from the source captions, not missing Gemini translations. Translation cannot recover dialogue absent from that source. Use a complete uploaded subtitle file or a different video; speech recognition is still a later milestone.

Երրորդ փուլ՝ faster-whisper և ձայնի ֆոնային մշակում։ Այս փուլը դեռ իրականացված չէ։ Մուտքի սահմանափակումների կամ DRM-ի շրջանցում չի նախատեսվում։

## Պաշտոնական աղբյուրներ

Իրականացման ժամանակ ստուգվել են [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/), [structured output](https://ai.google.dev/gemini-api/docs/structured-output), [մոդելների կատալոգը](https://ai.google.dev/gemini-api/docs/models), [YouTube IFrame API](https://developers.google.com/youtube/iframe_api_reference), [yt-dlp Python ինտեգրումը](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp)։ Քո հաշվի մոդելների իրական հասանելիությունը ստուգվում է `list_models.py`-ով, ոչ թե ենթադրվում։
# Saved Armenian subtitle library

**Local video use:** double-click **Start HaySub.bat**. Put completed videos in
the project's **data/videos** folder. With the configured [local library layout](docs/LOCAL_LIBRARY.md),
files stay there and appear on the page automatically. **Scan video folder now** can
also register them. Attach Armenian subtitles before previewing/publishing. Only
supported H.264/AAC MP4 media is playable. See [local video instructions](docs/VIDEO_HOSTING.md#local-development-without-a-bucket).

**Owner-uploaded video viewing:** see [docs/VIDEO_HOSTING.md](docs/VIDEO_HOSTING.md).
The owner page now supports private S3 multipart uploads, prepared Armenian tracks,
private previews and unlisted `/watch/...` links. Viewers of these hosted videos
need no extension or installed app. Storage credentials and a separate media
inspection/cleanup worker are required; absent configuration is shown on the page.
No video is stored in Git, SQLite or the deployment package. No service purchase or
public deployment is performed by this feature.

**Public release setup:** see [docs/PUBLISHING.md](docs/PUBLISHING.md) for the
Windows hosting/store steps and [docs/FRIENDS.md](docs/FRIENDS.md) for what to send
viewers after publication. The extension now has a shared-library picker; public
builds use your HTTPS server and disable paid translation requests. Owner tools
are protected in `HAYSUB_PUBLIC=1` mode. Translations remain private until
**Publish for viewers** is selected. Local development behavior remains available.

The web page now keeps completed SRT/VTT file translations in **Your Armenian subtitle library**, below the file translator.

1. Start HaySub using the existing Windows startup instructions and open `http://127.0.0.1:8000/`.
2. Upload an English or Russian SRT/VTT in the file translator and start translation. Creating a new translation still requires the configured backend Gemini key.
3. When translation finishes, the Armenian SRT is saved automatically and appears in the library. Search by its title or original filename.
4. Click **Rename**, enter a title, and save. The title persists and determines the downloaded filename; subtitle text and timings stay unchanged.
5. Click the Armenian SRT download button whenever needed. Reading, renaming and downloading saved translations does not call Gemini or require an API key.

The library is stored in `data/haysub.sqlite3`, in the `subtitle_library` table, alongside the existing translation cache and resumable jobs. Keep this database when moving or backing up the project; clearing browser storage does not delete the library. Restarting the server preserves saved files. Existing completed file jobs are added automatically at startup when their source cues and valid complete translations are available. Partial or failed jobs remain resumable and do not appear as completed files. Older hash-only cache entries cannot reconstruct an entire source file.

Reuploading identical subtitles with the same model/prompt reuses their job and preserves a custom library title. Saved SRT snapshots remain downloadable even after the configured model changes. Renaming changes metadata, not filesystem paths. Click **Publish for viewers** to include a completed translation in the extension's shared catalog. To make that catalog available outside your computer, deploy the server and build the public extension following [docs/PUBLISHING.md](docs/PUBLISHING.md).

Verification for this change: 139 Python tests and 48 Node checks passed, including library persistence, startup recovery, partial-file exclusion, rename validation, safe filenames, search and error handling. Run them on Windows with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/*.test.cjs extension/tests/*.test.cjs
```

No live Chrome check or real Gemini request was performed for this change. Manually restart the backend, refresh the page, complete a small file translation, rename it, restart again and confirm its list entry and downloaded Armenian SRT remain correct. Check the new section on a narrow window as well.

# Automatic local subtitle files

With the [local library layout](docs/LOCAL_LIBRARY.md), completed SRT/VTT uploads
are saved in `data/subtitles/<title>/armenian.srt`, next to `original.srt` or
`original.vtt`. The legacy layout uses
`data/translated-subtitles/<title>_hy/<title>_hy.srt`. Duplicate titles include a translation ID in the folder name to avoid collisions.
These files are saved on the computer running the server; a hosted server saves
them on its own disk. The webpage's download button saves a copy to your browser's
download location.

