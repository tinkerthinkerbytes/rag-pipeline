"""
FastAPI wrapper for the RAG pipeline.

Endpoints:
  POST /query   — run a query through the full RAG pipeline
  GET  /health  — liveness
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.ingest import ingest
    print("Ingesting corpus...", flush=True)
    ingest(corpus_dir="corpus")
    print("Corpus ready.", flush=True)
    yield


app = FastAPI(
    title="rag-pipeline",
    description="RAG over a SOC document corpus — paragraph-level chunking, cosine retrieval, grounded generation.",
    version="1.0.0",
    lifespan=lifespan,
)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 3


class ChunkResult(BaseModel):
    chunk_id: str
    source: str
    text: str
    distance: float


class QueryResponse(BaseModel):
    query: str
    response: str
    sources_used: list[str]
    chunks: list[ChunkResult]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    from src.generate import generate
    from src.retrieve import retrieve

    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    chunks = retrieve(req.query, top_k=req.top_k)
    result = generate(req.query, chunks)

    return QueryResponse(
        query=req.query,
        response=result["response"],
        sources_used=result["sources_used"],
        chunks=[ChunkResult(**c) for c in chunks],
    )
