from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.graph import app as graph_app
from src.state import AgentState
from langchain_core.messages import HumanMessage
import uvicorn

app = FastAPI(title="Supply Chain Risk Sentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RiskRequest(BaseModel):
    query: str

@app.post("/analyze_risk")
async def analyze_risk(request: RiskRequest):
    """
    Triggers the agentic graph to analyze supply chain risks based on the user's query.
    """
    try:
        initial_state = AgentState(
            messages=[HumanMessage(content=request.query)],
            risk_score=0.0,
            impacted_suppliers=[],
            analysis="",
            report_draft="",
            next_step=""
        )
        
        # Run the graph
        # For simplicity in this MVP, we'll wait for the final result instead of streaming
        # In a real app, we'd use StreamingResponse
        final_state = await graph_app.ainvoke(initial_state)
        
        return {
            "status": "success",
            "report": final_state.get("report_draft", "No report generated."),
            "risk_score": final_state.get("risk_score", 0),
            "impacted_suppliers": final_state.get("impacted_suppliers", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/regions")
def get_regions():
    """
    Fetches the list of unique countries (regions) where suppliers are located.
    """
    import psycopg2
    import os
    
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            port=os.getenv("POSTGRES_PORT")
        )
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT country FROM suppliers ORDER BY country ASC")
        rows = cur.fetchall()
        countries = [row[0] for row in rows]
        
        cur.close()
        conn.close()
        return {"regions": countries}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in /regions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
