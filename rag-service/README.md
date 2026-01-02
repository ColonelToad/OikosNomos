# RAG Service

Python FastAPI service providing LLM-powered natural language queries with retrieval-augmented generation (RAG).

## Features

- ChromaDB vector store for document retrieval
- OpenAI GPT-4 or Anthropic Claude LLM
- Retrieval of relevant documentation and tariff info
- Integration with billing and forecast services
- Citation tracking

## API Endpoints

### `POST /query`
Answer a natural language question.

**Request**:
```json
{
  "question": "Why is my projected bill $120?",
  "home_id": "home_001",
  "include_citations": true
}
```

**Response**:
```json
{
  "question": "Why is my projected bill $120?",
  "answer": "Your projected monthly bill of $120 is based on...",
  "citations": [
    {
      "doc_id": "tariff_pge_e6_chunk_0",
      "content": "PG&E E-6 TOU tariff...",
      "relevance_score": 0.85
    }
  ],
  "system_state": {...},
  "timestamp": "2026-01-02T14:30:00"
}
```

### `POST /index/rebuild`
Rebuild the vector store from docs directory.

### `GET /index/stats`
Get index statistics.

## Configuration

### Environment Variables

```bash
# Required: Choose one
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# LLM Provider (openai or anthropic)
LLM_PROVIDER=openai

# Model
LLM_MODEL=gpt-4o-mini  # or claude-3-5-haiku-20241022
```

## Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY=sk-...

# Run locally
uvicorn main:app --reload

# Rebuild index
curl -X POST http://localhost:8000/index/rebuild
```

## Document Management

Place markdown files in `docs/` directory:

```
docs/
├── tariff_pge_e6.md
├── device_profiles.md
├── project_overview.md
└── faq.md
```

Rebuild index after adding/updating docs:

```bash
curl -X POST http://localhost:8003/index/rebuild
```

## RAG Architecture

1. **Query** → Embed user question
2. **Retrieve** → Search ChromaDB for top-k relevant docs
3. **Fetch State** → Get current billing/forecast from services
4. **Generate** → LLM answers using retrieved context + state
5. **Respond** → Return answer with citations

## Example Queries

- "Why is my bill $120?"
- "Can I get back to my 2015 bill of $60?"
- "What device should I remove first?"
- "How much would I save without the EV charger?"
- "Explain my time-of-use charges"
