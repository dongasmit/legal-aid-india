import streamlit as st
import os
import json
from app_logic import ask_legal_ai, convert_law_code, get_source_image

# --- CONFIGURATION & DATABASE SETUP ---
DB_FILE = "jurisone_data.json"

def load_db():
    """Load users and chats from local JSON file."""
    if not os.path.exists(DB_FILE):
        return {} # Return empty db if file doesn't exist
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    """Save everything to local JSON file."""
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="JurisOne | Legal Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; font-weight: 700; color: #f8fafc;} 
    .sub-header {font-size: 1.1rem; color: #94a3b8; margin-bottom: 2rem;}
    .stChatInput {border-radius: 12px;}
    div[data-testid="stSidebar"] {background-color: #1e293b;}
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTICATION LOGIC ---
if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 JurisOne Secure Login</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        db = load_db()
        
        with tab1:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", use_container_width=True):
                if username in db and db[username]["password"] == password:
                    st.session_state.user = username
                    st.success("Access Granted.")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        
        with tab2:
            new_user = st.text_input("New Username", key="reg_user")
            new_pass = st.text_input("New Password", type="password", key="reg_pass")
            if st.button("Register", use_container_width=True):
                if new_user in db:
                    st.error("User already exists.")
                elif new_user and new_pass:
                    db[new_user] = {
                        "password": new_pass, 
                        "chats": {"New Case #1": []} # Default first chat
                    }
                    save_db(db)
                    st.success("Account created! Please Login.")
                else:
                    st.warning("Please fill all fields.")

# --- MAIN APP LOGIC ---
def main_app():
    user = st.session_state.user
    db = load_db()
    
    # Ensure user has data
    if user not in db:
        st.session_state.user = None
        st.rerun()
        
    user_data = db[user]
    chats = user_data["chats"]
    
    # --- SIDEBAR: WORKSPACE ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/924/924915.png", width=70)
        st.title("JurisOne Workspace")
        st.caption(f"Logged in as: **{user}**")
        
        if st.button("Logout", type="primary", use_container_width=True):
            st.session_state.user = None
            st.rerun()
            
        st.markdown("---")
        st.markdown("### 🗂️ Case Files")

        # 1. New Case Button
        if st.button("➕ Open New Case", use_container_width=True):
            new_id = f"Case File #{len(chats) + 1}"
            chats[new_id] = [] # Create empty list
            db[user]["chats"] = chats
            save_db(db) 
            st.session_state.current_chat_id = new_id
            st.rerun()

        # 2. Case Selector
        if "current_chat_id" not in st.session_state or st.session_state.current_chat_id not in chats:
            st.session_state.current_chat_id = list(chats.keys())[0]
            
        selected_case = st.radio(
            "Select Active Case:", 
            list(chats.keys()), 
            index=list(chats.keys()).index(st.session_state.current_chat_id)
        )
        
        if selected_case != st.session_state.current_chat_id:
            st.session_state.current_chat_id = selected_case
            st.rerun()
            
        st.markdown("---")
        st.subheader("🛠️ Tools")
        ipc_input = st.text_input("IPC -> BNS Converter", placeholder="e.g. 302 IPC")
        if st.button("Convert"):
             res = convert_law_code(ipc_input)
             st.info(res)

    # --- MAIN CHAT AREA ---
    st.markdown('<div class="main-header">JurisOne ⚖️</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">AI Co-Counsel • Working on: <b>{st.session_state.current_chat_id}</b></div>', unsafe_allow_html=True)

    # 1. Load History
    current_chat_id = st.session_state.current_chat_id
    history = chats[current_chat_id]

    # 2. Display Chat
    for message in history:
        avatar = "🧑‍⚖️" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # 3. Handle Input
    if prompt := st.chat_input("Draft a petition, research case law..."):
        
        # A. Show User Msg
        with st.chat_message("user", avatar="🧑‍⚖️"):
            st.markdown(prompt)
        
        # B. Save User Msg
        history.append({"role": "user", "content": prompt})
        db[user]["chats"][current_chat_id] = history
        save_db(db) 
        
        # C. Generate AI Response
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            with st.spinner("⚖️ Consulting database..."):
                try:
                    response_data = ask_legal_ai(prompt, history)
                    final_answer = response_data["answer"]
                    
                    message_placeholder.markdown(final_answer)
                    
                    # D. Save AI Msg
                    history.append({"role": "assistant", "content": final_answer})
                    db[user]["chats"][current_chat_id] = history
                    save_db(db)
                    
                    # E. SHOW EXTRAS (RESTORED IMAGES!)
                    if response_data.get("type") == "draft":
                        st.success("Draft Generated.")
                        st.download_button("📄 Download DOCX", response_data["docx"], "draft.docx")
                        st.download_button("📑 Download PDF", response_data["pdf"], "draft.pdf")
                    
                    # --- FIXED VERIFICATION DECK ---
                    elif response_data.get("type") == "research" and response_data.get("context"):
                         st.markdown("---")
                         st.subheader("🔍 Verification Deck")
                         
                         # Create tabs for clean UI
                         tabs = st.tabs([f"Source {i+1}" for i in range(len(response_data["context"]))])
                         
                         for i, (tab, doc) in enumerate(zip(tabs, response_data["context"])):
                             with tab:
                                 # Get Metadata
                                 source_path = doc.metadata.get("source", "")
                                 page_num = doc.metadata.get("page", 0)
                                 source_name = os.path.basename(source_path)
                                 
                                 col1, col2 = st.columns([1, 1.5])
                                 
                                 # Left: Text Snippet
                                 with col1:
                                     st.info(f"**Document:** {source_name}\n\n**Page:** {page_num + 1}")
                                     st.caption(f"**Excerpt:** \"{doc.page_content[:300]}...\"")
                                 
                                 # Right: The Actual Image
                                 with col2:
                                     # Call the image generator from app_logic
                                     img = get_source_image(source_path, page_num)
                                     if img:
                                         st.image(img, caption=f"Original Scan: Page {page_num + 1}", use_container_width=True)
                                     else:
                                         st.warning("⚠️ Original scan unavailable (File not found locally).")

                except Exception as e:
                    message_placeholder.error(f"Error: {e}")

# --- APP ENTRY POINT ---
if st.session_state.user:
    main_app()
else:
    login_page()