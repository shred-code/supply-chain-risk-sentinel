import os
import requests
import psycopg2
from typing import List, Dict, Any
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

@tool
def sql_tool(query: str) -> str:
    """
    Executes a read-only SQL query on the PostgreSQL database to find suppliers or shipments.
    Useful for finding suppliers by country, category, or checking shipment status.
    The available tables are:
    - suppliers (id, name, country, category, risk_tolerance_score)
    - shipments (id, supplier_id, value_usd, status, due_date)
    """
    try:
        # Basic safety check to prevent modification
        if not query.strip().lower().startswith("select"):
            return "Error: Only SELECT queries are allowed."

        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            port=os.getenv("POSTGRES_PORT")
        )
        cur = conn.cursor()
        cur.execute(query)
        results = cur.fetchall()
        
        # Get column names
        colnames = [desc[0] for desc in cur.description]
        
        cur.close()
        conn.close()
        
        # Format results as a list of dictionaries
        formatted_results = []
        for row in results:
            formatted_results.append(dict(zip(colnames, row)))
            
        return str(formatted_results)
        
    except Exception as e:
        return f"Database Error: {e}"

@tool
def news_tool(query: str) -> str:
    """
    Fetches live news articles from NewsAPI.org based on a search query.
    Useful for finding events like typhoons, strikes, or political unrest in specific countries.
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return "Error: NEWS_API_KEY not found."
        
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={api_key}&language=en&pageSize=5"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("status") != "ok":
            return f"NewsAPI Error: {data.get('message')}"
            
        articles = data.get("articles", [])
        if not articles:
            return "No news found."
            
        results = []
        for article in articles:
            results.append(f"Title: {article['title']}\nSource: {article['source']['name']}\nDescription: {article['description']}\nURL: {article['url']}")
            
        return "\n\n".join(results)
        
    except Exception as e:
        return f"Error fetching news: {e}"

@tool
def fx_tool(base_currency: str = "USD", target_currency: str = "JPY") -> str:
    """
    Fetches the current exchange rate between two currencies.
    Useful for checking financial risks related to currency fluctuations.
    """
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    if not api_key:
        return "Error: EXCHANGE_RATE_API_KEY not found."
        
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("result") != "success":
            return f"FX API Error: {data.get('error-type')}"
            
        rates = data.get("conversion_rates", {})
        rate = rates.get(target_currency)
        
        if rate:
            return f"1 {base_currency} = {rate} {target_currency}"
        else:
            return f"Rate for {target_currency} not found."
            
    except Exception as e:
        return f"Error fetching exchange rate: {e}"
