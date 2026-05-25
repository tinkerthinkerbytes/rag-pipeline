"""
RAG Pipeline CLI

Commands:
  ingest          Load corpus docs, chunk, embed, store to Chroma
  query <text>    Run a single query through the full RAG pipeline
  eval            Run the evaluation harness across all test cases
"""
import argparse

from dotenv import load_dotenv

load_dotenv()


def cmd_ingest(args):
    from src.ingest import ingest
    ingest(corpus_dir=args.corpus)


def cmd_query(args):
    from src.generate import generate
    from src.retrieve import retrieve

    chunks = retrieve(args.query, top_k=args.top_k)

    print("\nRETRIEVED CHUNKS:")
    for i, chunk in enumerate(chunks, 1):
        preview = chunk["text"][:120].replace("\n", " ")
        print(f"  [{i}] {chunk['source']}  (distance: {chunk['distance']})")
        print(f"      {preview}...")

    result = generate(args.query, chunks)

    print(f"\nRESPONSE:\n{result['response']}")
    print(f"\nSources used: {', '.join(result['sources_used'])}")


def cmd_eval(args):
    from src.eval import run_eval
    run_eval(top_k=args.top_k)


def main():
    parser = argparse.ArgumentParser(
        description="RAG Pipeline — SOC document corpus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Embed corpus and store in Chroma")
    p_ingest.add_argument("--corpus", default="corpus", help="Path to corpus directory")
    p_ingest.set_defaults(func=cmd_ingest)

    p_query = sub.add_parser("query", help="Query the RAG pipeline")
    p_query.add_argument("query", help="Question to answer")
    p_query.add_argument("--top-k", type=int, default=3, dest="top_k")
    p_query.set_defaults(func=cmd_query)

    p_eval = sub.add_parser("eval", help="Run evaluation harness")
    p_eval.add_argument("--top-k", type=int, default=3, dest="top_k")
    p_eval.set_defaults(func=cmd_eval)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
