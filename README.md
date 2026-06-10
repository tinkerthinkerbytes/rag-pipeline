# RAG Pipeline

Full RAG loop over a synthetic SOC document corpus — chunking, embedding, vector retrieval, grounded generation, and a structured eval harness.

**Stack:** OpenAI `text-embedding-3-small` · Chroma · `gpt-4.1-nano` · Python

## Architecture

```
corpus/ (.md files)
      │
      ▼
  [ingest.py]
  • Paragraph-level chunking, 500-char sentence-boundary fallback
  • text-embedding-3-small embeddings
  • Persisted to Chroma (cosine space)
      │
      ▼
  [retrieve.py]
  • Embed query, cosine search → top-k chunks + distances
      │
      ▼
  [generate.py]
  • Context block injected into prompt → gpt-4.1-nano
  • Response cites source documents
      │
      ▼
  [eval.py]
  • 5 test cases, 3 named dimensions
  • JSON report
```

## Setup

```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create `.env` — on Windows (PowerShell):
```powershell
[System.IO.File]::WriteAllText(".env", "OPENAI_API_KEY=sk-your-key-here")
```
On Mac/Linux:
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```
> **Windows:** avoid `Out-File -Encoding utf8` — PowerShell 5.1 writes UTF-8 with BOM, which causes `python-dotenv` to parse the key as `﻿OPENAI_API_KEY` (not found, silent failure). Avoid `echo > .env` — writes UTF-16, also breaks dotenv.

## Usage

```bash
# Ingest corpus (once, or after changes to corpus/)
python main.py ingest

# Query
python main.py query "What containment steps apply to a malware-infected endpoint?"

# Eval
python main.py eval
```

## Design Notes

**Chunking:** Paragraph-level (`\n\n`) — retrieval quality holds at semantic boundaries, not arbitrary character counts. Sentence-boundary fallback at 500 chars keeps chunks dense enough to embed usefully. Fixed-size windowing is fine for unstructured prose; structured docs (policies, runbooks) chunk more cleanly at paragraph breaks.

**Embedding:** `text-embedding-3-small` — good semantic similarity performance at low cost. `text-embedding-3-large` doesn't move the needle at this corpus scale.

**Retrieval:** Chroma persistent store, cosine similarity, `top_k=3`. Each result logged with chunk ID, source, and distance — retrieval decisions are traceable. Chroma is the right call below ~100k chunks; above that, pgvector or a dedicated service.

**Generation:** `gpt-4.1-nano`, `temperature=0.1`. System prompt constrains output to retrieved context and instructs explicit refusal when context is insufficient — primary faithfulness control.

## Evaluation

| Dimension | Measures | Failure means |
|---|---|---|
| `retrieval_hit` | Expected keywords in retrieved chunks | Vector search returned wrong chunks |
| `completeness` | Expected keywords in generated response | Generator dropped available information |
| `grounded` | Response is substantive, no refusal | Model couldn't use context |

`grounded` is a keyword-based proxy. True faithfulness (does the response assert things not in the retrieved context?) requires LLM-as-judge — implemented in the companion [Eval Harness](../eval-harness/) project.

## Known Limitations

| Limitation | Threshold | Mitigation |
|---|---|---|
| Chroma in-process | ~100k chunks | Migrate to Chroma server mode or pgvector |
| No chunk overlap | Boundary splits lose adjacent context | Add 1-sentence overlap at ingest |
| Fixed `top_k=3` | Deep queries may need more context | Adaptive `top_k` based on distance distribution |
| No reranking | Cosine similarity is a blunt first-pass | Cross-encoder reranker as second-stage filter |
| Single embedding model | May underperform on domain jargon | Domain-adapted or fine-tuned embeddings |

## Corpus

Six synthetic SOC documents — fabricated for demonstration, no real data.

| File | Type | Content |
|---|---|---|
| `incident_001.md` | Incident report | Phishing campaign, credential harvesting |
| `incident_002.md` | Incident report | Cobalt Strike beacon, Severity 1 |
| `policy_access_control.md` | Policy | MFA requirements, least privilege, access reviews |
| `policy_incident_response.md` | Policy | Severity tiers, SLAs, escalation paths |
| `runbook_phishing.md` | Runbook | Phishing triage, containment, evidence collection |
| `runbook_malware.md` | Runbook | Malware containment, forensics, remediation |
