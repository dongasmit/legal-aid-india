import streamlit as st
from app_logic import ask_legal_ai, convert_law_code, get_source_image, _init_error
from auth import create_user, verify_user

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="JurisOne | Legal AI", page_icon="⚖️", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if "user" not in st.session_state:
    st.session_state.user = None

# Surface any AI initialisation errors early so users see a clear message.
if _init_error:
    st.error(_init_error)
    st.stop()

# Initialize the Multi-Thread Case System
if "cases" not in st.session_state:
    st.session_state.cases = {"New Case #1": []}
if "active_case" not in st.session_state:
    st.session_state.active_case = "New Case #1"

# --- AUTHENTICATION LOGIC ---
def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>🔐 JurisOne Secure Login</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Enterprise-Grade Legal Intelligence</p><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        with tab1:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", use_container_width=True):
                if username and password:
                    success, message = verify_user(username, password)
                    if success:
                        st.session_state.user = username
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill all fields.")
        
        with tab2:
            new_user = st.text_input("New Username", key="reg_user")
            new_pass = st.text_input("New Password", type="password", key="reg_pass")
            if st.button("Register", use_container_width=True):
                if new_user and new_pass:
                    success, message = create_user(new_user, new_pass)
                    if success:
                        st.success(f"{message} Please Login.")
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill all fields.")

# --- MAIN APP ROUTER ---
if st.session_state.user is None:
    login_page()
else:
    # --- SIDEBAR (Logged In State) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/6024/6024190.png", width=60)
        st.title("JurisOne Workspace")
        st.write(f"Logged in as: **{st.session_state.user}**")
        
        if st.button("Logout", type="primary", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        st.divider()
        
        # --- CASE FILES (MULTI-CHAT SYSTEM) ---
        st.markdown("### 📁 Case Files")
        if st.button("➕ Open New Case", use_container_width=True):
            new_case_name = f"New Case #{len(st.session_state.cases) + 1}"
            st.session_state.cases[new_case_name] = []
            st.session_state.active_case = new_case_name
            st.rerun()

        # Switch between cases
        selected_case = st.radio(
            "Select Active Case:", 
            list(st.session_state.cases.keys()), 
            index=list(st.session_state.cases.keys()).index(st.session_state.active_case)
        )
        
        if selected_case != st.session_state.active_case:
            st.session_state.active_case = selected_case
            st.rerun()

        st.divider()
        
        # --- TOOLS ---
        st.markdown("### 🛠 Tools")
        st.markdown("**IPC → BNS Converter**")
        ipc_code = st.text_input("e.g., 302 IPC", key="ipc_input")
        if st.button("Convert", use_container_width=True):
            if ipc_code:
                with st.spinner("Converting..."):
                    conversion = convert_law_code(ipc_code)
                    st.info(conversion)

    # --- MAIN CHAT INTERFACE ---
    st.title(f"⚖️ {st.session_state.active_case}")
    
    # Load the messages for the currently active case
    current_chat = st.session_state.cases[st.session_state.active_case]
    
    # Display historical chat messages
    for idx, message in enumerate(current_chat):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Re-render Verification Deck from history
            if message.get("context"):
                with st.expander("🔍 Verification Deck"):
                    tabs = st.tabs([f"Source {i+1}" for i in range(len(message["context"]))])
                    for i, doc in enumerate(message["context"]):
                        with tabs[i]:
                            source_path = doc.metadata.get('source', 'Unknown')
                            page_num = doc.metadata.get('page', 0)
                            
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                st.info(f"**Document:**\n{source_path}\n\n**Page:** {page_num + 1}")
                            with col2:
                                img = get_source_image(source_path, page_num)
                                if img:
                                    st.image(img, caption=f"Original Scan: Page {page_num + 1}", use_container_width=True)
                                else:
                                    st.markdown("##### 📄 Official Case Excerpt")
                                    st.success(doc.page_content)
            
            # Re-render download buttons from history
            if message.get("docx"):
                st.download_button("📄 Download DOCX", data=message["docx"], file_name="jurisone_draft.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"dl_docx_{idx}")
            if message.get("pdf"):
                st.download_button("📑 Download PDF", data=message["pdf"], file_name="jurisone_draft.pdf", mime="application/pdf", key=f"dl_pdf_{idx}")

    # --- CHAT INPUT & PROCESSING ---
    if prompt := st.chat_input("Draft a petition, research case law..."):
        
        # 1. Show user message
        st.session_state.cases[st.session_state.active_case].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # 2. Process and show assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing Indian Law..."):
                response_data = ask_legal_ai(prompt, st.session_state.cases[st.session_state.active_case])
                
                # Show main answer
                st.markdown(response_data["answer"])
                
                # Prepare message dictionary to save
                message_to_save = {
                    "role": "assistant", 
                    "content": response_data["answer"],
                    "context": response_data.get("context", []),
                    "docx": response_data.get("docx", None),
                    "pdf": response_data.get("pdf", None)
                }
                
                # Render Verification Deck live
                if message_to_save["context"]:
                    with st.expander("🔍 Verification Deck", expanded=True):
                        tabs = st.tabs([f"Source {i+1}" for i in range(len(message_to_save["context"]))])
                        for i, doc in enumerate(message_to_save["context"]):
                            with tabs[i]:
                                source_path = doc.metadata.get('source', 'Unknown')
                                page_num = doc.metadata.get('page', 0)
                                
                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    st.info(f"**Document:**\n{source_path}\n\n**Page:** {page_num + 1}")
                                with col2:
                                    img = get_source_image(source_path, page_num)
                                    if img:
                                        st.image(img, caption=f"Original Scan: Page {page_num + 1}", use_container_width=True)
                                    else:
                                        st.markdown("##### 📄 Official Case Excerpt")
                                        st.success(doc.page_content)
                
                # Render Download Buttons live
                if message_to_save["docx"]:
                    st.download_button("📄 Download DOCX", data=message_to_save["docx"], file_name="jurisone_draft.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_docx_new")
                if message_to_save["pdf"]:
                    st.download_button("📑 Download PDF", data=message_to_save["pdf"], file_name="jurisone_draft.pdf", mime="application/pdf", key="dl_pdf_new")
                    
                # Save to active case session state
                st.session_state.cases[st.session_state.active_case].append(message_to_save)