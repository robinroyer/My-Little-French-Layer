import os
import json
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def process_legal_pdfs(file_path):
    # Load the PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    
    # Split text into manageable chunks
    # Laws need context, so we use a decent overlap
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )
    chunks = text_splitter.split_documents(docs)
    return chunks

def process_folder(input_folder, output_folder):
    """Process all PDF files in input_folder and save results to output_folder."""
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    # Create output folder if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Get all PDF files in input folder
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        return

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")

        # Process the PDF
        chunks = process_legal_pdfs(str(pdf_file))

        # Convert chunks to serializable format
        chunks_data = [
            {
                "page_content": chunk.page_content,
                "metadata": chunk.metadata
            }
            for chunk in chunks
        ]

        # Save to output folder with same name but .jsonl extension
        output_file = output_path / f"{pdf_file.stem}.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for chunk_data in chunks_data:
                f.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")

        print(f"  Saved {len(chunks)} chunks to {output_file.name}")

    print(f"\nProcessed {len(pdf_files)} files")


# Example usage
# chunks = process_legal_pdfs("penal_code.pdf")

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_folder = script_dir / "input"
    output_folder = script_dir / "output"
    process_folder(input_folder, output_folder)