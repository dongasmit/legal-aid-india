# JurisOne — AI-Powered Legal Assistant for Indian Law

JurisOne is an enterprise-grade AI legal assistant built for Indian law practitioners, researchers, and citizens. It combines a Retrieval-Augmented Generation (RAG) pipeline with a secure, multi-session chat interface to provide instant legal research, document drafting, and IPC → BNS code conversion.

---

## Features

- **Legal Research** — Ask complex legal questions and receive structured answers backed by cited laws, judgments, and precedents from the knowledge base.
- **Document Drafting** — Generate professionally formatted legal documents (petitions, notices, affidavits, contracts) with a guided interview flow.
- **IPC → BNS Converter** — Instantly map old Indian Penal Code sections to their new Bharatiya Nyaya Sanhita equivalents.
- **Multi-Case Workspace** — Maintain separate conversation threads for different matters simultaneously.
- **Source Verification Deck** — Inspect the exact source documents and PDF page scans used to generate each answer.
- **Export** — Download any drafted document as a `.docx` or `.pdf` file.
- **Auto-Harvester** — A GitHub Actions workflow runs every 6 hours to fetch the latest Supreme Court judgments and legal news and push them into the Pinecone knowledge base.
- **Secure Authentication** — User accounts are stored in a PostgreSQL database with bcrypt-hashed passwords (no plaintext storage).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend / UI | [Streamlit](https://streamlit.io) |
| LLM | [Groq](https://groq.com) — `llama-3.3-70b-versatile` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` via HuggingFace |
| Vector Store | [Pinecone](https://www.pinecone.io) |
| Orchestration | [LangChain](https://www.langchain.com) |
| Authentication | [bcrypt](https://pypi.org/project/bcrypt/) + [PostgreSQL](https://www.postgresql.org/) |
| PDF Generation | [fpdf2](https://py-pdf.github.io/fpdf2/) |
| CI / Auto-Harvesting | [GitHub Actions](https://github.com/features/actions) |

---

## Environment Variables

Create a `.env` file in the project root (never commit this file):

```
GROQ_API_KEY=your_groq_api_key
PINECONE_API_KEY=your_pinecone_api_key
DATABASE_URL=postgresql://user:password@host/dbname
```

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | API key from [console.groq.com](https://console.groq.com) |
| `PINECONE_API_KEY` | API key from [app.pinecone.io](https://app.pinecone.io) |
| `DATABASE_URL` | PostgreSQL connection string (e.g., from Neon, Supabase, or local) |

The Pinecone index must be named **`jurisone-index`** and configured with **384 dimensions** (matching the `all-MiniLM-L6-v2` embedding model).

---

## Setup & Running Locally

```bash
# 1. Clone the repository
git clone https://github.com/dongasmit/legal-aid-india.git
cd legal-aid-india

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file (see Environment Variables above)

# 5. Initialise the database (creates the users table)
python auth.py

# 6. Launch the app
streamlit run app_ui.py
```

---

## Populating the Knowledge Base

To ingest local PDF documents into Pinecone:

```bash
# Place PDFs in the source_docs/ folder, then run:
python ingest_data.py
```

For a large batch of historical PDFs (e.g., from Kaggle):

```bash
python local_ingest.py
```

---

## Auto-Harvester

The GitHub Actions workflow at `.github/workflows/auto_harvester.yml` runs `cloud_harvester.py` every 6 hours. It:

1. Parses the LiveLaw and Google News RSS feeds for the latest Supreme Court judgments and legal articles.
2. Skips URLs that have already been processed (tracked in `harvested_urls.json`).
3. Fetches and chunks new article content.
4. Embeds and upserts chunks into the Pinecone index.

The workflow requires the `PINECONE_API_KEY` secret to be set in the repository's **Settings → Secrets and variables → Actions**.

---

## Project Structure

```
legal-aid-india/
├── app_ui.py            # Streamlit frontend — entry point
├── app_logic.py         # AI/RAG logic (research, drafting, PDF generation)
├── auth.py              # bcrypt + PostgreSQL authentication
├── cloud_harvester.py   # GitHub Actions auto-harvester (RSS → Pinecone)
├── ingest_data.py       # Ingest local PDFs into Pinecone
├── local_ingest.py      # Bulk historical PDF ingestion
├── daily_update.py      # Google-search-based PDF downloader
├── build_vector_db.py   # DEPRECATED — legacy Chroma DB builder
├── config.py            # Centralised constants and logging setup
├── requirements.txt     # Python dependencies
├── source_docs/         # Local PDF storage folder
├── .github/
│   └── workflows/
│       └── auto_harvester.yml
└── .env                 # (not committed) API keys and DB URL
```
