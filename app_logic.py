import os
import io
import sys
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from docx import Document
from fpdf import FPDF
import fitz  # PyMuPDF
from PIL import Image

# 1. SETUP
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_PATH = "vector_db"

if not GROQ_API_KEY:
    raise ValueError("❌ API Key missing!")

# 2. RESOURCES
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
retriever = vector_db.as_retriever(search_kwargs={"k": 5})

llm = ChatGroq(temperature=0.1, model_name="llama-3.3-70b-versatile", api_key=GROQ_API_KEY)

# --- HELPER FUNCTIONS ---
def generate_docx(text):
    doc = Document()
    doc.add_heading('JurisOne Legal Draft', 0)
    for paragraph in text.split('\n'):
        if paragraph.strip():
            doc.add_paragraph(paragraph.strip())
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, clean_text)
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer

def get_source_image(file_path, page_number):
    try:
        clean_path = file_path.replace("\\", "/")
        filename = os.path.basename(clean_path)
        local_path = os.path.join("source_docs", filename)
        if not os.path.exists(local_path): return None
        doc = fitz.open(local_path)
        if page_number >= len(doc): return None
        page = doc.load_page(page_number)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    except: return None

# --- INTELLIGENCE FUNCTIONS ---

# 1. THE STRATEGIST (Research with Memory)
def get_research_response(query, history_text):
    """
    Research that remembers context. 
    It combines history + new query to find the right documents.
    """
    
    # STEP A: CONTEXTUAL SEARCH QUERY
    # This fixes the "Deaf Bot" issue. We tell it: "Look at the history!"
    query_transform_prompt = ChatPromptTemplate.from_template(
        """
        Given the conversation history and the new question, create a precise search query.
        
        HISTORY: {history}
        NEW QUESTION: {question}
        
        If the question is "What documents do I need?", and history is about "Attempted Murder", 
        the search query must be: "Documents required for Attempted Murder case India".
        
        OUTPUT ONLY THE SEARCH QUERY.
        """
    )
    
    # Create the search query
    search_query_chain = query_transform_prompt | llm | StrOutputParser()
    generated_query = search_query_chain.invoke({"history": history_text, "question": query})
    print(f"DEBUG: Generated Search Query: {generated_query}") # See this in terminal

    # STEP B: SENIOR PARTNER ANSWER
    answer_prompt = ChatPromptTemplate.from_template(
        """
        You are a Senior Legal Partner. Provide strategic advice.
        
        CONTEXT (Laws/Judgments): {context}
        USER QUERY: {question}
        
        **INSTRUCTIONS:**
        1. Answer based on the CONTEXT provided.
        2. If the user asks for documents, list them clearly.
        3. END your response by saying: 
           "I can draft these for you. Just say: 'Draft the [Document Name]'."
        
        **FORMAT:**
        - **Executive Summary**
        - **Legal Provisions** (Cite Sections)
        - **Precedents** (Cite Case Names if in context)
        - **Strategic Steps**
        """
    )
    
    rag_chain = (
        RunnableParallel({
            "context": lambda x: retriever.invoke(generated_query), # Use the SMART query
            "question": RunnablePassthrough()
        })
        .assign(answer= answer_prompt | llm | StrOutputParser())
    )
    
    return rag_chain.invoke(query)

# 2. THE INTERVIEWER (Context Aware)
def analyze_drafting_needs(user_input, history_text):
    analyzer_prompt = ChatPromptTemplate.from_template(
        """
        You are a Legal Drafting Expert.
        Analyze the HISTORY to understand what case we are dealing with.
        
        Current Request: {input}
        Full Conversation History: {history}
        
        **TASK:**
        1. Extract the Case Type from history (e.g., Hit and Run, Murder, Rent).
        2. Identify the document the user wants to draft now.
        3. Check if we have names/dates/details.
        
        **OUTPUT JSON ONLY:**
        {{
            "status": "READY" or "MISSING_INFO",
            "missing_details": ["List of questions"],
            "document_type": "Specific Document Name (e.g. Bail Application for Attempted Murder)"
        }}
        """
    )
    chain = analyzer_prompt | llm | JsonOutputParser()
    return chain.invoke({"input": user_input, "history": history_text})

# 3. THE DRAFTER
def generate_legal_draft(user_input, history_text, doc_type):
    draft_prompt = ChatPromptTemplate.from_template(
        """
        You are a Senior Advocate. Draft a professional **{doc_type}**.
        Use the details from this history:
        {history}
        
        Requirements:
        - Full Legal Format.
        - Use placeholders [_______] for missing info.
        - NO conversational text. Just the document content.
        """
    )
    chain = draft_prompt | llm | StrOutputParser()
    return chain.invoke({"history": history_text, "input": user_input, "doc_type": doc_type})

def convert_law_code(query):
    converter_prompt = ChatPromptTemplate.from_template(
        "Map Old IPC '{query}' to New BNS. Output: Old -> New (Key Changes)."
    )
    chain = converter_prompt | llm | StrOutputParser()
    return chain.invoke({"query": query})

# --- MAIN ROUTER ---
def ask_legal_ai(user_input, chat_history_list):
    # 1. Format History
    history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history_list])
    
    # 2. TRIGGER LOGIC (Expanded Keywords)
    # This fixes the "draft the" issue
    draft_keywords = ["draft", "write", "prepare", "create", "generate"]
    is_draft_request = any(k in user_input.lower() for k in draft_keywords)
    
    # 3. ROUTING
    if is_draft_request:
        analysis = analyze_drafting_needs(user_input, history_text)
        
        if analysis["status"] == "MISSING_INFO":
            questions = "\n".join([f"- {q}" for q in analysis["missing_details"]])
            return {
                "type": "interview",
                "answer": f"**Drafting Protocol: {analysis['document_type']}**\n\nI have the legal context, but I need specific details to fill the document:\n\n{questions}",
                "context": []
            }
        else:
            draft_text = generate_legal_draft(user_input, history_text, analysis["document_type"])
            return {
                "type": "draft",
                "answer": f"**Draft Ready: {analysis['document_type']}**\n\nHere is the legally compliant draft based on our case strategy.",
                "docx": generate_docx(draft_text),
                "pdf": generate_pdf(draft_text),
                "context": []
            }
            
    else:
        # Research Mode (Now passes HISTORY_TEXT)
        response = get_research_response(user_input, history_text)
        return {
            "type": "research",
            "answer": response["answer"],
            "context": response["context"]
        }