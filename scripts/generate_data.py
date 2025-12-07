import os
import pandas as pd
import random
from faker import Faker
from fpdf import FPDF

fake = Faker()

# Configuration
NUM_SUPPLIERS = 20
COUNTRIES = ['Taiwan', 'Japan', 'Ukraine', 'USA']
CATEGORIES = ['Electronics', 'Raw Materials', 'Logistics']
DATA_DIR = "data"
CONTRACTS_DIR = os.path.join(DATA_DIR, "contracts")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONTRACTS_DIR, exist_ok=True)

def generate_suppliers():
    suppliers = []
    for i in range(1, NUM_SUPPLIERS + 1):
        country = random.choice(COUNTRIES)
        suppliers.append({
            "id": i,
            "name": fake.company(),
            "country": country,
            "category": random.choice(CATEGORIES),
            "risk_tolerance_score": random.randint(1, 10)
        })
    
    df = pd.DataFrame(suppliers)
    df.to_csv(os.path.join(DATA_DIR, "suppliers.csv"), index=False)
    print(f"Generated {NUM_SUPPLIERS} suppliers in {DATA_DIR}/suppliers.csv")
    return suppliers

def generate_contracts(suppliers):
    for supplier in suppliers:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        text = f"Contract for {supplier['name']}\n\n"
        text += f"Country: {supplier['country']}\n"
        text += f"Date: {fake.date_this_year()}\n\n"
        text += "Terms and Conditions:\n"
        
        # Add some risk-related clauses
        if supplier['country'] == 'Japan':
            text += "If the JPY/USD exchange rate drops below 140, Supplier can renegotiate pricing.\n"
        elif supplier['country'] == 'Taiwan':
            text += "Force Majeure applies for typhoons and earthquakes.\n"
        elif supplier['country'] == 'Ukraine':
            text += "Shipping routes subject to change based on conflict zones.\n"
        else:
            text += "Standard delivery terms apply.\n"
            
        text += "\nThis contract is valid for 12 months."
        
        pdf.multi_cell(0, 10, text)
        pdf.output(os.path.join(CONTRACTS_DIR, f"contract_{supplier['id']}.pdf"))
    
    print(f"Generated {len(suppliers)} contracts in {CONTRACTS_DIR}/")

if __name__ == "__main__":
    suppliers = generate_suppliers()
    generate_contracts(suppliers)
