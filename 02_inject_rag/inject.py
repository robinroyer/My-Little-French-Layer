import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http import models

def inject_to_qdrant(chunks, collection_name="law_library"):
    # Using a standard open-source embedding model
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    
    url = "http://localhost:6333"
    
    # Initialize Vector Store and upload
    vector_store = QdrantVectorStore.from_documents(
        chunks,
        embeddings,
        url=url,
        collection_name=collection_name,
    )
    print(f"Successfully injected {len(chunks)} chunks into Qdrant.")

def load_single_jsonl(jsonl_file):
    """Load a single JSONL file and return Document objects."""
    documents = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            chunk_data = json.loads(line)
            doc = Document(
                page_content=chunk_data["page_content"],
                metadata=chunk_data["metadata"]
            )
            documents.append(doc)
    return jsonl_file.name, documents


def load_jsonl_files(input_folder, max_workers=4):
    """Load all .jsonl files and convert them to Document objects.

    Args:
        input_folder: Path to folder containing JSONL files
        max_workers: Maximum number of threads for parallel loading
    """
    input_path = Path(input_folder)
    jsonl_files = list(input_path.glob("*.jsonl"))

    if not jsonl_files:
        print(f"No JSONL files found in {input_folder}")
        return []

    print(f"Loading {len(jsonl_files)} JSONL files with {max_workers} workers...")

    all_documents = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(load_single_jsonl, jsonl_file): jsonl_file
            for jsonl_file in jsonl_files
        }

        for future in as_completed(futures):
            jsonl_file = futures[future]
            try:
                file_name, documents = future.result()
                all_documents.extend(documents)
                print(f"  {file_name}: {len(documents)} documents")
            except Exception as e:
                print(f"  Error loading {jsonl_file.name}: {e}")

    print(f"Total: {len(all_documents)} documents loaded")
    return all_documents


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_folder = script_dir.parent / "01_extract_content" / "output"

    # Load all documents from JSONL files
    documents = load_jsonl_files(input_folder)

    if documents:
        # Inject into Qdrant
        inject_to_qdrant(documents)