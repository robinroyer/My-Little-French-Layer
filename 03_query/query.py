from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from qdrant_client import QdrantClient

embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
vector_store = QdrantVectorStore(
    client=QdrantClient(url="http://localhost:6333"),
    collection_name="law_library",
    embedding=embeddings
)
llm = Ollama(model="smollm2:1.7b")

def ask(query):
    context = "\n".join([doc.page_content for doc in vector_store.similarity_search(query, k=3)])
    return llm.invoke(f"""You are a legal assistant. Use the following law fragments to answer.
If the answer isn't in the context, say you don't know.

Context: {context}

Question: {query}""")

if __name__ == "__main__":
    while True:
        query = input("\nYou: ").strip()
        if query.lower() in ("exit", "quit"):
            break
        print(f"\nAssistant: {ask(query)}")
