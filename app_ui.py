import streamlit as st
from app_logic import ask_legal_ai, convert_law_code

# --- Page Config ---
st.set_page_config(page_title="JurisOne", page_icon="⚖️", layout="wide")

# --- CUSTOM CSS (For that "Law Firm" look) ---
st.markdown("""
    <style>
    .main-header {font-size: 3rem; font-weight: 700; color: #1E3A8A;}
    .sub-header {font-size: 1.2rem; color: #64748B;}
    .stChatInput {border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: TOOLS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2237/2237535.png", width=80) # Placeholder Logo
    st.title("JurisOne Tools")
    st.markdown("---")
    
    # TOOL 1: IPC -> BNS CONVERTER
    st.subheader("🔄 Law Converter")
    st.caption("Map Old IPC Sections to New BNS")
    
    ipc_input = st.text_input("Enter IPC Section (e.g., '420 IPC')", key="ipc_query")
    if st.button("Convert to BNS", type="primary"):
        with st.spinner("Mapping laws..."):
            try:
                conversion_result = convert_law_code(ipc_input)
                st.info(conversion_result)
            except Exception as e:
                st.error(f"Error: {e}")
    
    st.markdown("---")
    st.markdown("Developed for Indian Legal Professionals.")

# --- MAIN APP: CHAT INTERFACE ---
st.markdown('<div class="main-header">JurisOne ⚖️</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Powered Case Intelligence & Drafting</div>', unsafe_allow_html=True)
st.markdown("---")

# --- Chat History Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- User Input & Logic ---
if prompt := st.chat_input("Ask a legal question, request a draft, or analyze a case..."):
    
    # 1. Display User Message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Get AI Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ JurisOne is analyzing...")
        
        try:
            response_data = ask_legal_ai(prompt, st.session_state.messages[:-1]) 
            final_answer = response_data["answer"]
            
            # Show the answer
            message_placeholder.markdown(final_answer)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
            
            # --- RESEARCH MODE: Show Sources ---
            if response_data["type"] == "research" and response_data["context"]:
                with st.expander("📚 Referenced Legal Authorities (Click to Verify)"):
                    for i, doc in enumerate(response_data["context"]):
                        st.markdown(f"**Source {i+1}** (Page {doc.metadata.get('page', '?')})")
                        st.caption(doc.page_content[:300] + "...")
                        st.markdown("---")
            
            # --- DRAFT MODE: Show Download Buttons ---
            if response_data["type"] == "draft":
                st.markdown("---")
                st.subheader("💾 Download Draft")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="📄 Word (.docx)",
                        data=response_data["docx"],
                        file_name="JurisOne_Draft.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                with col2:
                    st.download_button(
                        label="📑 PDF",
                        data=response_data["pdf"],
                        file_name="JurisOne_Draft.pdf",
                        mime="application/pdf"
                    )

        except Exception as e:
            message_placeholder.error(f"Error: {e}")