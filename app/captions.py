"""Retrieve only English caption text with yt-dlp; never download media."""
import re
from urllib.parse import parse_qs, urlsplit
from yt_dlp import YoutubeDL
from app.subtitles import parse_subtitles, video_id

MAX_CAPTION_BYTES = 2 * 1024 * 1024


class CaptionError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message + ' Կարող ես վերբեռնել .srt կամ .vtt ենթագրերի ֆայլ և կրկին սեղմել դիտման կոճակը։')


class QuietLogger:
    # yt-dlp errors can contain signed caption URLs; never send these to the UI.
    def __init__(self):
        self.failure = None

    def debug(self, message):
        pass

    def warning(self, message):
        lower = message.lower()
        if '429' in lower or 'rate limit' in lower:
            self.failure = retrieval_error(message)
        elif ('subtitles' in lower and ('po token' in lower or 'skipped' in lower)) and self.failure is None:
            self.failure = CaptionError('access_denied', 'YouTube-ը սահմանափակել է ենթագրերի հասանելիությունը։')

    def error(self, message):
        pass


def english_tracks(info, allow_any_language=False):
    """Creator English first, then native English auto-captions, never translations."""
    for field, source in (('subtitles', 'creator'), ('automatic_captions', 'automatic')):
        tracks = info.get(field) or {}
        for language in sorted(tracks, key=lambda lang: (not lang.startswith('en'), lang != 'en', lang)):
            if not re.fullmatch(r'en(?:[-_][A-Za-z0-9]+)*', language) and not (allow_any_language and re.fullmatch(r'[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)*', language)):
                continue
            for track in tracks[language]:
                query = parse_qs(urlsplit(track.get('url', '')).query)
                if track.get('ext') == 'vtt' and track.get('url') and 'tlang' not in query:
                    yield source, language, track


def normalize_rolling(cues):
    """Trim adjacent suffix/prefix repeats; preserve repeated dialogue after a gap.

    Compare full raw windows, even when their displayed prefix was removed.
    Only automatic captions pass through this function.
    """
    result, previous_words, previous_end = [], [], -1
    for cue in cues:
        words = cue['source'].split()
        overlap = 0
        if cue['start'] <= previous_end + 0.15:
            left, right = [w.casefold() for w in previous_words], [w.casefold() for w in words]
            for size in range(min(len(left), len(right)), 0, -1):
                if left[-size:] == right[:size]:
                    overlap = size
                    break
        previous_words, previous_end = words, cue['end']
        if overlap == len(words):
            if result:
                result[-1]['end'] = max(result[-1]['end'], cue['end'])
            continue
        if result and result[-1]['end'] > cue['start']:
            result[-1]['end'] = cue['start']
            if result[-1]['end'] <= result[-1]['start']:
                old = result.pop()
                words = old['source'].split() + words[overlap:]
                overlap = 0
        result.append(dict(cue, source=' '.join(words[overlap:])))
    return [dict(cue, id=i + 1) for i, cue in enumerate(result)]


def parse_automatic_vtt(raw):
    """YouTube ASR sometimes inserts blank lines *inside* a timed cue.

    Rebuild blocks from timestamp lines instead of treating every blank line as
    a cue boundary. This repair is exclusive to YouTube automatic captions.
    """
    if not raw or len(raw) > MAX_CAPTION_BYTES:
        raise ValueError('Invalid caption size')
    text = raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    timestamp = r'(?:\d{2,}:)?\d{2}:\d{2}[.,]\d{3}'
    matches = list(re.finditer(rf'(?m)^{timestamp}[^\S\n]+-->[^\S\n]+{timestamp}[^\n]*', text))
    blocks = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        lines = [line.strip() for line in text[match.start():end].splitlines() if line.strip()]
        blocks.append('\n'.join(lines))
    return parse_subtitles(('\n\n'.join(blocks)).encode('utf-8'), allow_empty_cues=True)


def retrieval_error(exc):
    message = str(exc).lower()
    if '429' in message or 'too many requests' in message or 'rate limit' in message:
        return CaptionError('rate_limited', 'YouTube-ը ժամանակավորապես սահմանափակել է հարցումները։ Սպասիր և փորձիր կրկին։')
    if any(word in message for word in ('403', '401', 'sign in', 'private', 'members-only', 'age-restricted', 'not available', 'unavailable', 'blocked', 'bot')):
        return CaptionError('access_denied', 'YouTube-ը չի թույլատրել ենթագրերի ստացումը․ տեսանյութը կարող է լինել փակ կամ սահմանափակված։')
    return CaptionError('retrieval_failed', 'Չհաջողվեց ստանալ YouTube-ի ենթագրերը։ Ստուգիր կապը և փորձիր կրկին։')


def retrieve_captions(video, allow_any_language=False):
    video = video_id('https://www.youtube.com/watch?v=' + video)
    logger = QuietLogger()
    options = dict(skip_download=True, noplaylist=True, quiet=True, no_warnings=True,
                   logger=logger, socket_timeout=15, retries=1, extractor_retries=1,
                   ignore_no_formats_error=True,
                   writesubtitles=False, writeautomaticsub=False,
                   extractor_args={'youtube': {'skip': ['translated_subs', 'hls', 'dash']}})
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info('https://www.youtube.com/watch?v=' + video, download=False)
            if not info:
                raise logger.failure or CaptionError('retrieval_failed', 'YouTube-ը չի վերադարձրել տեսանյութի տվյալները։')
            last_error = None
            for source, language, track in english_tracks(info, allow_any_language):
                try:
                    url = urlsplit(track['url'])
                    host = url.hostname or ''
                    if url.scheme != 'https' or not (host == 'youtube.com' or host.endswith('.youtube.com')):
                        raise ValueError('Unexpected caption host')
                    with ydl.urlopen(track['url']) as response:
                        raw = response.read(MAX_CAPTION_BYTES + 1)
                    cues = parse_automatic_vtt(raw) if source == 'automatic' else parse_subtitles(raw, allow_empty_cues=True)
                    if source == 'automatic':
                        cues = normalize_rolling(cues)
                    if not cues:
                        raise ValueError('Empty captions')
                    return dict(cues=cues, source=source, language=language)
                except Exception as exc:
                    last_error = retrieval_error(exc)
                    if last_error.code == 'rate_limited':
                        raise last_error
            if last_error:
                raise last_error
            if logger.failure:
                raise logger.failure
            raise CaptionError('missing_captions', 'Այս տեսանյութի համար հասանելի ենթագրեր չեն գտնվել։' if allow_any_language else 'Այս տեսանյութի համար հասանելի անգլերեն ենթագրեր չեն գտնվել։')
    except CaptionError:
        raise
    except Exception as exc:
        raise retrieval_error(exc) from None
