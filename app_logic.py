import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel

# 1. Load Keys
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_PATH = "vector_db"

if not GROQ_API_KEY:
    raise ValueError("❌ API Key missing! Check .env file.")

def get_rag_chain():
    # --- A. Setup ---
    print("🧠 Loading Vector Database...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})

    llm = ChatGroq(
        temperature=0, 
        model_name="llama-3.3-70b-versatile", 
        api_key=GROQ_API_KEY
    )

    # --- B. The "Translator" (Fixes Slang Permanently) ---
    # This step converts "Hit and Run" -> "Section 106 BNS negligence"
    query_transform_prompt = ChatPromptTemplate.from_template(
        """
        You are a legal search optimizer. Convert the user's question into precise Indian Legal keywords.
        
        Rules:
        1. Identify the core crime (e.g., "Hit and run" -> "Death by negligence", "Failure to report accident").
        2. Map to relevant Acts (e.g., "Motor Vehicles Act", "BNS", "IT Act").
        3. Output ONLY the search keywords.
        
        Example 1:
        User: "Hit and run punishment"
        Keywords: "Section 106(2) Bharatiya Nyaya Sanhita causing death by negligence Section 134 Motor Vehicles Act"
        
        Example 2:
        User: "Land grabbing by relative"
        Keywords: "Criminal Trespass Section 329 BNS Transfer of Property Act illegal possession"

        User Question: {question}
        Keywords:
        """
    )
    
    # Create the transformation chain
    query_transform_chain = query_transform_prompt | llm | StrOutputParser()

    # --- C. The "Answerer" (The Lawyer) ---
    answer_prompt = ChatPromptTemplate.from_template(
        """
        You are an expert Indian Legal Assistant.
        Answer the question based ONLY on the following context:
        {context}

        Question: {question}
        
        Instructions:
        - Cite the specific Act and Section number if available.
        - Explain the punishment clearly.
        - If the exact section isn't found, explain the general legal principle found in the text.
        """
    )

    # --- D. The Full Pipeline ---
    # 1. We translate the query first
    # 2. We use the translated query to fetch docs (context)
    # 3. We pass the docs + original question to the LLM to answer
    rag_chain = (
        RunnableParallel({
            "context": query_transform_chain | retriever, 
            "question": RunnablePassthrough()
        })
        .assign(answer= answer_prompt | llm | StrOutputParser())
    )

    return rag_chain

# --- DRAFTING MODULE (Unchanged) ---
def draft_legal_document(doc_type, details):
    llm = ChatGroq(temperature=0.3, model_name="llama-3.3-70b-versatile", api_key=GROQ_API_KEY)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an Indian Senior Advocate. Draft a formal document."),
        ("human", "Draft: {doc_type}\nDetails:\n{details}")
    ])
    return (prompt | llm).invoke({"doc_type": doc_type, "details": details}).content