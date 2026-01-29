import streamlit as st
from app_logic import ask_legal_ai

# --- Page Config ---
st.set_page_config(page_title="Indian Legal Aid AI", page_icon="⚖️", layout="wide")
st.title("⚖️ Indian Legal Aid AI (Law Firm Edition)")
st.caption("Powered by Llama 3 & Bharatiya Nyaya Sanhita (BNS)")

# --- Chat History Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- User Input & Logic ---
if prompt := st.chat_input("Ask a legal question or request a draft..."):
    
    # 1. Display User Message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Get AI Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ Analyzing legal strategy...")
        
        try:
            response_data = ask_legal_ai(prompt, st.session_state.messages[:-1]) 
            final_answer = response_data["answer"]
            
            # Show the answer
            message_placeholder.markdown(final_answer)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
            
            # --- RESEARCH MODE: Show Sources ---
            if response_data["type"] == "research" and response_data["context"]:
                with st.expander("📚 Referenced Legal Authorities"):
                    for i, doc in enumerate(response_data["context"]):
                        st.markdown(f"**Source {i+1}:**")
                        st.caption(doc.page_content[:300] + "...")
            
            # --- DRAFT MODE: Show Download Buttons ---
            if response_data["type"] == "draft":
                st.markdown("---")
                st.subheader("💾 Download Options")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="📄 Download as Word (.docx)",
                        data=response_data["docx"],
                        file_name="Legal_Draft.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                with col2:
                    st.download_button(
                        label="📑 Download as PDF",
                        data=response_data["pdf"],
                        file_name="Legal_Draft.pdf",
                        mime="application/pdf"
                    )

        except Exception as e:
            message_placeholder.error(f"Error: {e}")