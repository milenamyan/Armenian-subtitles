"""Optional live caption check; downloads no media and makes no Gemini calls."""
import argparse
from app.captions import CaptionError, retrieve_captions
from app.subtitles import video_id

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('url', help='YouTube video URL')
args = parser.parse_args()
try:
    result = retrieve_captions(video_id(args.url))
except (CaptionError, ValueError) as exc:
    print(getattr(exc, 'code', 'invalid_url') + ': ' + str(exc))
    raise SystemExit(1)
print(f"source={result['source']} language={result['language']} cues={len(result['cues'])}")
