from sqlalchemy import create_engine, text
import os

FORENSIC_URL = os.getenv("FORENSIC_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db")
engine = create_engine(FORENSIC_URL)

def migrate():
    with engine.connect() as conn:
        print("[*] Inceput migrare financial_items...")
        # 1. Stergem tabelul vechi (datele vor fi regenerate la reprocesare)
        conn.execute(text("DROP TABLE IF EXISTS financial_items CASCADE"))
        
        # 2. Cream tabelul nou conform specificatiilor Phase 3
        conn.execute(text("""
            CREATE TABLE financial_items (
                id VARCHAR PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id),
                doc_number VARCHAR,
                doc_filename VARCHAR,
                transaction_date VARCHAR,
                description TEXT,
                amount FLOAT,
                currency VARCHAR DEFAULT 'RON',
                doc_type VARCHAR,
                transaction_type VARCHAR,
                cui_source VARCHAR,
                iban_source VARCHAR,
                cui_destination VARCHAR,
                iban_destination VARCHAR
            )
        """))
        
        # 3. Indexuri pentru viteza
        conn.execute(text("CREATE INDEX idx_fi_doc_id ON financial_items(document_id)"))
        conn.execute(text("CREATE INDEX idx_fi_cui_s ON financial_items(cui_source)"))
        conn.execute(text("CREATE INDEX idx_fi_iban_s ON financial_items(iban_source)"))
        conn.execute(text("CREATE INDEX idx_fi_cui_d ON financial_items(cui_destination)"))
        conn.execute(text("CREATE INDEX idx_fi_iban_d ON financial_items(iban_destination)"))
        
        conn.commit()
        print("[+] Migrare finalizata cu succes.")

if __name__ == "__main__":
    migrate()
