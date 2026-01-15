FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    supervisor \
    postgresql \
    postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*

ENV MEILI_VERSION=1.5.0
RUN wget -qO /usr/local/bin/meilisearch \
    https://github.com/meilisearch/meilisearch/releases/download/v${MEILI_VERSION}/meilisearch-linux-amd64 \
    && chmod +x /usr/local/bin/meilisearch

WORKDIR /app

COPY backend/ /app/backend/
COPY database/ /app/database/
COPY docker/supervisord.conf /etc/supervisord.conf
COPY docker/start.sh /app/start.sh

RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    && chmod +x /app/start.sh

EXPOSE 5000 5432 7700

CMD ["/app/start.sh"]
