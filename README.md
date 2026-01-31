# My Little French Layer (MLFL)

A RAG (Retrieval Augmented Generation) pipeline for querying French legal documents.

![Pipeline](pipeline.png)

## Pipeline Steps

### 1. Download Legal PDFs

Download law codes from Legifrance:
- https://www.legifrance.gouv.fr/liste/code?etatTexte=VIGUEUR&etatTexte=VIGUEUR_DIFF

Place PDF files in `01_extract_content/input/`.

### 2. Extract & Chunk

Extract text from PDFs and split into chunks for indexing.

```bash
python 01_extract_content/extract.py
```

### 3. Inject into Vector Database

Load chunks and inject into Qdrant using [BGE embeddings](https://huggingface.co/BAAI/bge-small-en-v1.5).


```bash
python 02_inject_rag/inject.py
```

### 4. Query

Query the legal assistant with optional RAG support.

```bash
# Interactive chat with RAG
python 03_query/query.py --chat

# Interactive chat without RAG (vanilla mode)
python 03_query/query.py --chat --vanilla

# Single query
python 03_query/query.py "What is the penalty for theft?"

# Pipe input/output
echo "What is article 311-1?" | python 03_query/query.py

# Use Claude instead of Ollama
python 03_query/query.py --provider claude --chat

# Custom Ollama server
python 03_query/query.py --model llama3 --url http://localhost:11434
```

**Options:**

| Flag | Description |
|------|-------------|
| `-c, --chat` | Interactive chat mode |
| `-v, --vanilla` | Disable RAG (no vector store context) |
| `-p, --provider` | LLM provider: `ollama` (default) or `claude` |
| `-m, --model` | Model name override |
| `-u, --url` | Ollama server URL |
| `--qdrant-url` | Qdrant server URL |
| `--collection` | Qdrant collection name |

## Requirements

- Qdrant running on `localhost:6333`
```
docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
    qdrant/qdrant

```

- Ollama with a model installed (e.g., `smollm2:1.7b`)
