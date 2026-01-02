import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
import logging
from typing import List, Dict
import os

logger = logging.getLogger(__name__)

class DocumentRetriever:
    """
    Handles document storage and retrieval using ChromaDB
    """
    
    def __init__(self, chroma_dir: str = "chroma_data"):
        self.chroma_dir = Path(chroma_dir)
        self.client = None
        self.collection = None
        
    def initialize(self):
        """Initialize ChromaDB client and collection"""
        try:
            self.chroma_dir.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=str(self.chroma_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="oikosnomo_docs",
                metadata={"description": "OikosNomos documentation and context"}
            )
            
            logger.info(f"ChromaDB initialized. Documents: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Check if retriever is ready"""
        return self.collection is not None
    
    def get_document_count(self) -> int:
        """Get number of documents in collection"""
        if self.collection:
            return self.collection.count()
        return 0
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of documents with content and metadata
        """
        if not self.is_ready():
            logger.warning("Retriever not initialized")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k
            )
            
            documents = []
            if results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    documents.append({
                        'id': results['ids'][0][i] if results['ids'] else f"doc_{i}",
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'score': results['distances'][0][i] if results['distances'] else 0.0
                    })
            
            logger.info(f"Retrieved {len(documents)} documents for query")
            return documents
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def add_documents(self, documents: List[Dict]):
        """
        Add documents to the collection
        
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
        """
        if not self.is_ready():
            raise ValueError("Retriever not initialized")
        
        try:
            ids = [doc['id'] for doc in documents]
            contents = [doc['content'] for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]
            
            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise
    
    def rebuild_index(self):
        """
        Rebuild the entire index from docs directory
        
        This reads all markdown files from the docs directory and indexes them.
        """
        from config import settings
        
        # Delete existing collection
        if self.collection:
            self.client.delete_collection(name="oikosnomo_docs")
        
        # Recreate
        self.initialize()
        
        # Load documents from docs directory
        docs_path = Path(settings.docs_dir)
        if not docs_path.exists():
            logger.warning(f"Docs directory not found: {docs_path}")
            return
        
        documents = []
        for md_file in docs_path.glob("**/*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split into chunks
                chunks = self._chunk_text(content, settings.chunk_size, settings.chunk_overlap)
                
                for i, chunk in enumerate(chunks):
                    documents.append({
                        'id': f"{md_file.stem}_chunk_{i}",
                        'content': chunk,
                        'metadata': {
                            'source': str(md_file.name),
                            'chunk_index': i
                        }
                    })
                
                logger.info(f"Loaded {len(chunks)} chunks from {md_file.name}")
                
            except Exception as e:
                logger.error(f"Error loading {md_file}: {e}")
        
        if documents:
            self.add_documents(documents)
            logger.info(f"Index rebuilt with {len(documents)} document chunks")
        else:
            logger.warning("No documents found to index")
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to split
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at paragraph or sentence
            if end < len(text):
                last_para = chunk.rfind('\n\n')
                last_sentence = chunk.rfind('. ')
                
                if last_para > chunk_size * 0.5:
                    end = start + last_para
                    chunk = text[start:end]
                elif last_sentence > chunk_size * 0.5:
                    end = start + last_sentence + 1
                    chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - overlap
        
        return chunks
