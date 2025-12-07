import os
import pandas as pd
import psycopg2
from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from dotenv import load_dotenv
import PyPDF2

load_dotenv()

# Configuration
DATA_DIR = "data"
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.csv")
CONTRACTS_DIR = os.path.join(DATA_DIR, "contracts")

def ingest_suppliers():
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            port=os.getenv("POSTGRES_PORT")
        )
        cur = conn.cursor()
        
        df = pd.read_csv(SUPPLIERS_FILE)
        
        # Check if data already exists to avoid duplicates
        cur.execute("SELECT COUNT(*) FROM suppliers")
        count = cur.fetchone()[0]
        if count > 0:
            print(f"Suppliers table already has {count} rows. Skipping ingestion.")
            return

        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO suppliers (id, name, country, category, risk_tolerance_score)
                VALUES (%s, %s, %s, %s, %s)
            """, (row['id'], row['name'], row['country'], row['category'], row['risk_tolerance_score']))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"Successfully ingested {len(df)} suppliers into PostgreSQL.")
        
    except Exception as e:
        print(f"Error ingesting suppliers: {e}")

def ingest_contracts():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or "your_google_api_key" in api_key:
        print("Skipping Contract Ingestion: GOOGLE_API_KEY not found or invalid.")
        return

    try:
        # Initialize Qdrant Client
        client = QdrantClient(url=os.getenv("QDRANT_URL"))
        collection_name = "supplier_contracts"
        
        # Create collection if not exists
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            print(f"Created Qdrant collection: {collection_name}")

        # Initialize Embeddings
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )

        documents = []
        pdf_files = [f for f in os.listdir(CONTRACTS_DIR) if f.endswith('.pdf')]
        
        for pdf_file in pdf_files:
            file_path = os.path.join(CONTRACTS_DIR, pdf_file)
            supplier_id = pdf_file.split('_')[1].split('.')[0]
            
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            
            doc = Document(
                page_content=text,
                metadata={"supplier_id": int(supplier_id), "source": pdf_file}
            )
            documents.append(doc)

        if documents:
            vector_store.add_documents(documents)
            print(f"Successfully ingested {len(documents)} contracts into Qdrant.")
        else:
            print("No contract documents found to ingest.")

    except Exception as e:
        print(f"Error ingesting contracts: {e}")

if __name__ == "__main__":
    print("Starting Data Ingestion...")
    ingest_suppliers()
    ingest_contracts()
    print("Data Ingestion Complete.")
