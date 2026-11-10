FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HAYSUB_PUBLIC=1 HAYSUB_DB=/var/data/haysub.sqlite3
ENV HAYSUB_MEDIA_WORKER_ENABLED=1
WORKDIR /srv/haysub
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY app ./app
COPY static ./static
RUN useradd --uid 10001 --create-home haysub && mkdir -p /var/data && chown haysub:haysub /var/data
EXPOSE 8000
# One process: SQLite and in-process owner translation jobs must share state.
# The entry point initializes disk ownership, then drops to the haysub user
# before importing the web app or accepting any requests.
CMD ["python", "-m", "app.serve"]
