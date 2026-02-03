import streamlit as st
import os
from app_logic import ask_legal_ai, convert_law_code, get_source_image

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="JurisOne | Legal Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (Professional Polish) ---
st.markdown("""
    <style>
    /* 1. Fix Title Color (White for Dark Mode) */
    .main-header {font-size: 2.5rem; font-weight: 700; color: #f8fafc;} 
    .sub-header {font-size: 1.1rem; color: #94a3b8; margin-bottom: 2rem;}
    
    /* 2. Chat Input Styling */
    .stChatInput {border-radius: 12px;}
    
    /* 3. Sidebar Background */
    div[data-testid="stSidebar"] {background-color: #1e293b;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE SETUP (The Memory Fix) ---
# This allows us to have multiple "Files" or "Chats" side-by-side
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {"Case File #1": []}  # Default start
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "Case File #1"

# --- SIDEBAR: WORKSPACE ---
with st.sidebar:
    # 4. FIXED LOGO: Scales of Justice (No more Bathtub!)
    st.image("https://cdn-icons-png.flaticon.com/512/924/924915.png", width=70)
    st.title("JurisOne Workspace")
    
    # 1. CASE MANAGEMENT (New Feature)
    st.markdown("### 🗂️ Active Cases")
    
    # Button to start a fresh brain for a new client
    if st.button("➕ Open New Case File", use_container_width=True):
        new_case_name = f"Case File #{len(st.session_state.all_chats) + 1}"
        st.session_state.all_chats[new_case_name] = []
        st.session_state.current_chat_id = new_case_name
        st.rerun()

    # Dropdown to switch between clients/cases
    case_list = list(st.session_state.all_chats.keys())
    selected_case = st.radio(
        "Select Case:", 
        case_list, 
        index=case_list.index(st.session_state.current_chat_id)
    )
    
    # If user switches case, update the view
    if selected_case != st.session_state.current_chat_id:
        st.session_state.current_chat_id = selected_case
        st.rerun()

    st.markdown("---")
    
    # 2. MINI TOOLS (The IPC Converter)
    st.subheader("🛠️ Quick Tools")
    st.caption("Legacy Law Converter (IPC -> BNS)")
    ipc_input = st.text_input("Enter Section (e.g., '420 IPC')", key="ipc_tool")
    if st.button("Convert", type="secondary"):
        with st.spinner("Mapping..."):
            try:
                res = convert_law_code(ipc_input)
                st.info(res)
            except Exception as e:
                st.error("Could not find mapping.")

# --- MAIN PAGE LAYOUT ---
st.markdown('<div class="main-header">JurisOne ⚖️</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">AI Co-Counsel • Working on: <b>{st.session_state.current_chat_id}</b></div>', unsafe_allow_html=True)

# --- CHAT INTERFACE ---

# 1. Load History for the SELECTED Case
current_case_id = st.session_state.current_chat_id
chat_history = st.session_state.all_chats[current_case_id]

# 2. Display Messages
for message in chat_history:
    # Use professional avatars: 🧑‍⚖️ for Lawyer, 🤖 for AI
    role_avatar = "🧑‍⚖️" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=role_avatar):
        st.markdown(message["content"])

# 3. Handle New Input
if prompt := st.chat_input("Draft a petition, research case law, or ask for strategy..."):
    
    # A. Display User Message
    with st.chat_message("user", avatar="🧑‍⚖️"):
        st.markdown(prompt)
    
    # B. Save to History
    st.session_state.all_chats[current_case_id].append({"role": "user", "content": prompt})
    
    # C. Generate AI Response
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        
        # The "Professor Impresser" Spinner
        with st.spinner("⚖️ Consulting database & analyzing precedents..."):
            try:
                # CALL THE LOGIC with SPECIFIC HISTORY
                response_data = ask_legal_ai(prompt, chat_history) 
                final_answer = response_data["answer"]
                
                # Show Text Answer
                message_placeholder.markdown(final_answer)
                
                # Save Assistant Response to History
                st.session_state.all_chats[current_case_id].append({"role": "assistant", "content": final_answer})
                
                # --- DYNAMIC UI ELEMENTS ---
                
                # TYPE 1: RESEARCH (Show Images)
                if response_data["type"] == "research" and response_data.get("context"):
                    st.markdown("---")
                    st.subheader("🔍 Verification Deck")
                    st.caption("Evidence sourced from official records:")
                    
                    tabs = st.tabs([f"Source {i+1}" for i in range(len(response_data["context"]))])
                    
                    for i, (tab, doc) in enumerate(zip(tabs, response_data["context"])):
                        with tab:
                            # Metadata
                            source_name = os.path.basename(doc.metadata.get("source", "Unknown Document"))
                            page_num = doc.metadata.get("page", 0)
                            
                            col1, col2 = st.columns([1, 2])
                            with col1:
                                st.info(f"**Doc:** {source_name}\n\n**Page:** {page_num}")
                                st.markdown(f"*{doc.page_content[:200]}...*")
                            
                            with col2:
                                # Render Image
                                img = get_source_image(doc.metadata.get("source"), page_num)
                                if img:
                                    st.image(img, caption=f"Original Page {page_num}", use_container_width=True)
                                else:
                                    st.warning("⚠️ Original scan unavailable locally.")

                # TYPE 2: DRAFT (Show Downloads)
                elif response_data["type"] == "draft":
                    st.markdown("---")
                    st.success("✅ Draft Generated Successfully.")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button("📄 Download Word Doc", response_data["docx"], "Legal_Draft.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    with col2:
                        st.download_button("📑 Download PDF", response_data["pdf"], "Legal_Draft.pdf", "application/pdf")

            except Exception as e:
                message_placeholder.error(f"System Error: {e}")