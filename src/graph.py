import os
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.state import AgentState
from src.tools import sql_tool, news_tool, fx_tool

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# --- Nodes ---

def supervisor_node(state: AgentState):
    """
    Routes the query to the appropriate agent.
    """
    messages = state['messages']
    last_message = messages[-1]
    
    prompt = """You are a Supply Chain Risk Supervisor.
    Analyze the user's request.
    - If they are asking for data (suppliers, shipments, news, exchange rates), route to 'data_fetcher'.
    - If they are asking for risk analysis (impact, assessment, correlation), route to 'risk_analyst'.
    - If the analysis is done and a report is needed, route to 'reporter'.
    
    Return ONLY the name of the next node: 'data_fetcher', 'risk_analyst', or 'reporter'.
    If the conversation is over or the request is unclear, return 'reporter' to summarize.
    """
    
    # Simple keyword-based routing for robustness, can be upgraded to LLM call
    content = last_message.content.lower()
    
    if "report" in content or "summary" in content:
        next_step = "reporter"
    elif "risk" in content or "impact" in content or "analyze" in content:
        next_step = "risk_analyst"
    else:
        next_step = "data_fetcher"
        
    return {"next_step": next_step}

def data_fetcher_node(state: AgentState):
    """
    Uses tools to fetch data.
    """
    messages = state['messages']
    # This agent has access to tools
    tools = [sql_tool, news_tool, fx_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}

def risk_analyst_node(state: AgentState):
    """
    Analyzes the data and calculates risk.
    """
    messages = state['messages']
    
    prompt = """You are a Risk Analyst.
    Review the conversation history, which includes data from SQL, News, and FX.
    
    Your goal is to:
    1. Identify any risks (e.g., natural disasters, financial instability, political unrest).
    2. Correlate them with our suppliers (from SQL data).
    3. Calculate a risk score (0-100).
    4. List impacted suppliers.
    
    CRITICAL: You must output valid JSON ONLY. Do not add any markdown formatting like ```json ... ```.
    
    The JSON structure must be:
    {
        "risk_score": <calculated_score>,
        "impacted_suppliers": [
            {
                "name": "<Actual Supplier Name>", 
                "country": "<Country>", 
                "category": "<Category>", 
                "risk_level": "High/Medium/Low",
                "trend": "Stable/Worsening/Improving"
            }
        ],
        "analysis": "Brief analysis of the risk..."
    }
    
    IMPORTANT: 
    - Use REAL supplier names found in the SQL tool output. 
    - If no specific suppliers are found in the data, return an empty list [] for impacted_suppliers.
    - Do NOT use "Supplier A" or "Supplier B" unless they are in the actual data.
    """
    
    response = llm.invoke([SystemMessage(content=prompt)] + messages)
    
    import json
    import re
    
    content = response.content
    risk_score = 0.0
    impacted_suppliers = []
    analysis = ""
    
    try:
        # Clean up potential markdown code blocks
        cleaned_content = re.sub(r'```json\s*', '', content)
        cleaned_content = re.sub(r'```', '', cleaned_content).strip()
        
        data = json.loads(cleaned_content)
        risk_score = float(data.get("risk_score", 0))
        impacted_suppliers = data.get("impacted_suppliers", [])
        analysis = data.get("analysis", "")
        
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        analysis = content # Fallback: use the whole content as analysis
        # Fallback parsing for score
        if "Risk Score:" in content:
            try:
                score_str = content.split("Risk Score:")[1].split("\n")[0].strip()
                risk_score = float(score_str)
            except:
                pass
            
    return {
        "messages": [response],
        "risk_score": risk_score,
        "impacted_suppliers": impacted_suppliers,
        "analysis": analysis
    }

def reporter_node(state: AgentState):
    """
    Generates the final report.
    """
    # We do NOT pass the full message history to avoid AI-AI confusion and JSON parsing issues.
    # Instead, we pass the structured analysis from the Risk Analyst.
    
    risk_score = state.get('risk_score', 0)
    analysis = state.get('analysis', "No analysis provided.")
    
    prompt = f"""You are a Reporter.
    
    RISK ANALYSIS:
    {analysis}
    
    RISK SCORE: {risk_score}
    
    TASK:
    Write a concise, markdown-formatted report for the user based *only* on the analysis above.
    
    CRITICAL INSTRUCTIONS:
    1. Do NOT list the specific suppliers in the text. The user can see them in the "Impacted Suppliers" dashboard panel.
    2. Focus on the *reasoning* for the risk.
    3. Keep it brief and professional.
    """
    
    # Invoke with a single HumanMessage containing the prompt
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {
        "messages": [response],
        "report_draft": response.content
    }

# --- Graph Definition ---

workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("data_fetcher", data_fetcher_node)
workflow.add_node("risk_analyst", risk_analyst_node)
workflow.add_node("reporter", reporter_node)

# Tool Node for Data Fetcher
tools = [sql_tool, news_tool, fx_tool]
tool_node = ToolNode(tools)
workflow.add_node("tools", tool_node)

# Edges
workflow.set_entry_point("supervisor")

def supervisor_router(state: AgentState):
    return state['next_step']

workflow.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "data_fetcher": "data_fetcher",
        "risk_analyst": "risk_analyst",
        "reporter": "reporter"
    }
)

def data_fetcher_router(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "risk_analyst" # After fetching data, go to analysis

workflow.add_conditional_edges(
    "data_fetcher",
    data_fetcher_router,
    {
        "tools": "tools",
        "risk_analyst": "risk_analyst"
    }
)

workflow.add_edge("tools", "data_fetcher") # Return to fetcher to process tool output
workflow.add_edge("risk_analyst", "reporter")
workflow.add_edge("reporter", END)

app = workflow.compile()
