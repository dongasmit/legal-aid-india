import streamlit as st
from app_logic import get_rag_chain, draft_legal_document

# --- Page Config ---
st.set_page_config(page_title="Indian Legal Aid AI", page_icon="⚖️", layout="wide")

st.title("⚖️ Indian Legal Aid AI")
st.caption("Powered by Llama 3 & Bharatiya Nyaya Sanhita (BNS)")

# --- Tabs for different features ---
tab1, tab2 = st.tabs(["🔍 Research Assistant", "📝 Legal Drafter"])

# ==========================================
# TAB 1: RESEARCH (The Chatbot)
# ==========================================
with tab1:
    st.header("Ask Legal Questions")
    st.markdown("Ask about crimes, punishments, or procedures (e.g., 'Hit and Run', 'Cheating').")
    
    # Load the brain (Cached)
    @st.cache_resource
    def load_rag():
        return get_rag_chain()
    
    try:
        rag_chain = load_rag()
    except Exception as e:
        st.error(f"Error loading AI: {e}")
        st.stop()

    # Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display previous history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("Ask a legal question..."):
        # 1. Show User Message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2. Generate AI Response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("⏳ Consulting the law...")
            
            try:
                # The 'input' key is no longer strictly needed with RunnablePassthrough, 
                # but we pass the prompt directly.
                response = rag_chain.invoke(prompt)
                
                # EXTRACT THE ANSWER
                # The new chain returns a dict: {'question': ..., 'context': ..., 'answer': ...}
                final_answer = response['answer']
                
                message_placeholder.markdown(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                
                # 3. DEBUG TAB: Show what the AI read
                # This proves if your "Translation Layer" worked!
                with st.expander("🕵️‍♂️ View Retrieved Legal Sections (Debug Info)"):
                    context_docs = response['context']
                    if not context_docs:
                        st.warning("No relevant legal documents found. Try adding more PDFs to 'source_docs'.")
                    else:
                        for i, doc in enumerate(context_docs):
                            st.markdown(f"**Source {i+1} (Page {doc.metadata.get('page', '?')}):**")
                            st.caption(doc.page_content[:500] + "...") # Show first 500 chars
                            st.markdown("---")
                        
            except Exception as e:
                message_placeholder.error(f"Error: {e}")

# ==========================================
# TAB 2: DRAFTER (The Document Generator)
# ==========================================
with tab2:
    st.header("Draft Legal Documents")
    st.markdown("Generate professional legal drafts tailored for Indian context.")

    col1, col2 = st.columns(2)
    
    with col1:
        # Input Form
        doc_type = st.selectbox(
            "What do you want to draft?",
            ["Legal Notice", "Rent Agreement", "Affidavit", "Employment Contract", "Power of Attorney", "Divorce Petition (Mutual)", "Custom Request"]
        )
        
        user_details = st.text_area(
            "Enter Details (Names, Dates, Amounts, Terms):",
            height=300,
            placeholder="E.g., \nLandlord: Smit Donga\nTenant: raj Kumar\nRent: 15,000 INR\nProperty: Flat 202, Anand, Gujarat..."
        )
        
        generate_btn = st.button("✨ Draft Document", type="primary")

    with col2:
        # Output Area
        if generate_btn and user_details:
            with st.spinner("Drafting your document..."):
                try:
                    # Call the drafting function from app_logic
                    draft_text = draft_legal_document(doc_type, user_details)
                    
                    st.subheader("Final Draft")
                    st.text_area("Copy your draft below:", value=draft_text, height=600)
                    st.download_button("Download .txt", draft_text, file_name=f"{doc_type}_Draft.txt")
                    
                except Exception as e:
                    st.error(f"Error: {e}")