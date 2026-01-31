from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from qdrant_client import QdrantClient

llm = Ollama(model="smollm2:1.7b")

def ask(query):
    return llm.invoke(f"""You are a legal assistant. Use the following law fragments to answer.
If the answer isn't in the context, say you don't know.

Question: {query}""")

if __name__ == "__main__":
    while True:
        query = input("\nYou: ").strip()
        if query.lower() in ("exit", "quit"):
            break
        print(f"\nAssistant: {ask(query)}")
