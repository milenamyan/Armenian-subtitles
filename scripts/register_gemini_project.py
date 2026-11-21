"""Register the active .env key's project without displaying or storing its secret."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', help='Google Cloud project ID shown beside this key in AI Studio')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    import os
    from app.rate_limits import register_project
    register_project(os.getenv('GEMINI_API_KEY', ''), args.project)
    print(f'Active key linked to project {args.project}. Restart HaySub to apply. No API call was made.')


if __name__ == '__main__':
    main()
