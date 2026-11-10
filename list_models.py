"""List models actually accessible to your key, without a generation request."""
import os
from dotenv import load_dotenv
from google import genai
load_dotenv()
if not os.getenv('GEMINI_API_KEY'):
    raise SystemExit('Set GEMINI_API_KEY in .env first.')
with genai.Client(api_key=os.environ['GEMINI_API_KEY']) as client:
    for model in client.models.list():
        if 'generateContent' in (model.supported_actions or []):
            print(model.name)
