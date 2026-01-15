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
    postgresql-server-dev-all \
    git \
    build-essential \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Find and set PostgreSQL version for easier access
RUN PG_VERSION=$(ls -1 /usr/lib/postgresql/ | head -1) && \
    echo "export PG_VERSION=${PG_VERSION}" >> /etc/profile && \
    echo "export PATH=/usr/lib/postgresql/${PG_VERSION}/bin:\$PATH" >> /etc/profile && \
    ln -sf /usr/lib/postgresql/${PG_VERSION}/bin/* /usr/local/bin/ 2>/dev/null || true

# Install pgvector extension
RUN PG_VERSION=$(ls -1 /usr/lib/postgresql/ | head -1) && \
    PG_CONFIG=/usr/lib/postgresql/${PG_VERSION}/bin/pg_config && \
    echo "Installing pgvector for PostgreSQL ${PG_VERSION}" && \
    echo "PostgreSQL sharedir: $(${PG_CONFIG} --sharedir)" && \
    echo "PostgreSQL pkglibdir: $(${PG_CONFIG} --pkglibdir)" && \
    cd /tmp && \
    git clone --depth 1 --branch v0.7.2 https://github.com/pgvector/pgvector.git && \
    cd pgvector && \
    export PG_CONFIG=${PG_CONFIG} && \
    make && \
    make install && \
    # Verify installation (make install should have installed everything)
    SHAREDIR=$(${PG_CONFIG} --sharedir) && \
    PKGLIBDIR=$(${PG_CONFIG} --pkglibdir) && \
    echo "Verifying pgvector installation..." && \
    if [ -f ${SHAREDIR}/extension/vector.control ] && [ -f ${PKGLIBDIR}/vector.so ]; then \
        echo "✓ pgvector installed successfully"; \
        echo "  - Extension: ${SHAREDIR}/extension/vector.control"; \
        echo "  - Library: ${PKGLIBDIR}/vector.so"; \
    else \
        echo "✗ Installation verification failed"; \
        echo "Checking for files..." && \
        ls -la ${SHAREDIR}/extension/vector* 2>/dev/null || echo "Extension files not found"; \
        ls -la ${PKGLIBDIR}/vector* 2>/dev/null || echo "Library not found"; \
        find /usr -name "vector.control" 2>/dev/null | head -5 || true; \
        find /usr -name "vector.so" 2>/dev/null | head -5 || true; \
        exit 1; \
    fi && \
    cd / && \
    rm -rf /tmp/pgvector

# Install Ollama (latest version) with GPU support
# Note: For GPU support, NVIDIA Container Toolkit must be installed on the host
RUN curl -fsSL https://ollama.com/install.sh | sh || \
    (echo "Ollama install script failed, trying manual install..." && \
     OLLAMA_VERSION=$(curl -s https://api.github.com/repos/ollama/ollama/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/') && \
     echo "Installing Ollama version ${OLLAMA_VERSION:-latest}" && \
     curl -L https://github.com/ollama/ollama/releases/download/${OLLAMA_VERSION:-v0.1.32}/ollama-linux-amd64 -o /usr/local/bin/ollama && \
     chmod +x /usr/local/bin/ollama) && \
    # Install timeout command if not available
    (command -v timeout || apt-get update && apt-get install -y --no-install-recommends coreutils && rm -rf /var/lib/apt/lists/*)

ENV MEILI_VERSION=1.5.0
RUN wget -qO /usr/local/bin/meilisearch \
    https://github.com/meilisearch/meilisearch/releases/download/v${MEILI_VERSION}/meilisearch-linux-amd64 \
    && chmod +x /usr/local/bin/meilisearch

WORKDIR /app

COPY backend/ /app/backend/
COPY database/ /app/database/
COPY docker/supervisord.conf /etc/supervisord.conf
COPY docker/start.sh /app/start.sh

# Create PostgreSQL wrapper script
RUN PG_VERSION=$(ls -1 /usr/lib/postgresql/ | head -1) && \
    echo "#!/bin/bash" > /usr/local/bin/start-postgres.sh && \
    echo "exec /usr/lib/postgresql/${PG_VERSION}/bin/postgres -D /var/lib/postgresql/data -c listen_addresses='*'" >> /usr/local/bin/start-postgres.sh && \
    chmod +x /usr/local/bin/start-postgres.sh

RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    && chmod +x /app/start.sh

EXPOSE 5000 5432 7700 11434

CMD ["/app/start.sh"]
