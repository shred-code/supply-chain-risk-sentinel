import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
print(f"User: {os.getenv('POSTGRES_USER')}")
print(f"DB: {os.getenv('POSTGRES_DB')}")

def create_tables():
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            port=os.getenv("POSTGRES_PORT")
        )
        cur = conn.cursor()

        # Create Suppliers Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                country VARCHAR(50),
                category VARCHAR(50),
                risk_tolerance_score INT
            );
        """)

        # Create Shipments Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id SERIAL PRIMARY KEY,
                supplier_id INT,
                value_usd DECIMAL,
                status VARCHAR(20),
                due_date DATE,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Database schema initialized successfully.")

    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    create_tables()
