FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    supervisor \
    postgresql-15 \
    postgresql-contrib-15 \
    postgresql-15-pgvector \
    python3.11 \
    python3.11-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set up Python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Install Meilisearch
ENV MEILI_VERSION=1.5.0
RUN wget -qO /usr/local/bin/meilisearch \
    https://github.com/meilisearch/meilisearch/releases/download/v${MEILI_VERSION}/meilisearch-linux-amd64 \
    && chmod +x /usr/local/bin/meilisearch

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

# Copy application files
COPY backend/ /app/backend/
COPY database/ /app/database/
COPY docker/supervisord.conf /etc/supervisord.conf
COPY docker/start.sh /app/start.sh

# Install Python packages
RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    && chmod +x /app/start.sh

# Create directories
RUN mkdir -p /var/lib/postgresql/data /var/lib/meilisearch /root/.ollama

# Environment variables
ENV POSTGRES_USER=ai_chatbot
ENV POSTGRES_PASSWORD=ai_chatbot123
ENV POSTGRES_DB=ai_chatbot_db
ENV MEILISEARCH_KEY=masterKey123
ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_NUM_GPU=1
ENV DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@localhost:5432/ai_chatbot_db
ENV MEILISEARCH_URL=http://localhost:7700
ENV OLLAMA_URL=http://localhost:11434
ENV LLM_MODEL=llama3.1:8b
ENV EMBEDDING_MODEL=llama3.1:8b
ENV PORT=5000

EXPOSE 5000 5432 7700 11434

CMD ["/app/start.sh"]


