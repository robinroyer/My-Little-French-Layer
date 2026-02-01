"""
PDF Cleaning and Enrichment Pipeline for French Legal Documents.

Extracts PDFs from Legifrance and enriches them with metadata for better RAG results.
Outputs:
  - 01_output/: Markdown files (human-readable)
  - 02_structured/: JSONL files with full metadata for RAG injection
"""
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Article patterns for French legal codes
ARTICLE_PATTERNS = [
    r"Article\s+(L\.?\s*\d+[-–]\d+[-–]?\d*)",      # Article L.311-1, Article L311-1
    r"Article\s+(R\.?\s*\d+[-–]\d+[-–]?\d*)",      # Article R.311-1
    r"Article\s+(D\.?\s*\d+[-–]\d+[-–]?\d*)",      # Article D.311-1
    r"Article\s+(A\.?\s*\d+[-–]\d+[-–]?\d*)",      # Article A.311-1
    r"Article\s+(\d+[-–]\d+[-–]?\d*)",              # Article 311-1
    r"Art\.\s*(\d+[-–]\d+)",                        # Art. 311-1
]

# Hierarchy patterns (order matters - from highest to lowest level)
HIERARCHY_PATTERNS = [
    (r"PARTIE\s+(LÉGISLATIVE|RÉGLEMENTAIRE|PRELIMINAIRE)", "partie"),
    (r"LIVRE\s+([IVX]+|PRÉLIMINAIRE|\d+)", "livre"),
    (r"TITRE\s+([IVX]+|PRÉLIMINAIRE|\d+)", "titre"),
    (r"CHAPITRE\s+([IVX]+|PRÉLIMINAIRE|\d+)", "chapitre"),
    (r"SECTION\s+(\d+|[IVX]+)", "section"),
    (r"SOUS-SECTION\s+(\d+|[IVX]+)", "sous_section"),
]


@dataclass
class HierarchyTracker:
    """Tracks the current position in the legal document hierarchy."""
    partie: Optional[str] = None
    livre: Optional[str] = None
    titre: Optional[str] = None
    chapitre: Optional[str] = None
    section: Optional[str] = None
    sous_section: Optional[str] = None

    # Store titles associated with each level
    titles: dict = field(default_factory=dict)

    LEVELS = ["partie", "livre", "titre", "chapitre", "section", "sous_section"]

    def update(self, level: str, value: str, title: Optional[str] = None):
        """Update a hierarchy level and reset all lower levels."""
        if level not in self.LEVELS:
            return

        setattr(self, level, value)
        if title:
            self.titles[level] = title

        # Reset lower levels
        idx = self.LEVELS.index(level)
        for lower_level in self.LEVELS[idx + 1:]:
            setattr(self, lower_level, None)
            self.titles.pop(lower_level, None)

    def get_hierarchy(self) -> list[str]:
        """Return current hierarchy as a list of strings."""
        result = []
        for level in self.LEVELS:
            value = getattr(self, level)
            if value:
                # Format nicely
                level_name = level.replace("_", "-").capitalize()
                title = self.titles.get(level, "")
                if title:
                    result.append(f"{level_name} {value} - {title}")
                else:
                    result.append(f"{level_name} {value}")
        return result

    def get_hierarchy_string(self) -> str:
        """Return hierarchy as a formatted string for embedding."""
        return " > ".join(self.get_hierarchy())


