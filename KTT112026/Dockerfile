FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md VERSION.txt ./
COPY src ./src

ENV PYTHONPATH=/app/src
ENV KTT_DATABASE_PATH=/data/ktt112026.db

# Ensure data dir exists; sects.json optional (loader has embedded NPC fallback)
RUN mkdir -p /data \
    && python -c "from pathlib import Path; p=Path('/app/src/ktt112026/game/content/data'); \
print('data files:', sorted(x.name for x in p.glob('*.json'))); \
assert (p/'vukhi.json').is_file(), 'missing vukhi.json'; \
sects=p/'sects.json'; \
print('sects.json', 'OK' if sects.is_file() else 'MISSING (using embedded fallback)')"

CMD ["python", "-m", "ktt112026"]
