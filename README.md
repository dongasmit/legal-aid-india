# ⚖️ JurisOne — Autonomous Legal AI Co-Counsel

> **Self-healing Agentic RAG for the Indian legal framework**
> Powered by LangGraph · Qdrant Hybrid Search · Groq Llama-3.3

JurisOne is an enterprise-grade Legal AI assistant that provides hallucination-resistant legal research, automated document drafting, and real-time legal source verification — engineered specifically for Indian law.

---

## 🧠 Architecture — Agentic RAG 2.0

JurisOne uses a **cyclic, self-healing agent** (not a linear chain) built with [LangGraph](https://github.com/langchain-ai/langgraph). The system knows when it doesn't know — falling back to trusted web sources instead of hallucinating.

```
User Query
    │
    ▼
┌─── LangGraph State ─────────────┐
│  Node 1: Hybrid Retrieve         │
│  (Qdrant: dense MiniLM + BM25)   │
│          │                        │
│  Node 2: FlashRank Rerank        │
│          │                        │
│  Node 3: Relevance Grade         │
│          │                        │
│   ┌──────▼──────┐                 │
│   │ RAG OK?     │                 │
│   │ YES → Gen   │                 │
│   │ NO  → Web   │                 │
│   └──────┬──────┘                 │
│          ▼                        │
│  Node 4: Generate (structured)    │
│          │                        │
│  Node 5: Hallucination Check      │
│  (loops back to fix or rewrite)   │
└───────────────────────────────────┘
            │
            ▼
   LegalResponse (JSON)
```

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **Hybrid Search** | Dense (MiniLM-384) + Sparse (BM25) vectors with Reciprocal Rank Fusion |
| **Cross-Encoder Reranking** | FlashRank reranks top-20 candidates down to top-5 |
| **Self-Healing Loop** | Hallucination critic detects ungrounded claims → retries → rewrites query → graceful exit |
| **Web Fallback** | Scrapes Indian Kanoon when local corpus lacks relevant docs |
| **Verification Deck** | Renders original PDF pages of cited sources for visual proof |
| **Smart Draft Routing** | Detects drafting intent → interviews for missing details → generates DOCX/PDF |
| **Structured Output** | All responses are Pydantic `LegalResponse` with citations, confidence, and source type |

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Llama-3.3-70b-versatile via [Groq](https://groq.com) |
| **Orchestration** | LangGraph (cyclic state machine) + LangChain |
| **Vector DB** | [Qdrant](https://qdrant.tech) (self-hosted via Podman) |
| **Embeddings** | `all-MiniLM-L6-v2` (384-dim, HuggingFace) |
| **Sparse Search** | `bm25s` (fitted on full corpus, persisted to disk) |
| **Reranking** | FlashRank (`ms-marco-TinyBERT-L-2-v2`) |
| **Web Fallback** | Indian Kanoon public scraping via `httpx` + `BeautifulSoup` |
| **API** | FastAPI with CORS for Next.js frontend |
| **Frontend** | Next.js 16+ (React 19, Tailwind, Dark Mode) + Streamlit (legacy) |
| **Doc Processing** | PyMuPDF, python-docx, fpdf |
| **Containerization** | Podman (rootless, Fedora Linux) |

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.11+
- [Podman](https://podman.io) (or Docker) for Qdrant
- A [Groq API key](https://console.groq.com) (free tier works)

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/legal-aid-india.git
cd legal-aid-india
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key

# Qdrant (local Podman container)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=jurisone_legal

# Indian Kanoon (leave empty to use public scraping)
INDIANKANOON_API_KEY=
```

### 3. Start Qdrant

```bash
# Using the included management script
bash qdrant-podman.sh start

# Or manually with Podman/Docker
podman run -d --name qdrant-jurisone \
  -p 127.0.0.1:6333:6333 -p 127.0.0.1:6334:6334 \
  -v qdrant-jurisone-data:/qdrant/storage:z \
  docker.io/qdrant/qdrant
```

### 4. Initialize Collection & Ingest

```bash
python qdrant_setup.py                    # Create collection schema
python local_ingest.py --skip-context     # Ingest all PDFs (fast, no API calls)
# python local_ingest.py                  # With Groq contextual enrichment (slow, rate-limited)
```

### 5. Run the API Server

```bash
python api.py
# API available at http://localhost:8000
```

### 6. Run the Frontend

```bash
cd jurisone-frontend && npm run dev
# Frontend available at http://localhost:3000
```

---

## 📁 Project Structure

```
legal-aid-india/
├── agent_graph.py          # LangGraph agentic RAG workflow (Phase 5)
├── retrieval.py            # Hybrid search + FlashRank reranking (Phase 3)
├── web_search.py           # Indian Kanoon web fallback (Phase 4)
├── schemas.py              # Pydantic LegalResponse + Citation models (Phase 6)
├── local_ingest.py         # Contextual ingestion pipeline (Phase 2)
├── qdrant_setup.py         # One-time Qdrant collection creation (Phase 1)
├── qdrant-podman.sh        # Podman container lifecycle management
├── app_logic.py            # Smart routing (Research → Agent, Draft → Drafter)
├── api.py                  # FastAPI endpoints (/api/chat, /api/document/image)
├── app_ui.py               # Streamlit UI (legacy)
├── auth.py                 # User authentication (bcrypt + PostgreSQL)
├── requirements.txt        # Python dependencies
├── .env                    # API keys and config (not committed)
├── source_docs/            # PDF corpus (Indian law, SC judgments, statutes)
├── bm25_model/             # Persisted BM25 sparse model (generated at ingest)
├── jurisone-frontend/      # Next.js frontend application
│   └── src/
│       ├── app/            # Next.js pages
│       ├── components/     # React components (VerificationDeck, etc.)
│       ├── context/        # React context providers
│       └── lib/            # Utility functions
└── docs/
    ├── ARCHITECTURE.md     # Detailed system architecture
    ├── API.md              # API endpoint reference
    └── INGESTION.md        # Data pipeline documentation
```

---

## 🧪 Testing

```bash
# Test hybrid retrieval standalone
python retrieval.py "bail application IPC 302 grounds"

# Test web search fallback
python web_search.py "Bharatiya Nyaya Sanhita section 103"

# Test full agentic graph
python agent_graph.py "What is the penalty for murder under BNS section 103?"
```

---

## 📊 Corpus Statistics

| Metric | Value |
|--------|-------|
| PDFs ingested | 42 |
| Total chunks | 13,794 |
| Dense vector dim | 384 (Cosine) |
| BM25 vocabulary | ~28,195 terms |
| Qdrant point count | 13,794 |

---

## ⚠️ Disclaimer

JurisOne is an AI research tool intended to assist legal professionals. It does not constitute formal legal advice. Always verify AI-generated analysis against authoritative legal sources.

---

## 📝 License

This project is intended for educational and research purposes.