def load_legifrance_mapping(script_dir: Path) -> dict:
    """Load the Legifrance ID to code name/URL mapping."""
    mapping_file = script_dir / "legifrance_mapping.json"
    if mapping_file.exists():
        with open(mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_code_info(pdf_path: Path, mapping: dict) -> dict:
    """Extract code information from PDF filename using mapping."""
    stem = pdf_path.stem  # e.g., "LEGITEXT000006070719"

    if stem in mapping:
        return {
            "source_book": mapping[stem]["name"],
            "source_url": mapping[stem]["url"],
            "legitext_id": stem
        }

    # Fallback: use filename as code name
    return {
        "source_book": stem,
        "source_url": f"https://www.legifrance.gouv.fr/codes/texte_lc/{stem}",
        "legitext_id": stem
    }


def extract_article_id(text: str) -> Optional[str]:
    """Extract article ID from text using patterns."""
    for pattern in ARTICLE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Normalize the article ID (replace en-dash with hyphen)
            article_id = match.group(1).replace("–", "-").replace(" ", "")
            return article_id
    return None


def detect_hierarchy_change(line: str) -> Optional[tuple[str, str, Optional[str]]]:
    """Detect if a line indicates a hierarchy change.

    Returns: (level, value, title) or None
    """
    line_upper = line.upper().strip()

    for pattern, level in HIERARCHY_PATTERNS:
        match = re.search(pattern, line_upper)
        if match:
            value = match.group(1)
            # Try to extract title (text after the hierarchy marker)
            title = None
            full_match = re.search(pattern + r"[:\s]*(.+)?", line_upper)
            if full_match and full_match.group(2):
                title = full_match.group(2).strip()
            return (level, value, title)

    return None


def extract_title_from_next_lines(lines: list[str], start_idx: int) -> Optional[str]:
    """Extract title from lines following a hierarchy marker."""
    for i in range(start_idx, min(start_idx + 3, len(lines))):
        line = lines[i].strip()
        # Skip empty lines and lines that look like article references
        if line and not re.match(r"^(Article|Art\.)", line, re.IGNORECASE):
            # Check if it looks like a title (not too long, no article pattern)
            if len(line) < 200 and not extract_article_id(line):
                return line
    return None


@dataclass
class ExtractedArticle:
    """Represents an extracted article with its metadata."""
    article_id: str
    content: str
    page: int
    hierarchy: list[str]


def process_pdf_with_hierarchy(file_path: Path) -> list[dict]:
    """Process PDF and extract articles with hierarchy tracking."""
    pdf = fitz.open(str(file_path))
    tracker = HierarchyTracker()
    articles = []
    current_article_id = None
    current_article_content = []
    current_article_page = 0
    current_article_hierarchy = []

    for page_num in range(len(pdf)):
        page = pdf[page_num]
        text = str(page.get_text("text"))
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Check for hierarchy changes
            hierarchy_change = detect_hierarchy_change(line_stripped)
            if hierarchy_change:
                level, value, title = hierarchy_change
                # Try to get better title from next lines if not found
                if not title:
                    title = extract_title_from_next_lines(lines, i + 1)
                tracker.update(level, value, title)
                continue

            # Check for new article
            article_id = extract_article_id(line_stripped)
            if article_id:
                # Save previous article if exists
                if current_article_id and current_article_content:
                    articles.append({
                        "article_id": current_article_id,
                        "content": "\n".join(current_article_content).strip(),
                        "page": current_article_page,
                        "hierarchy": current_article_hierarchy.copy()
                    })

                # Start new article
                current_article_id = article_id
                current_article_content = [line_stripped]
                current_article_page = page_num + 1  # 1-indexed
                current_article_hierarchy = tracker.get_hierarchy()
            elif current_article_id:
                # Continue current article
                current_article_content.append(line_stripped)

    # Save last article
    if current_article_id and current_article_content:
        articles.append({
            "article_id": current_article_id,
            "content": "\n".join(current_article_content).strip(),
            "page": current_article_page,
            "hierarchy": current_article_hierarchy.copy()
        })

    pdf.close()
    return articles


def create_enriched_content(article: dict, code_info: dict) -> str:
    """Create enriched content with context prefix for embedding."""
    parts = [f"Source: {code_info['source_book']}"]

    if article["hierarchy"]:
        parts.append(" > ".join(article["hierarchy"]))

    parts.append(f"Article {article['article_id']}")
    parts.append(f"URL: {code_info['source_url']}")
    parts.append("")  # Empty line before content
    parts.append(article["content"])

    return "\n".join(parts)


def process_single_pdf(pdf_file: Path, output_md_path: Path, output_json_path: Path,
                       mapping: dict) -> tuple[str, int, int]:
    """Process a single PDF file and save results."""
    code_info = get_code_info(pdf_file, mapping)

    # Extract articles with hierarchy
    articles = process_pdf_with_hierarchy(pdf_file)

    # Generate Markdown output (human-readable)
    md_lines = [f"# {code_info['source_book']}\n"]
    md_lines.append(f"Source: {code_info['source_url']}\n")
    md_lines.append(f"LEGITEXT ID: {code_info['legitext_id']}\n")
    md_lines.append("---\n")

    current_hierarchy = []
    for article in articles:
        # Add hierarchy headers when they change
        if article["hierarchy"] != current_hierarchy:
            current_hierarchy = article["hierarchy"]
            md_lines.append(f"\n## {' > '.join(current_hierarchy)}\n")

        md_lines.append(f"\n### Article {article['article_id']}\n")
        md_lines.append(f"*Page {article['page']}*\n")
        md_lines.append(f"\n{article['content']}\n")

    # Write Markdown
    md_file = output_md_path / f"{pdf_file.stem}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Create chunks with enriched content for RAG
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = []
    for article in articles:
        enriched_content = create_enriched_content(article, code_info)

        # Split if content is too long
        if len(enriched_content) > 1000:
            # Split the article content, keeping metadata prefix
            content_chunks = text_splitter.split_text(article["content"])
            for i, chunk_content in enumerate(content_chunks):
                # Recreate enriched content for each chunk
                chunk_article = article.copy()
                chunk_article["content"] = chunk_content
                enriched = create_enriched_content(chunk_article, code_info)

                chunks.append({
                    "page_content": enriched,
                    "metadata": {
                        "source": pdf_file.name,
                        "source_book": code_info["source_book"],
                        "source_url": code_info["source_url"],
                        "legitext_id": code_info["legitext_id"],
                        "article_id": article["article_id"],
                        "hierarchy": article["hierarchy"],
                        "page": article["page"],
                        "chunk_index": i
                    }
                })
        else:
            chunks.append({
                "page_content": enriched_content,
                "metadata": {
                    "source": pdf_file.name,
                    "source_book": code_info["source_book"],
                    "source_url": code_info["source_url"],
                    "legitext_id": code_info["legitext_id"],
                    "article_id": article["article_id"],
                    "hierarchy": article["hierarchy"],
                    "page": article["page"],
                    "chunk_index": 0
                }
            })

    # Write JSONL
    json_file = output_json_path / f"{pdf_file.stem}.jsonl"
    with open(json_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    return pdf_file.name, len(articles), len(chunks)


def process_folder(input_folder: Path, output_md_folder: Path, output_json_folder: Path,
                   mapping: dict, max_workers: int = 14):
    """Process all PDF files in input folder."""
    input_path = Path(input_folder)
    output_md_path = Path(output_md_folder)
    output_json_path = Path(output_json_folder)

    # Create output folders
    output_md_path.mkdir(parents=True, exist_ok=True)
    output_json_path.mkdir(parents=True, exist_ok=True)

    # Get all PDF files
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        return

    print(f"Processing {len(pdf_files)} PDF files with {max_workers} workers...")
    print(f"  Markdown output: {output_md_path}")
    print(f"  JSON output: {output_json_path}")
    print()

    total_articles = 0
    total_chunks = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_single_pdf, pdf_file, output_md_path, output_json_path, mapping
            ): pdf_file
            for pdf_file in pdf_files
        }

        for future in as_completed(futures):
            pdf_file = futures[future]
            try:
                pdf_name, num_articles, num_chunks = future.result()
                total_articles += num_articles
                total_chunks += num_chunks
                print(f"  {pdf_name}: {num_articles} articles -> {num_chunks} chunks")
            except Exception as e:
                print(f"  Error processing {pdf_file.name}: {e}")

    print()
    print(f"Processed {len(pdf_files)} files")
    print(f"Total articles: {total_articles}")
    print(f"Total chunks: {total_chunks}")


