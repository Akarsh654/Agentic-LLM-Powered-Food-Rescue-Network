import os
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv(dotenv_path="./secrets.env")

# ---------------------------
# Define State
# ---------------------------
class NegotiationState(TypedDict):
    business_name: str
    business_type: str
    items: List[Dict]
    food_banks: List[Dict]
    previous_attempts: List[Dict]
    current_message: Optional[str]
    response: Optional[str]
    status: str

# ---------------------------
# Initialize LLMs using OpenRouter
# ---------------------------
llm_model_id = "mistralai/mistral-small-3.2-24b-instruct:free"

primary_llm = ChatOpenAI(
    model=llm_model_id,
    temperature=0.7,
    max_tokens=1024,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_API_BASE")
)

simulator_llm = ChatOpenAI(
    model=llm_model_id,
    temperature=0.5,
    max_tokens=512,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_API_BASE")
)

# ---------------------------
# Format Function
# ---------------------------
def format_items(items: List[Dict]) -> str:
    # Group items by food type
    grouped_items = {}
    for item in items:
        food_type = item['type']
        if food_type not in grouped_items:
            grouped_items[food_type] = []
        grouped_items[food_type].append(item)
    
    # Format each group
    formatted_items = []
    for food_type, items_list in grouped_items.items():
        if len(items_list) == 1:
            formatted_items.append(
                f"- {food_type}: {items_list[0]['quantity']} units (expires {items_list[0]['expiry']})"
            )
        else:
            entries = []
            for item in items_list:
                entries.append(f"{item['quantity']} units (expires {item['expiry']})")
            formatted_items.append(
                f"- {food_type}: {', '.join(entries)}"
            )
    
    return "\n".join(formatted_items)

# ---------------------------
# Negotiation Functions
# ---------------------------
def generate_initial_message(state: NegotiationState) -> NegotiationState:
    items_str = "\n".join([
        f"- {item['food']}: {item['quantity']} units (expires {item['expiry']})" 
        for item in state['items']
    ])
    
    food_banks_str = "\n".join([
        f"- {fb['name']}: {fb['distance_m']} meters away" 
        for fb in state['food_banks'][:3] 
    ])

    prompt = f"""You are a food donation negotiation agent. You are negotiating with {state['business_name']} ({state['business_type']}) about donating food items.

Current items available:
{items_str}

Nearby food banks that can accept these donations:
{food_banks_str}

Generate a professional initial message to start the negotiation process. Make sure to:
1. Mention the specific food items and their expiry dates
2. Name the nearby food banks explicitly: {', '.join([fb['name'] for fb in state['food_banks'][:3]])}
3. Highlight benefits of food donation (reduced food waste, community support)
4. Request a meeting to discuss details

Important: Use the actual food bank names in the message instead of a generic placeholder like "[Your Organization's Name]". The message should be personalized to mention the specific food banks that can accept the donations."""

    response = primary_llm.invoke([HumanMessage(content=prompt)]).content
    return {**state, "current_message": response}

def simulate_business_response(state: NegotiationState) -> NegotiationState:
    prompt = f"""You are the business owner. You received this message from the food donation agent:

{state['current_message']}

Respond appropriately to continue the negotiation."""
    response = simulator_llm.invoke([HumanMessage(content=prompt)]).content
    return {**state, "response": response}

def analyze_and_adapt(state: NegotiationState) -> NegotiationState:
    prompt = f"""Analyze the business response and adapt the negotiation strategy:

Previous message: {state.get('current_message', 'None')}
Business response: {state.get('response', 'None')}

Generate the next message to continue the negotiation."""
    
    response = primary_llm.invoke([HumanMessage(content=prompt)]).content
    lc = response.lower()
    if "agreement" in lc or "donation" in lc:
        status = "completed"
    elif "no" in lc or "decline" in lc:
        status = "failed"
    else:
        status = "ongoing"
    prev = state.get('previous_attempts', [])
    attempt = {"message": state.get('current_message'), "response": state.get('response'), "outcome": status}
    return {**state, "previous_attempts": prev + [attempt], "current_message": response, "status": status}

def should_continue(state: NegotiationState) -> str:
    return "end" if state["status"] != "ongoing" else "retry"

# ---------------------------
# Build LangGraph Workflow
# ---------------------------
workflow = StateGraph(NegotiationState)
workflow.add_node("generate_message", generate_initial_message)
workflow.add_node("simulate_response", simulate_business_response)
workflow.add_node("analyze_adapt", analyze_and_adapt)
workflow.set_entry_point("generate_message")
workflow.add_edge("generate_message", "simulate_response")
workflow.add_edge("simulate_response", "analyze_adapt")
workflow.add_conditional_edges("analyze_adapt", should_continue, {"end": END, "retry": "generate_message"})

negotiation_graph = workflow.compile()

# ---------------------------
# Run Functions
# ---------------------------
def run_negotiation_initial(state: Dict) -> Dict:
    return generate_initial_message(state)

def run_negotiation_step(state: Dict, owner_resp: str) -> Dict:
    state["response"] = owner_resp
    state = analyze_and_adapt(state)
    if state["status"] == "ongoing":
        state = generate_initial_message(state)
    return state
