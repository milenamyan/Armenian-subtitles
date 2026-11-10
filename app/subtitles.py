"""Small, strict SRT/WebVTT parser. Times are seconds; intervals are [start,end)."""
import html
import math
import re
from urllib.parse import urlsplit, parse_qs

# Exact annotation labels only; sentences and lyrics containing these words stay.
MUSIC_LABELS = {
    'music', 'background music', 'instrumental', 'instrumental music',
    'music playing', 'music continues', 'music fades', 'music swells',
    'soft music', 'gentle music', 'dramatic music', 'upbeat music', 'sad music',
    'tense music', 'ominous music', 'loud music', 'quiet music', 'classical music',
    'orchestral music', 'romantic music', 'suspenseful music', 'cheerful music',
    'музыка', 'звучит музыка', 'играет музыка', 'фоновая музыка', 'тихая музыка',
    'тревожная музыка', 'лирическая музыка', 'весёлая музыка', 'веселая музыка',
    'грустная музыка', 'музыка продолжается',
    'երաժշտություն', 'երաժշտութիւն', 'երաժշտությւոն', 'հնչում է երաժշտություն',
    'ֆոնային երաժշտություն', 'մեղմ երաժշտություն',
}


def is_music_line(text: str) -> bool:
    text = html.unescape(re.sub(r'<[^>]*>', '', text)).strip().lower()
    normalized = re.sub(r'[\[\](){}♪♫♬♩🎵🎶.։…!?:\s>«»\-—–]+', ' ', text).strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized in MUSIC_LABELS or (not normalized and bool(re.search(r'[♪♫♬♩🎵🎶]', text)))


def without_music_lines(text: str) -> str:
    return '\n'.join(line for line in text.splitlines() if not is_music_line(line)).strip()


def is_music_only(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    return bool(lines) and all(is_music_line(line) for line in lines)


def video_id(url: str) -> str:
    p = urlsplit(url.strip())
    if p.scheme not in ('https', 'http') or p.username or p.password or p.port:
        raise ValueError('Enter a valid YouTube URL.')
    host = (p.hostname or '').lower()
    parts = p.path.strip('/').split('/')
    value = ''
    if host == 'youtu.be' and len(parts) == 1:
        value = parts[0]
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        if p.path == '/watch':
            value = parse_qs(p.query).get('v', [''])[0]
        elif len(parts) == 2 and parts[0] in ('embed', 'shorts', 'live'):
            value = parts[1]
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', value):
        raise ValueError('Enter a valid YouTube video URL (watch, shorts or youtu.be).')
    return value


def seconds(value: str) -> float:
    if not re.fullmatch(r'(?:\d{2,}:)?\d{2}:\d{2}[.,]\d{3}', value):
        raise ValueError('Invalid subtitle timestamp.')
    parts = value.replace(',', '.').split(':')
    if float(parts[-1]) >= 60 or int(parts[-2]) >= 60:
        raise ValueError('Invalid timestamp range.')
    return sum(float(n) * 60 ** i for i, n in enumerate(reversed(parts)))


def parse_subtitles(raw: bytes, *, allow_empty_cues: bool = False, preserve_text: bool = False) -> list[dict]:
    if not raw or len(raw) > 2 * 1024 * 1024:
        raise ValueError('Upload a nonempty subtitle file smaller than 2 MB.')
    try:
        text = raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    except UnicodeDecodeError:
        raise ValueError('Save subtitles as UTF-8.')
    cues = []
    for block_number, block in enumerate(re.split(r'\n\s*\n', text.strip()), 1):
        lines = block.strip().splitlines()
        if not lines or lines[0].startswith(('WEBVTT', 'NOTE', 'STYLE', 'REGION')):
            continue
        index = next((i for i, line in enumerate(lines[:2]) if '-->' in line), None)
        if index is None:
            raise ValueError('Invalid subtitle block: missing timestamps.')
        times = lines[index].split('-->')
        start, end = seconds(times[0].strip()), seconds(times[1].strip().split()[0])
        content = '\n'.join(lines[index + 1:]).strip()
        if not preserve_text:
            content = html.unescape(re.sub(r'<[^>]*>', '', content)).strip()
        cue_label = lines[0] if index == 1 else str(block_number)
        # Empty placeholders have nothing to display; malformed dialogue is an error.
        # Keep all valid dialogue at its original timestamp; never invent a duration.
        if allow_empty_cues and end >= start and not content:
            continue
        if end <= start or not content or len(content) > 5000:
            if end <= start:
                reason = 'end time must be later than start time'
            elif not content:
                reason = 'text is empty'
            else:
                reason = 'text exceeds 5,000 characters'
            raise ValueError(f'Subtitle cue {cue_label} ({times[0].strip()} --> {times[1].strip()}): {reason}.')
        if cues and start < cues[-1]['start']:
            raise ValueError('Subtitle timestamps must be in order.')
        cues.append(dict(id=len(cues) + 1, start=start, end=end, source=content))
        if len(cues) > 10000:
            raise ValueError('Maximum 10,000 subtitle cues.')
    if not cues:
        raise ValueError('No subtitle cues found.')
    return cues


def format_srt_time(seconds: float) -> str:
    """Round once to milliseconds so carry boundaries produce valid SRT times."""
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f'{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}'


def translated_srt(cues: list[dict], translated: dict) -> str:
    """Export only a complete translation, never fill missing lines with source text."""
    output = []
    # Validate all source timings, including cues omitted by music filtering.
    normalize_timings(cues)
    for i, cue in enumerate(cues, 1):
        if is_music_only(cue['source']):
            continue
        text = translated.get(str(cue['id']), '')
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Translation is not complete yet.')
        text = re.sub(r'\n\s*\n', '\n', text.replace('\r\n', '\n').replace('\r', '\n')).strip()
        text = without_music_lines(text)
        if not text:
            continue
        output.append(dict(cue, source=text))
    if not cues:
        raise ValueError('No subtitle cues found.')
    return render_srt(normalize_timings(output))


def normalize_timings(cues: list[dict]) -> list[dict]:
    """Merge equal starts and trim overlaps without changing input or losing text."""
    merged = []
    for index, cue in enumerate(cues, 1):
        start, end = cue['start'], cue['end']
        label = cue.get('id', index)
        if not all(math.isfinite(value) for value in (start, end)) or start < 0 or end <= start:
            raise ValueError(f'Subtitle cue {label}: invalid timing ({start} --> {end}); start must be nonnegative and end later than start.')
        if merged and start < merged[-1]['start']:
            raise ValueError(f'Subtitle cue {label}: start time is earlier than the preceding cue.')
        if merged and start == merged[-1]['start']:
            merged[-1]['source'] += '\n' + cue['source']
            merged[-1]['end'] = max(merged[-1]['end'], end)
        else:
            merged.append(dict(cue))
    for index, cue in enumerate(merged):
        if index + 1 < len(merged):
            cue['end'] = min(cue['end'], merged[index + 1]['start'])
        if round(cue['start'] * 1000) >= round(cue['end'] * 1000):
            raise ValueError(f"Subtitle cue {cue.get('id', index + 1)}: duration is nonpositive at SRT millisecond precision.")
    return merged


def render_srt(cues: list[dict]) -> str:
    blocks = [f"{i}\n{format_srt_time(cue['start'])} --> {format_srt_time(cue['end'])}\n{cue['source']}"
              for i, cue in enumerate(cues, 1)]
    return '\n\n'.join(blocks) + ('\n' if blocks else '')
