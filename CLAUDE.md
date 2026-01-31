# CLAUDE.md

## Project Overview

**My Little French Layer (MLFL)** - A RAG pipeline for querying French legal documents from Legifrance.

## Architecture

```
PDF files → Extract & Chunk → JSONL → Inject → Qdrant → Query with LLM
```

### Directory Structure

- `01_extract_content/` - PDF extraction and chunking
  - `input/` - Source PDF files
  - `output/` - Generated JSONL chunks
- `02_inject_rag/` - Vector database injection
- `03_query/` - Query interface with RAG support

## Key Commands

```bash
# Setup
pip install -r requirements.txt

# Start Qdrant (required for RAG)
docker run -p 6333:6333 -p 6334:6334 -v "$(pwd)/qdrant_storage:/qdrant/storage:z" qdrant/qdrant

# Pipeline steps
python 01_extract_content/extract.py      # Extract PDFs to JSONL
python 02_inject_rag/inject.py            # Inject into Qdrant
python 03_query/query.py --chat           # Interactive query
```

## Query Script Usage

The unified `03_query/query.py` supports multiple modes:

| Mode | Command |
|------|---------|
| Chat with RAG | `python 03_query/query.py --chat` |
| Chat vanilla | `python 03_query/query.py --chat --vanilla` |
| Single query | `python 03_query/query.py "question"` |
| Pipe | `echo "question" \| python 03_query/query.py` |
| Claude provider | `python 03_query/query.py --provider claude` |

## Tech Stack

- **Embeddings**: `BAAI/bge-small-en-v1.5` (HuggingFace)
- **Vector DB**: Qdrant (localhost:6333)
- **LLM**: Ollama (default) or Claude via `--provider claude`
- **Framework**: LangChain ecosystem

## Code Patterns

- All scripts use `ThreadPoolExecutor` for parallel processing
- Default workers: 14 for extraction, 4 for injection
- Chunks: 1000 chars with 150 overlap
- JSONL format for intermediate storage (one JSON object per line)

## Environment

- Python virtual environment in `./venv`
- Ollama server at `http://192.168.1.58:8889/` (configurable via `--url`)
- Qdrant at `http://localhost:6333` (configurable via `--qdrant-url`)

## Important Notes

- PDF files should be placed in `01_extract_content/input/`
- The `--vanilla` flag skips RAG context (useful for comparison)
- Claude provider requires `ANTHROPIC_API_KEY` environment variable
