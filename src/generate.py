"""Inject retrieved chunks into a prompt and generate a grounded response."""
from openai import OpenAI

GENERATION_MODEL = "gpt-4.1-nano"

SYSTEM_PROMPT = (
    "You are a SOC analyst assistant. Answer questions using ONLY the provided context. "
    "Cite which source document your answer draws from. "
    "If the context does not contain sufficient information to answer, say so explicitly — "
    "do not invent facts."
)


def format_context(chunks: list[dict]) -> str:
    sections = []
    for i, chunk in enumerate(chunks, 1):
        sections.append(f"[{i}] (source: {chunk['source']})\n{chunk['text']}")
    return "\n\n".join(sections)


def generate(query: str, chunks: list[dict]) -> dict:
    """
    Build a grounded prompt from retrieved chunks and call the generation model.
    Returns {response, sources_used, retrieved_chunks}.
    """
    oai = OpenAI()
    context = format_context(chunks)

    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    completion = oai.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
    )

    return {
        "response": completion.choices[0].message.content,
        "sources_used": sorted({c["source"] for c in chunks}),
        "retrieved_chunks": chunks,
    }
