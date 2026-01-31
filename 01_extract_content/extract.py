import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import fitz  # PyMuPDF - much faster than pypdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_text_fast(file_path):
    """Extract text from PDF using PyMuPDF (fast)."""
    docs = []
    pdf = fitz.open(file_path)
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        text = page.get_text("text")
        if text.strip():  # Skip empty pages
            docs.append(Document(
                page_content=text,
                metadata={"source": str(file_path), "page": page_num}
            ))
    pdf.close()
    return docs


def process_legal_pdfs(file_path):
    """Load PDF and split into chunks."""
    docs = extract_text_fast(file_path)

    # Split text into manageable chunks
    # Laws need context, so we use a decent overlap
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=1000,
        chunk_overlap=150
    )
    chunks = text_splitter.split_documents(docs)
    return chunks

def process_single_pdf(pdf_file, output_path):
    """Process a single PDF file and save results to output_path."""
    output_file = output_path / f"{pdf_file.stem}.jsonl"
    chunk_count = 0

    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in process_legal_pdfs(str(pdf_file)):
            chunk_data = {
                "page_content": chunk.page_content,
                "metadata": chunk.metadata
            }
            f.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")
            chunk_count += 1

    return pdf_file.name, output_file.name, chunk_count


def process_folder(input_folder, output_folder, max_workers=14):
    """Process all PDF files in input_folder and save results to output_folder.

    Args:
        input_folder: Path to folder containing PDF files
        output_folder: Path to folder where results will be saved
        max_workers: Maximum number of threads for parallel processing
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    # Create output folder if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Get all PDF files in input folder
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        return

    print(f"Processing {len(pdf_files)} PDF files with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_pdf, pdf_file, output_path): pdf_file
            for pdf_file in pdf_files
        }

        for future in as_completed(futures):
            pdf_file = futures[future]
            try:
                pdf_name, output_name, chunk_count = future.result()
                print(f"  {pdf_name} -> {output_name} ({chunk_count} chunks)")
            except Exception as e:
                print(f"  Error processing {pdf_file.name}: {e}")

    print(f"\nProcessed {len(pdf_files)} files")


# Example usage
# chunks = process_legal_pdfs("penal_code.pdf")

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_folder = script_dir / "input"
    output_folder = script_dir / "output"
    process_folder(input_folder, output_folder)