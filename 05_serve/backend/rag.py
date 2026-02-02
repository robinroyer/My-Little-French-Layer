"""RAG (Retrieval Augmented Generation) logic for MLFL."""
from dataclasses import dataclass
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from config import config


@dataclass
class Source:
    """A source document retrieved from the vector store."""

    content: str
    metadata: dict


def get_vector_store() -> QdrantVectorStore | None:
    """Initialize the vector store for RAG."""
    try:
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        return QdrantVectorStore(
            client=QdrantClient(url=config.qdrant_url),
            collection_name=config.qdrant_collection,
            embedding=embeddings,
        )
    except Exception:
        return None


def check_qdrant_health() -> bool:
    """Check if Qdrant is accessible."""
    try:
        client = QdrantClient(url=config.qdrant_url)
        client.get_collections()
        return True
    except (UnexpectedResponse, Exception):
        return False


def retrieve_context(vector_store: QdrantVectorStore, query: str, k: int = 3, score_threshold: float = 0.7) -> tuple[str, list[Source]]:
    """Retrieve relevant documents and return context string with sources."""
    docs = vector_store.similarity_search(
        query,
        score_threshold=score_threshold,
        k=k)

    sources = [
        Source(
            content=doc.page_content,
            metadata=doc.metadata or {},
        )
        for doc in docs
    ]

    context = "\n\n---\n\n".join([doc.page_content for doc in docs])
    return context, sources


def build_prompt(query: str, context: str | None = None, history: list[dict] | None = None) -> str:
    """Build the prompt for the LLM."""
    system_prompt = """Tu es un assistant juridique français spécialisé dans le conseil et l'analyse de textes légaux.
    Ta mission est d'aider les utilisateurs à comprendre le droit français avec rigueur et précision.

    RÈGLES CRITIQUES :
    1. ANALYSE DU CONTEXTE : Examine si les extraits fournis sont réellement pertinents par rapport à la question.
    2. PORTE DE SORTIE : Si le contexte fourni est hors-sujet, incomplet ou n'a aucun rapport direct avec la requête, ne tente pas d'inventer une réponse. Dis explicitement que les documents à ta disposition ne permettent pas de répondre précisément.
    3. REQUÊTES COURTES : Si la question est trop vague (ex: un seul mot), demande à l'utilisateur de préciser sa situation juridique avant d'utiliser le contexte.
    4. FIDÉLITÉ : Ne cite des articles que s'ils figurent dans le contexte ou si tu es certain de leur application exacte.

    Réponds toujours dans la même langue que l'utilisateur."""

    if context:
        system_prompt += f"""
    ---
    CONTEXTE JURIDIQUE À UTILISER PRIORITAIREMENT :
    {context}
    ---
    INSTRUCTION FINALE : Si le contexte ci-dessus ne contient pas la solution spécifique à la question, réponds : "D'après les documents consultés, je ne dispose pas d'assez d'informations pour répondre précisément. Pourriez-vous clarifier votre demande ?"."""
        


    # Build conversation history
    messages = [system_prompt]

    if history:
        for msg in history[-6:]:  # Keep last 6 messages for context
            role = "User" if msg["role"] == "user" else "Assistant"
            messages.append(f"{role}: {msg['content']}")

    messages.append(f"User: {query}")
    messages.append("Assistant:")

    return "\n\n".join(messages)
