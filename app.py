import streamlit as st
import json
import os
import datetime

# --- CONFIGURATION ---
DATA_FILE = "chat_data.json"

# --- DATABASE FUNCTIONS (Load/Save to JSON) ---
def load_data():
    """Load all users and chats from the local JSON file."""
    if not os.path.exists(DATA_FILE):
        return {}  # Return empty dict if file doesn't exist
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    """Save the current data to the local JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- AUTHENTICATION FUNCTIONS ---
def login_user(username, password):
    data = load_data()
    if username in data and data[username]["password"] == password:
        return True
    return False

def register_user(username, password):
    data = load_data()
    if username in data:
        return False  # User already exists
    data[username] = {"password": password, "chats": {}}
    save_data(data)
    return True

# --- UI SECTIONS ---
def login_page():
    st.title("🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if login_user(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def register_page():
    st.title("📝 Register")
    with st.form("register_form"):
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        submit = st.form_submit_button("Create Account")

        if submit:
            if register_user(new_user, new_pass):
                st.success("Account created! Please log in.")
            else:
                st.error("Username already exists.")

# --- MAIN APP LOGIC ---
def main_app():
    st.sidebar.title(f"👤 {st.session_state['username']}")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.rerun()

    # Load user data
    data = load_data()
    user_data = data[st.session_state["username"]]
    chats = user_data.get("chats", {})

    # Sidebar: Chat Selection
    st.sidebar.header("🗂️ Your Chats")
    
    # "New Chat" button
    if st.sidebar.button("➕ New Chat"):
        new_chat_id = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chats[new_chat_id] = []  # Initialize empty chat
        data[st.session_state["username"]]["chats"] = chats
        save_data(data)
        st.session_state["current_chat"] = new_chat_id
        st.rerun()

    # List existing chats
    chat_ids = list(chats.keys())
    if not chat_ids:
        st.info("No chats yet. Click 'New Chat' to start.")
        current_chat = None
    else:
        # Default to most recent if none selected
        if "current_chat" not in st.session_state or st.session_state["current_chat"] not in chat_ids:
            st.session_state["current_chat"] = chat_ids[-1]
        
        current_chat = st.sidebar.radio("Select a Session:", chat_ids, index=chat_ids.index(st.session_state["current_chat"]))
        st.session_state["current_chat"] = current_chat

    # Chat Interface
    if current_chat:
        st.header(f"Chat: {current_chat}")
        
        # Display history
        messages = chats[current_chat]
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input new message
        if prompt := st.chat_input("Type a message..."):
            # Add user message
            new_msg = {"role": "user", "content": prompt}
            messages.append(new_msg)
            
            # --- SIMULATE BOT RESPONSE (Replace with your AI logic) ---
            bot_reply = f"Echo: {prompt}" 
            messages.append({"role": "assistant", "content": bot_reply})
            # ---------------------------------------------------------

            # Save to JSON immediately
            data[st.session_state["username"]]["chats"][current_chat] = messages
            save_data(data)
            
            st.rerun()

# --- APP ENTRY POINT ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    menu = st.sidebar.selectbox("Menu", ["Login", "Register"])
    if menu == "Login":
        login_page()
    else:
        register_page()
else:
    main_app()