# RAG Pipeline

A production-pattern Retrieval-Augmented Generation pipeline built on a synthetic SOC document corpus. Demonstrates the full RAG loop: corpus ingestion, chunking, embedding, vector retrieval, grounded generation, and a structured evaluation harness.

## Architecture

```
corpus/ (.md files)
      │
      ▼
  [ingest.py]
  • Paragraph-level chunking
  • OpenAI text-embedding-3-small
  • Stored in Chroma (cosine space)
      │
      ▼
  [retrieve.py]
  • Embed query (same model)
  • Cosine similarity search → top-k chunks + distances
      │
      ▼
  [generate.py]
  • Format context block from retrieved chunks
  • Grounded prompt → gpt-4.1-nano
  • Response cites source documents
      │
      ▼
  [eval.py]
  • 5 test cases with expected keywords
  • Measures: retrieval_hit, completeness, grounded
  • Outputs JSON report
```

## Setup

```bash
pip install -r requirements.txt
```

On Windows (PowerShell), create the `.env` file with:
```powershell
'OPENAI_API_KEY=sk-your-key-here' | Out-File -FilePath .env -Encoding utf8
```

On Mac/Linux:
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

> Note: avoid using `echo "..." > .env` in PowerShell — the `>` redirect writes UTF-16 by default, which breaks `python-dotenv`.

## Usage

```bash
# 1. Ingest the corpus (run once, or after changing corpus/)
python main.py ingest

# 2. Query the pipeline
python main.py query "What containment steps apply to a malware-infected endpoint?"

# 3. Run the evaluation harness
python main.py eval
```

## Design Decisions

### Chunking Strategy

**Approach:** Paragraph-level primary split (`\n\n`), with a sentence-boundary fallback for paragraphs exceeding 500 characters.

**Why paragraph-level:** A paragraph is a semantic unit — it expresses a single idea. Splitting at arbitrary character counts (e.g. fixed-size sliding windows) cuts across logical boundaries, producing chunks where the first sentence belongs to one topic and the last belongs to another. That degrades both embedding quality (the vector represents a blended idea) and retrieved context (the generator gets partial thoughts).

**Why 500-char fallback:** Embedding models encode a chunk into a single fixed-dimension vector. Very long chunks average together many ideas, making the vector less discriminative. 500 characters (~80-100 words) is a practical ceiling for this corpus — long enough to carry meaning, short enough to remain specific.

**Trade-off vs alternatives:**
- *Fixed-size with overlap* is more common in tutorials because it's corpus-agnostic, but produces noisier chunks for structured documents like policies and runbooks.
- *Semantic chunking* (split when sentence embedding similarity drops) is theoretically superior but adds latency and complexity at ingest time — overkill for a corpus this size.

### Embedding Model

**Model:** `text-embedding-3-small` (OpenAI)

**Why:** Strong semantic similarity performance, 1536-dimension output, low cost. For a corpus of this scale (~50 chunks), the quality ceiling of `text-embedding-3-large` (3072 dimensions) adds cost with no measurable benefit. The same model is used for both corpus chunks and query embeddings — this is required, not optional; mismatched models produce meaningless similarity scores.

### Retrieval Approach

**Method:** Cosine similarity via Chroma's persistent vector store. `top_k=3` by default.

**Why cosine over L2:** Cosine similarity measures directional alignment between vectors, not absolute distance. This makes it robust to differences in text length — a short query and a long chunk can still score highly if they share conceptual direction. L2 distance penalises length differences.

**Why Chroma:** Zero infrastructure, embedded in-process, Python-native, persists to disk. Appropriate for corpora up to ~100k chunks. At larger scale (millions of chunks, concurrent queries), a dedicated vector database (Pinecone, Weaviate, pgvector) would be warranted.

**Retrieved context logging:** Each query logs chunk IDs, source documents, and cosine distances so retrieval decisions are traceable. In production this feeds observability tooling.

### Generation

**Model:** `gpt-4.1-nano` — cost-efficient instruction-following, large context window, no reasoning overhead needed for grounded Q&A.

**Temperature:** 0.1 — low variance is correct for factual retrieval tasks. Higher temperature introduces hallucination risk without benefit.

**Prompt design:** System prompt explicitly constrains the model to the provided context and instructs it to flag when context is insufficient. This is the primary faithfulness control — the model is told it is not allowed to invent.

## Evaluation Harness

Five test cases covering the three document types (incident reports, policies, runbooks). Each case defines a query and expected keywords — terms that must appear in both the retrieved chunks (retrieval quality) and the final response (completeness).

| Dimension | What it measures | Failure means |
|---|---|---|
| `retrieval_hit` | Expected keywords present in retrieved chunks | Vector search failed — wrong chunks returned |
| `completeness` | Expected keywords present in generated response | Generator dropped available information |
| `grounded` | Response is substantive, no explicit refusal | Model couldn't use context or context was empty |

**Limitation:** `grounded` is a proxy. True faithfulness measurement — does the response contain claims not supported by the retrieved context? — requires an LLM-as-judge step. That is implemented in the companion [Eval Harness](../eval-harness/) project.

## Known Limitations at Scale

| Limitation | Threshold | Mitigation |
|---|---|---|
| Chroma in-process | ~100k chunks before latency degrades | Migrate to Chroma server mode or pgvector |
| No chunk overlap | Adjacent context can be split across chunk boundaries | Add 1-sentence overlap at ingest |
| Fixed `top_k=3` | Deep queries may need more context | Make `top_k` adaptive based on distance distribution |
| No reranking | Cosine similarity is a blunt instrument | Add a cross-encoder reranker (e.g. Cohere Rerank) as a second-stage filter |
| Single embedding model | `text-embedding-3-small` may underperform on domain-specific jargon | Fine-tune embeddings or use a domain-adapted model if retrieval degrades |

## Corpus

Six synthetic SOC documents — two incident reports, two security policies, two operational runbooks. All content is fabricated for demonstration purposes.

| File | Type | Content |
|---|---|---|
| `incident_001.md` | Incident report | Phishing campaign, credential harvesting |
| `incident_002.md` | Incident report | Cobalt Strike beacon, Severity 1 |
| `policy_access_control.md` | Policy | MFA requirements, least privilege, access reviews |
| `policy_incident_response.md` | Policy | Severity tiers, SLAs, escalation paths |
| `runbook_phishing.md` | Runbook | Phishing triage, containment, evidence collection |
| `runbook_malware.md` | Runbook | Malware containment, forensics, remediation |
