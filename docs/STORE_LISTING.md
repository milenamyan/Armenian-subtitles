# Chrome Web Store listing draft

Name: **HaySub — Armenian subtitles**

Short description:

> Choose prepared Armenian subtitles and display them over supported video players. Local subtitle files are also supported.

Full description:

> Watch supported web videos with Armenian subtitles from the HaySub library.
> Open a film, click HaySub, search by film or episode name and choose the matching
> translation. You can also upload your own UTF-8 SRT or VTT file for local display.
>
> Subtitles follow the video's playback clock, including pauses, seeks and speed
> changes. Adjust font size, text color, background opacity, vertical position and
> timing offset. Settings and selected files are saved locally in your browser.
>
> Embedded video players may require permission for their specific host. HaySub
> does not download video, collect cookies or bypass protected playback. Some
> nonstandard players, native-video fullscreen and picture-in-picture are unsupported.
> Choose subtitles for the exact film release or episode; HaySub does not identify
> films automatically and does not translate arbitrary videos in the public release.
>
> No Python installation, Gemini key or viewer account is required. An internet
> connection is needed to search/download from the library. Previously saved
> subtitles can display offline. Available translations are managed by the publisher.

Single purpose: display user-selected subtitle text over supported video players.

Permission explanations:

- **storage**: keep settings, timing offsets and selected subtitle files locally.
- **activeTab**: activate HaySub only on a page the user chooses by clicking it.
- **scripting**: add the subtitle overlay and read the selected video's clock.
- **YouTube content script matches**: attach the overlay to YouTube's player and
  clean up when YouTube changes videos without a full page reload.
- **Exact HaySub server host permission**: download published subtitle metadata
  and SRT text. No viewer key or paid-translation access is included.
- **Optional webNavigation**: enumerate frames of the active tab to locate an
  embedded video when the user asks.
- **Optional HTTP/HTTPS host permissions**: request only the specific embedded
  player origin the user selects; no request to grant all sites is made.

Remote code: none. Library subtitle text is parsed and rendered as text, not HTML
or executable code. The extension has no advertising or analytics trackers.

Privacy/data disclosures must match the actual host configuration and current
store questions. Search phrases and requested translation IDs go to the HaySub
server. The hosting provider receives ordinary request/IP information. The public
extension keeps local files, settings and video associations on the device and
does not send current page URLs, playback positions or local subtitle uploads.

Before submission: fill the real support email, homepage and privacy URLs; test
the public ZIP; capture genuine screenshots. Do not claim every website/video is
supported, automatic film matching, or store approval before it happens.
