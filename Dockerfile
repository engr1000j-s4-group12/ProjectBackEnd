FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GUIDE_DB_PATH=/app/runtime/guide.sqlite3 \
    GUIDE_UPLOAD_DIR=/app/runtime/uploads

WORKDIR /app

COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

COPY . /app
RUN chmod +x /app/scripts/docker-entrypoint.sh \
    && useradd --create-home --uid 10001 guide \
    && mkdir -p /app/runtime \
    && chown -R guide:guide /app/runtime

USER guide
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
