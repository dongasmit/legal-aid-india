# ⚖️ JurisOne – Autonomous Legal AI Co-Counsel

JurisOne is an enterprise-grade Legal AI assistant specifically engineered for the Indian legal framework. It utilizes a robust Retrieval-Augmented Generation (RAG) architecture to provide accurate, hallucination-free legal research and document drafting, grounded entirely in 75 years of authentic Supreme Court of India judgments.

## 🚀 Key Features

* **Zero-Hallucination RAG Pipeline:** Bypasses standard LLM memory to synthesize answers strictly from a verified vector database of Indian case law.
* **The Verification Deck:** Builds absolute trust by dynamically rendering the original, scanned PDF pages of the exact court judgments the AI is citing.
* **Autonomous Ingestion Engine:** A headless scraper driven by GitHub Actions that automatically harvests, chunks, and vectors daily legal news via RSS feeds to keep the AI's knowledge base continuously updated.
* **Smart Context Routing:** Analyzes user prompts and chat history to intelligently switch between complex legal research and automated legal document drafting (e.g., Bail Applications, Petitions).
* **Secure Cloud Authentication:** Multi-threaded user state management backed by a serverless PostgreSQL database with `bcrypt` cryptographic password hashing.

## 🧠 System Architecture

JurisOne decouples the frontend interface from a high-performance, cloud-native backend:
1. **Frontend:** Streamlit handles the multi-threaded UI and session states.
2. **Orchestration:** LangChain manages the prompt injection and vector routing.
3. **Database:** Pinecone Cloud Vector Database stores 384-dimensional mathematical embeddings of legal texts.
4. **Inference Engine:** Llama-3.3-70b-versatile (via Groq API) provides lightning-fast reasoning and synthesis.
5. **Memory Management:** PyMuPDF combined with strict garbage collection (`gc.collect()`) enables the processing of massive historical datasets without OOM kernel crashes.

## 🛠️ Tech Stack

* **Language:** Python 3.11+
* **AI & NLP:** LangChain, HuggingFace (`all-MiniLM-L6-v2`), Groq API (Llama 3)
* **Databases:** Pinecone (Vector), PostgreSQL/Neon (Relational Auth)
* **Document Processing:** PyMuPDF (`fitz`), Pillow, `python-docx`, `fpdf`
* **Infrastructure:** GitHub Actions (CI/CD), Streamlit Community Cloud

## ⚙️ Local Setup & Installation

1. **Clone the repository:**
   git clone https://github.com/yourusername/legal-aid-india.git
   cd legal-aid-india

2. **Install dependencies:**
   pip install -r requirements.txt

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your API keys:
   GROQ_API_KEY="your_groq_key"
   PINECONE_API_KEY="your_pinecone_key"
   DATABASE_URL="your_postgresql_connection_string"

4. **Initialize the Database:**
   python auth.py

5. **Run the Application:**
   streamlit run app_ui.py

## ⚠️ Disclaimer
JurisOne is an AI research tool intended to assist legal professionals. It does not constitute formal legal advice.