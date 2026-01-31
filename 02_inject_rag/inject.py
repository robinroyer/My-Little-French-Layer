import json
from pathlib import Path
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

def load_jsonl_files(input_folder):
    """Load all .jsonl files and convert them to Document objects."""
    input_path = Path(input_folder)
    jsonl_files = list(input_path.glob("*.jsonl"))

    if not jsonl_files:
        print(f"No JSONL files found in {input_folder}")
        return []

    all_documents = []
    for jsonl_file in jsonl_files:
        print(f"Loading: {jsonl_file.name}")
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                chunk_data = json.loads(line)
                doc = Document(
                    page_content=chunk_data["page_content"],
                    metadata=chunk_data["metadata"]
                )
                all_documents.append(doc)
        print(f"  Loaded {len(all_documents)} documents so far")

    return all_documents


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_folder = script_dir.parent / "01_extract_content" / "output"

    # Load all documents from JSONL files
    documents = load_jsonl_files(input_folder)

    if documents:
        # Inject into Qdrant
        inject_to_qdrant(documents)