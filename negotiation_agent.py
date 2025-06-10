import os
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
from langchain_huggingface import HuggingFaceEndpoint

load_dotenv(dotenv_path="./secrets.env")

class NegotiationState(TypedDict):
    business_name: str
    business_type: str
    items: List[Dict]
    food_banks: List[Dict]
    previous_attempts: List[Dict]
    current_message: Optional[str]
    response: Optional[str]
    status: str

llm_model_id = "mistralai/Mixtral-8x7B-Instruct-v0.1"
primary_llm = HuggingFaceEndpoint(repo_id=llm_model_id, task="text-generation", temperature=0.7, max_new_tokens=1024)
simulator_llm = HuggingFaceEndpoint(repo_id=llm_model_id, temperature=0.5, max_new_tokens=512)


def format_items(items: List[Dict]) -> str:
    return "\n".join([
        f"- {item['type']}: {item['quantity']} units (expires {item['expiry']})"
        for item in items
    ])

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

Generate a professional initial message to start the negotiation process. Include:
1. Specific food items and their expiry dates
2. Nearby food bank options
3. Benefits of food donation (reduced food waste, community support)
4. Request for a meeting to discuss details"""
    
    response = primary_llm.invoke(prompt)
    return {**state, "current_message": response}


def simulate_business_response(state: NegotiationState) -> NegotiationState:
    prompt = f"""You are the business owner. You received this message from the food donation agent:

{state['current_message']}

Respond appropriately to continue the negotiation."""
    response = simulator_llm.invoke(prompt)
    return {**state, "response": response}


def analyze_and_adapt(state: NegotiationState) -> NegotiationState:
    prompt = f"""Analyze the business response and adapt the negotiation strategy:

Previous message: {state.get('current_message', 'None')}
Business response: {state.get('response', 'None')}

Generate the next message to continue the negotiation."""
    response = primary_llm.invoke(prompt)
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

workflow = StateGraph(NegotiationState)
workflow.add_node("generate_message", generate_initial_message)
workflow.add_node("simulate_response", simulate_business_response)
workflow.add_node("analyze_adapt", analyze_and_adapt)
workflow.set_entry_point("generate_message")
workflow.add_edge("generate_message", "simulate_response")
workflow.add_edge("simulate_response", "analyze_adapt")
workflow.add_conditional_edges(
    "analyze_adapt",
    should_continue,
    {"end": END, "retry": "generate_message"}
)
negotiation_graph = workflow.compile()

def run_negotiation_initial(state: Dict) -> Dict:
    return generate_initial_message(state)

def run_negotiation_step(state: Dict, owner_resp: str) -> Dict:
    state["response"] = owner_resp
    state = analyze_and_adapt(state)
    if state["status"] == "ongoing":
        state = generate_initial_message(state)
    return state