FROM python:3.11-slim-bookworm
ARG APP_UID=10001
ARG APP_GID=10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 DATABASE_URL=sqlite:////data/caltopo-history.db TZ=Europe/Berlin
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates gosu tini && rm -rf /var/lib/apt/lists/* && groupadd --gid "${APP_GID}" caltopo && useradd --uid "${APP_UID}" --gid "${APP_GID}" --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin caltopo && mkdir -p /data && chown caltopo:caltopo /data
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app /app/app
COPY support/ui-assets-v0.8.tar.gz /tmp/ui-assets-v0.8.tar.gz
RUN tar -xzf /tmp/ui-assets-v0.8.tar.gz -C /app && rm -f /tmp/ui-assets-v0.8.tar.gz
COPY docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh && chown -R caltopo:caltopo /app
VOLUME ["/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=3)); raise SystemExit(0 if d.get('ok') else 1)"
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
