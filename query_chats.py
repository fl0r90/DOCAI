from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import json

FORENSIC_URL = os.getenv("FORENSIC_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db")
engine = create_engine(FORENSIC_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def query_recent_chats():
    db = SessionLocal()
    try:
        # Get last 5 messages
        from sqlalchemy import text
        result = db.execute(text("SELECT id, role, content, sql, created_at FROM chat_messages ORDER BY created_at DESC LIMIT 5"))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row[0]} | Role: {row[1]} | Time: {row[4]}")
            print(f"Content: {row[2]}")
            if row[3]:
                print(f"SQL: {row[3]}")
            print("-" * 20)
    finally:
        db.close()

if __name__ == "__main__":
    query_recent_chats()
