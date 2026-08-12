from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import datetime

# Import the existing AI logic
from app_logic import ask_legal_ai

app = FastAPI(title="JurisOne API")

# Configure CORS for Next.js development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "chat_data.json"

# --- HELPER FUNCTIONS (Migrated from app.py) ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- PYDANTIC MODELS ---
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    username: str
    chat_id: str
    message: str

# --- API ENDPOINTS ---

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/chats/{username}")
def get_user_chats(username: str):
    data = load_data()
    if username not in data:
        # Auto-create user for development ease
        data[username] = {"password": "password", "chats": {}}
        save_data(data)
    
    user_chats = data[username].get("chats", {})
    return {"chats": user_chats}

@app.post("/api/chats/{username}/new")
def create_new_chat(username: str):
    data = load_data()
    if username not in data:
        data[username] = {"password": "password", "chats": {}}
    
    new_chat_id = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data[username]["chats"][new_chat_id] = []
    save_data(data)
    
    return {"chat_id": new_chat_id}

@app.post("/api/chat")
def process_chat(request: ChatRequest):
    data = load_data()
    
    # Auto-create user and chat if they don't exist for development
    if request.username not in data:
        data[request.username] = {"password": "password", "chats": {}}
    if request.chat_id not in data[request.username]["chats"]:
        data[request.username]["chats"][request.chat_id] = []
        save_data(data)
        
    chat_history = data[request.username]["chats"][request.chat_id]
    
    # Append user message
    user_msg = {"role": "user", "content": request.message}
    chat_history.append(user_msg)
    
    try:
        # Call the existing Langchain logic
        # Note: We pass the history BEFORE generating the AI response
        ai_response_data = ask_legal_ai(request.message, chat_history)
        
        # Append AI message
        ai_msg = {"role": "assistant", "content": ai_response_data["answer"]}
        chat_history.append(ai_msg)
        
        # Save back to JSON
        data[request.username]["chats"][request.chat_id] = chat_history
        save_data(data)
        
        return ai_response_data
        
    except Exception as e:
        print(f"Error processing AI request: {e}")
        # Save the user message even if AI fails
        data[request.username]["chats"][request.chat_id] = chat_history
        save_data(data)
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import Response
import io
from app_logic import get_source_image

@app.get("/api/document/image")
def get_document_image(source: str, page: int):
    # Qdrant stores just the PDF basename (e.g., "Constitution.pdf").
    # Resolve it to source_docs/ relative path.
    source_path = source
    if not os.path.exists(source_path):
        # Try resolving inside source_docs/
        candidate = os.path.join("source_docs", source)
        if os.path.exists(candidate):
            source_path = candidate
    
    img = get_source_image(source_path, page)
    if not img:
        raise HTTPException(status_code=404, detail="Image could not be generated or found.")
        
    # Convert PIL Image to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    
    return Response(content=img_byte_arr, media_type="image/jpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
