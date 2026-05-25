"""Embed a query and retrieve the top-k most similar chunks from Chroma."""
import chromadb
from openai import OpenAI

from .ingest import CHROMA_PATH, COLLECTION_NAME, EMBED_MODEL


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """
    Embeds the query with the same model used at ingest time, then queries
    Chroma for the top_k nearest chunks by cosine distance.

    Returns a list of dicts: {chunk_id, source, text, distance}.
    Distance is cosine distance in [0, 2] — lower means more similar.
    """
    oai = OpenAI()

    try:
        chroma = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma.get_collection(COLLECTION_NAME)
    except Exception:
        raise RuntimeError(
            f"Vector store not found at '{CHROMA_PATH}/'. Run: python main.py ingest"
        )

    response = oai.embeddings.create(model=EMBED_MODEL, input=[query])
    query_embedding = response.data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "chunk_id": results["ids"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "text": results["documents"][0][i],
            "distance": round(results["distances"][0][i], 4),
        })

    return chunks
