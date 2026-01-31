#!/usr/bin/env python3
import argparse
import sys
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_anthropic import ChatAnthropic
from qdrant_client import QdrantClient

# Default configuration
DEFAULT_OLLAMA_URL = "http://192.168.1.58:8889/"
DEFAULT_OLLAMA_MODEL = "Qwen3 4B Instruct"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "law_library"


def get_llm(provider, model, url):
    """Initialize the LLM based on provider."""
    if provider == "claude":
        return ChatAnthropic(model=model)
    else:
        return Ollama(model=model, base_url=url)


def get_vector_store(qdrant_url, collection_name):
    """Initialize the vector store for RAG."""
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return QdrantVectorStore(
        client=QdrantClient(url=qdrant_url),
        collection_name=collection_name,
        embedding=embeddings
    )


def ask(query, llm, vector_store=None):
    """Ask a question, optionally using RAG context."""
    if vector_store:
        context = "\n".join([
            doc.page_content
            for doc in vector_store.similarity_search(query, k=3)
        ])
        prompt = f"""You are a legal assistant. Use the following law fragments to answer.
If the answer isn't in the context, say you don't know.

Context: {context}

Question: {query}"""
    else:
        prompt = f"""You are a legal assistant.

Question: {query}"""

    response = llm.invoke(prompt)
    # Handle both Ollama (str) and ChatAnthropic (AIMessage) responses
    if hasattr(response, 'content'):
        return response.content
    return response


def chat_mode(llm, vector_store):
    """Interactive chat loop."""
    mode = "RAG" if vector_store else "vanilla"
    print(f"Chat mode ({mode}). Type 'exit' or 'quit' to end.")

    while True:
        try:
            query = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        response = ask(query, llm, vector_store)
        print(f"\nAssistant: {response}")


def pipe_mode(llm, vector_store):
    """Read from stdin, write to stdout."""
    query = sys.stdin.read().strip()
    if query:
        response = ask(query, llm, vector_store)
        print(response)


def main():
    parser = argparse.ArgumentParser(
        description="Query legal documents with optional RAG support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --chat                      # Interactive chat with RAG
  %(prog)s --chat --vanilla            # Interactive chat without RAG
  %(prog)s "What is the penalty?"      # Single query with RAG
  echo "question" | %(prog)s           # Pipe input
  %(prog)s --provider claude           # Use Claude instead of Ollama
  %(prog)s --model "llama3" --url "http://localhost:11434"
"""
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Question to ask (if not using --chat or pipe)"
    )
    parser.add_argument(
        "--chat", "-c",
        action="store_true",
        help="Interactive chat mode"
    )
    parser.add_argument(
        "--vanilla", "-v",
        action="store_true",
        help="Disable RAG (no vector store context)"
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["ollama", "claude"],
        default="ollama",
        help="LLM provider (default: ollama)"
    )
    parser.add_argument(
        "--model", "-m",
        help=f"Model name (default: {DEFAULT_OLLAMA_MODEL} for Ollama, {DEFAULT_CLAUDE_MODEL} for Claude)"
    )
    parser.add_argument(
        "--url", "-u",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama server URL (default: {DEFAULT_OLLAMA_URL})"
    )
    parser.add_argument(
        "--qdrant-url",
        default=DEFAULT_QDRANT_URL,
        help=f"Qdrant server URL (default: {DEFAULT_QDRANT_URL})"
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help=f"Qdrant collection name (default: {DEFAULT_COLLECTION})"
    )

    args = parser.parse_args()

    # Determine model
    if args.model:
        model = args.model
    elif args.provider == "claude":
        model = DEFAULT_CLAUDE_MODEL
    else:
        model = DEFAULT_OLLAMA_MODEL

    # Initialize LLM
    llm = get_llm(args.provider, model, args.url)

    # Initialize vector store (unless vanilla mode)
    vector_store = None
    if not args.vanilla:
        vector_store = get_vector_store(args.qdrant_url, args.collection)

    # Determine execution mode
    if args.chat:
        chat_mode(llm, vector_store)
    elif args.query:
        response = ask(args.query, llm, vector_store)
        print(response)
    elif not sys.stdin.isatty():
        pipe_mode(llm, vector_store)
    else:
        # No input provided, default to chat mode
        chat_mode(llm, vector_store)


if __name__ == "__main__":
    main()
