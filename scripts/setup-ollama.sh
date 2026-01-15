#!/bin/bash
# Quick setup script for Ollama and Llama models

set -e

echo "🚀 Setting up Ollama for AI Chatbot"
echo ""

# Check if running in Docker
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    echo "📦 Running in Docker container"
    OLLAMA_CMD="docker exec -it ai-chatbot-ollama ollama"
else
    echo "💻 Running locally"
    OLLAMA_CMD="ollama"
    
    # Check if Ollama is installed
    if ! command -v ollama &> /dev/null; then
        echo "❌ Ollama is not installed!"
        echo "   Install from: https://ollama.com/download"
        exit 1
    fi
    
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "⚠️  Ollama is not running. Starting Ollama..."
        ollama serve &
        sleep 5
    fi
fi

echo ""
echo "📥 Available models:"
echo "  1. llama3.1:8b (Recommended, ~4.7GB)"
echo "  2. llama3.1:8b-instruct-q4_0 (Faster, quantized, ~4.6GB)"
echo "  3. llama3.2:3b (Smaller, faster, ~2GB)"
echo "  4. nomic-embed-text (For embeddings only, ~274MB)"
echo ""

read -p "Select model (1-4) or 'all' for all: " choice

case $choice in
    1)
        echo "📥 Pulling llama3.1:8b..."
        $OLLAMA_CMD pull llama3.1:8b
        MODEL="llama3.1:8b"
        ;;
    2)
        echo "📥 Pulling llama3.1:8b-instruct-q4_0..."
        $OLLAMA_CMD pull llama3.1:8b-instruct-q4_0
        MODEL="llama3.1:8b-instruct-q4_0"
        ;;
    3)
        echo "📥 Pulling llama3.2:3b..."
        $OLLAMA_CMD pull llama3.2:3b
        MODEL="llama3.2:3b"
        ;;
    4)
        echo "📥 Pulling nomic-embed-text..."
        $OLLAMA_CMD pull nomic-embed-text
        MODEL="nomic-embed-text"
        ;;
    all)
        echo "📥 Pulling all models..."
        $OLLAMA_CMD pull llama3.1:8b
        $OLLAMA_CMD pull llama3.1:8b-instruct-q4_0
        $OLLAMA_CMD pull llama3.2:3b
        $OLLAMA_CMD pull nomic-embed-text
        MODEL="llama3.1:8b"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Update your .env file with:"
echo "   LLM_MODEL=$MODEL"
if [ "$choice" != "4" ]; then
    echo "   EMBEDDING_MODEL=$MODEL"
else
    echo "   EMBEDDING_MODEL=nomic-embed-text"
fi
echo ""
echo "🧪 Test the setup:"
echo "   curl http://localhost:11434/api/tags"


