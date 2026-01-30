import os
import io
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from docx import Document
from fpdf import FPDF

# 1. Load Keys
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_PATH = "vector_db"

if not GROQ_API_KEY:
    raise ValueError("❌ API Key missing! Check .env file.")

# --- SHARED RESOURCES ---
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
retriever = vector_db.as_retriever(search_kwargs={"k": 5})

llm = ChatGroq(
    temperature=0.1, 
    model_name="llama-3.3-70b-versatile", 
    api_key=GROQ_API_KEY
)

# --- HELPER: FILE CONVERTERS ---
def generate_docx(text):
    doc = Document()
    doc.add_heading('Legal Draft', 0)
    doc.add_paragraph(text)
    
    # Save to memory buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # FPDF doesn't handle some unicode well, so we encode/decode just in case
    # or replace common problem characters
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, clean_text)
    
    # Output string to buffer
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer

# --- 1. THE RESEARCHER ---
def get_research_response(query):
    query_transform_prompt = ChatPromptTemplate.from_template(
        """
        You are a Legal Research Associate. Transform the Partner's raw query into precise legal search terms.
        Partner's Query: {question}
        Search Keywords:
        """
    )
    query_transform_chain = query_transform_prompt | llm | StrOutputParser()

    answer_prompt = ChatPromptTemplate.from_template(
        """
        You are a Junior Legal Associate at a top-tier Indian Law Firm. 
        Your task is to provide a **Case Strategy Note** based on the provided legal context.

        CONTEXT:
        {context}

        QUERY:
        {question}

        ---
        **DRAFTING GUIDELINES:**
        1. **Structure:** Legal Framework, Procedural Strategy, Evidentiary Standards, Recommended Filings.
        2. **Ending:** Explicitly ask: "Would you like me to draft any of these documents now?"
        ---
        """
    )

    rag_chain = (
        RunnableParallel({
            "context": query_transform_chain | retriever, 
            "question": RunnablePassthrough()
        })
        .assign(answer= answer_prompt | llm | StrOutputParser())
    )
    
    return rag_chain.invoke(query)

# --- 2. THE DRAFTER ---
def draft_from_context(user_instruction, previous_context):
    draft_prompt = ChatPromptTemplate.from_template(
        """
        You are a Senior Indian Advocate. 
        Draft a legal document based on the user's instruction and the previous case context.

        PREVIOUS CONTEXT:
        {history}

        USER INSTRUCTION:
        {instruction}

        OUTPUT FORMAT:
        - Full legal draft with placeholders [Name], [Date].
        - Use standard Indian legal language.
        """
    )
    chain = draft_prompt | llm | StrOutputParser()
    return chain.invoke({"history": previous_context, "instruction": user_instruction})

# --- 3. THE ROUTER ---
def ask_legal_ai(user_input, chat_history):
    draft_keywords = ["draft", "write", "generate", "create", "make"]
    affirmative_keywords = ["yes", "please", "sure", "ok", "go ahead"]
    
    is_draft_request = any(word in user_input.lower() for word in draft_keywords)
    is_confirmation = any(word in user_input.lower() for word in affirmative_keywords)
    
    if (is_draft_request or is_confirmation) and len(chat_history) > 0:
        last_ai_response = chat_history[-1]["content"]
        draft_text = draft_from_context(user_input, last_ai_response)
        
        # Generate files immediately
        return {
            "type": "draft",
            "answer": draft_text,
            "docx": generate_docx(draft_text),
            "pdf": generate_pdf(draft_text),
            "context": []
        }
    
    else:
        response = get_research_response(user_input)
        return {
            "type": "research",
            "answer": response["answer"],
            "context": response["context"]
        }

# --- 4. THE CONVERTER (IPC <-> BNS) ---
def convert_law_code(query):
    converter_prompt = ChatPromptTemplate.from_template(
        """
        You are an expert Legal Comparator specializing in the transition from Indian Penal Code (IPC) to Bharatiya Nyaya Sanhita (BNS).
        
        Task: Map the user's query (Old IPC Section or Concept) to the New BNS Section.
        
        User Query: {query}
        
        Output Format:
        **1. Old Law:** [Section X IPC]
        **2. New Law:** [Section Y BNS]
        **3. Key Changes:** [Briefly explain if the punishment increased, definition expanded, or if it remains identical.]
        
        If the section does not have a direct equivalent, explain why.
        """
    )
    chain = converter_prompt | llm | StrOutputParser()
    return chain.invoke({"query": query})