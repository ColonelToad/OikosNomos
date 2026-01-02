from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
from datetime import datetime
import httpx

from retriever import DocumentRetriever
from llm_client import LLMClient
from config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OikosNomos RAG Service", version="1.0.0")

# Global instances
retriever = DocumentRetriever()
llm_client = LLMClient(settings)

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    try:
        retriever.initialize()
        logger.info("RAG service started successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

class QueryRequest(BaseModel):
    question: str
    home_id: str = "home_001"
    include_citations: bool = True
    
class Citation(BaseModel):
    doc_id: str
    content: str
    relevance_score: float

class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: Optional[List[Citation]]
    system_state: Optional[Dict]
    timestamp: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OikosNomos RAG Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "vector_store_loaded": retriever.is_ready(),
        "llm_configured": llm_client.is_configured()
    }

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Answer a natural language question about energy costs and scenarios
    
    Uses RAG (Retrieval Augmented Generation) to:
    1. Retrieve relevant documents from knowledge base
    2. Fetch current system state (billing, forecasts)
    3. Generate answer using LLM with context
    
    Args:
        request: QueryRequest with user question
        
    Returns:
        QueryResponse with answer and citations
    """
    try:
        logger.info(f"Query received: {request.question}")
        
        # Step 1: Retrieve relevant documents
        retrieved_docs = retriever.search(
            query=request.question,
            k=5
        )
        
        # Step 2: Fetch current system state
        system_state = await fetch_system_state(request.home_id)
        
        # Step 3: Build context and generate answer
        answer = llm_client.generate_answer(
            question=request.question,
            documents=retrieved_docs,
            system_state=system_state
        )
        
        # Prepare citations
        citations = None
        if request.include_citations and retrieved_docs:
            citations = [
                Citation(
                    doc_id=doc['id'],
                    content=doc['content'][:200] + "...",
                    relevance_score=doc.get('score', 0.0)
                )
                for doc in retrieved_docs[:3]  # Top 3
            ]
        
        logger.info(f"Query answered successfully")
        
        return QueryResponse(
            question=request.question,
            answer=answer,
            citations=citations,
            system_state=system_state if request.include_citations else None,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_system_state(home_id: str) -> Dict:
    """
    Fetch current system state from other services
    
    Returns:
        Dictionary with current billing, forecast, etc.
    """
    state = {
        'home_id': home_id,
        'billing': None,
        'forecast': None,
        'timestamp': datetime.now().isoformat()
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Fetch billing info
        try:
            billing_url = f"{settings.billing_engine_url}/billing/current"
            response = await client.get(billing_url)
            if response.status_code == 200:
                state['billing'] = response.json()
        except Exception as e:
            logger.warning(f"Could not fetch billing data: {e}")
        
        # Fetch forecast
        try:
            forecast_url = f"{settings.forecast_service_url}/predict"
            response = await client.post(
                forecast_url,
                json={"home_id": home_id, "horizon_hours": 3}
            )
            if response.status_code == 200:
                state['forecast'] = response.json()
        except Exception as e:
            logger.warning(f"Could not fetch forecast: {e}")
    
    return state

@app.post("/index/rebuild")
async def rebuild_index():
    """
    Rebuild the vector store index from documents
    
    This should be called when documentation is updated.
    """
    try:
        logger.info("Rebuilding vector store index...")
        retriever.rebuild_index()
        logger.info("Index rebuilt successfully")
        
        return {
            "status": "success",
            "message": "Vector store index rebuilt",
            "document_count": retriever.get_document_count()
        }
    except Exception as e:
        logger.error(f"Index rebuild error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/index/stats")
async def index_stats():
    """Get statistics about the vector store"""
    try:
        return {
            "document_count": retriever.get_document_count(),
            "is_ready": retriever.is_ready()
        }
    except Exception as e:
        logger.error(f"Error getting index stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