def validate_output(output_json_folder: Path):
    """Validate the generated output files."""
    output_path = Path(output_json_folder)
    jsonl_files = list(output_path.glob("*.jsonl"))

    print(f"\nValidating {len(jsonl_files)} output files...")

    issues = []
    stats = {
        "total_chunks": 0,
        "chunks_with_book": 0,
        "chunks_with_article": 0,
        "chunks_with_hierarchy": 0,
        "chunks_with_url": 0
    }

    for jsonl_file in jsonl_files:
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    chunk = json.loads(line)
                    stats["total_chunks"] += 1

                    metadata = chunk.get("metadata", {})

                    if metadata.get("source_book"):
                        stats["chunks_with_book"] += 1
                    else:
                        issues.append(f"{jsonl_file.name}:{line_num} - missing source_book")

                    if metadata.get("article_id"):
                        stats["chunks_with_article"] += 1

                    if metadata.get("hierarchy"):
                        stats["chunks_with_hierarchy"] += 1

                    if metadata.get("source_url"):
                        stats["chunks_with_url"] += 1

                except json.JSONDecodeError as e:
                    issues.append(f"{jsonl_file.name}:{line_num} - JSON error: {e}")

    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  With source_book: {stats['chunks_with_book']} ({100*stats['chunks_with_book']/max(1,stats['total_chunks']):.1f}%)")
    print(f"  With article_id: {stats['chunks_with_article']} ({100*stats['chunks_with_article']/max(1,stats['total_chunks']):.1f}%)")
    print(f"  With hierarchy: {stats['chunks_with_hierarchy']} ({100*stats['chunks_with_hierarchy']/max(1,stats['total_chunks']):.1f}%)")
    print(f"  With source_url: {stats['chunks_with_url']} ({100*stats['chunks_with_url']/max(1,stats['total_chunks']):.1f}%)")

    if issues:
        print(f"\n  Issues found: {len(issues)}")
        for issue in issues[:10]:  # Show first 10 issues
            print(f"    - {issue}")
        if len(issues) > 10:
            print(f"    ... and {len(issues) - 10} more")
    else:
        print("\n  No issues found!")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_folder = script_dir / "input"
    output_md_folder = script_dir / "01_output"
    output_json_folder = script_dir / "02_structured"

    # Load mapping
    mapping = load_legifrance_mapping(script_dir)
    print(f"Loaded mapping for {len(mapping)} codes")

    # Process all PDFs
    process_folder(input_folder, output_md_folder, output_json_folder, mapping)

    # Validate output
    validate_output(output_json_folder)
