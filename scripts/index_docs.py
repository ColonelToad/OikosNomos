"""
Index documentation files for RAG retrieval

This script processes markdown files in the docs/ directory and indexes them
in ChromaDB for RAG-based queries.
"""

import sys
from pathlib import Path
import argparse

# Add parent directory to path to import from rag-service
sys.path.insert(0, str(Path(__file__).parent.parent / "rag-service"))

from retriever import DocumentRetriever
from config import settings

def index_documents(docs_dir, chroma_dir):
    """
    Index all markdown documents in the docs directory
    
    Args:
        docs_dir: Path to docs directory
        chroma_dir: Path to ChromaDB data directory
    """
    print("=" * 60)
    print("OikosNomos Document Indexer")
    print("=" * 60)
    
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        print(f"✗ Error: Docs directory not found: {docs_path}")
        print(f"  Creating directory...")
        docs_path.mkdir(parents=True, exist_ok=True)
    
    # Count markdown files
    md_files = list(docs_path.glob("**/*.md"))
    if not md_files:
        print(f"✗ Warning: No markdown files found in {docs_path}")
        print(f"  Please add documentation files to {docs_path}")
        return
    
    print(f"\n✓ Found {len(md_files)} markdown files:")
    for f in md_files:
        print(f"  - {f.name}")
    
    # Initialize retriever
    print(f"\nInitializing retriever with ChromaDB at {chroma_dir}...")
    settings.docs_dir = str(docs_dir)
    settings.chroma_dir = str(chroma_dir)
    
    retriever = DocumentRetriever(chroma_dir=str(chroma_dir))
    retriever.initialize()
    
    # Rebuild index
    print("\nRebuilding index...")
    retriever.rebuild_index()
    
    # Show stats
    doc_count = retriever.get_document_count()
    print(f"\n✓ Indexing complete!")
    print(f"  Total document chunks: {doc_count}")
    
    # Test search
    print("\nTesting search...")
    test_queries = [
        "What is time-of-use pricing?",
        "How is CO2 calculated?",
        "Device consumption"
    ]
    
    for query in test_queries:
        results = retriever.search(query, k=2)
        print(f"\n  Query: '{query}'")
        if results:
            print(f"  Found {len(results)} results:")
            for i, doc in enumerate(results[:1], 1):
                print(f"    {i}. {doc['id']} (score: {doc['score']:.3f})")
                print(f"       {doc['content'][:100]}...")
        else:
            print(f"  No results found")
    
    print("\n" + "=" * 60)
    print("✓ Done!")

def main():
    parser = argparse.ArgumentParser(description="Index documentation for OikosNomos RAG")
    parser.add_argument("--docs-dir", default="docs", help="Documentation directory")
    parser.add_argument("--chroma-dir", default="rag-service/chroma_data", 
                        help="ChromaDB data directory")
    
    args = parser.parse_args()
    
    try:
        index_documents(args.docs_dir, args.chroma_dir)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
