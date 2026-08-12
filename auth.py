import os
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Strict check to stop the script if the URL is missing
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is missing! Check your .env file and make sure it is saved.")

def get_db_connection():
    """Connects to the PostgreSQL cloud database."""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def init_db():
    """Creates the users table if it doesn't exist yet."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()
            print("✅ Database tables initialized successfully in the cloud!")
        except Exception as e:
            print(f"❌ Failed to create tables: {e}")
        finally:
            conn.close()
    else:
        print("❌ Could not connect to the database to create tables.")

def create_user(username, plain_text_password):
    """Hashes the password and saves the new user to PostgreSQL."""
    salt = bcrypt.gensalt()
    hashed_pw = bcrypt.hashpw(plain_text_password.encode('utf-8'), salt).decode('utf-8')
    
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, hashed_pw)
                )
            conn.commit()
            return True, "Account created successfully!"
        except psycopg2.IntegrityError:
            return False, "Username already exists."
        finally:
            conn.close()
    return False, "Database error."

def verify_user(username, plain_text_password):
    """Checks if the username exists and the password matches the hash."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
                user = cur.fetchone()
            
            if user:
                saved_hash = user['password_hash'].encode('utf-8')
                if bcrypt.checkpw(plain_text_password.encode('utf-8'), saved_hash):
                    return True, "Login successful!"
                else:
                    return False, "Incorrect password."
        finally:
            conn.close()
                
    return False, "Username not found."

if __name__ == "__main__":
    print("🚀 Attempting to connect to Neon Cloud Database...")
    init_db()