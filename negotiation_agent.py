import os
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import HuggingFaceEndpoint

# ---------------------------
# Environment Setup
# ---------------------------
load_dotenv(dotenv_path="./secrets.env")

# ---------------------------
# Define State (including food_banks)
# ---------------------------
class NegotiationState(TypedDict):
    business_name: str
    business_type: str
    items: List[Dict]              # From scout agent: {type, quantity, expiry}
    food_banks: List[Dict]         # From logistics agent: {name, distance_m, latitude, longitude}
    previous_attempts: List[Dict]  # {message, response, outcome}
    current_message: Optional[str]
    response: Optional[str]
    status: str                    # ongoing, succeeded, failed

# ---------------------------
# Initialize Hugging Face LLMs (Mistral)
# ---------------------------
llm_model_id = "mistralai/Mixtral-8x7B-Instruct-v0.1"  

primary_llm = HuggingFaceEndpoint(
    repo_id=llm_model_id,
    task="text-generation",
    temperature=0.7,
    max_new_tokens=512,
    timeout=300 
)

simulator_llm = HuggingFaceEndpoint(
    repo_id=llm_model_id,
    temperature=0.5,
    max_new_tokens=300
)

# ---------------------------
# Core Functions 
# ---------------------------
def generate_initial_message(state: NegotiationState) -> NegotiationState:
    business_type = state["business_type"]
    items = state["items"]
    banks = state["food_banks"]
    total_value = sum(item.get('estimated_value', 100) for item in items)
    tax_savings = total_value * 0.3

    prompt = f"""
You're a food donation coordinator. Persuade a {business_type} to donate surplus food.

Items: {items}
Nearby food banks: {[f"{b['name']} ({b['distance_m']}m)" for b in banks]}
Previous attempts: {state.get('previous_attempts', [])}

Guidelines:
- Highlight estimated tax benefits (${tax_savings:.2f})
- Emphasize CSR impact
- Show you will deliver donations to the closest food banks
- Use a tone appropriate for {business_type}
- Keep message under 3 short paragraphs
"""
    response = primary_llm.invoke(prompt)
    return {**state, "current_message": response}

# simulate_business_response and analyze_and_adapt remain the same
# ---------------------------
def simulate_business_response(state: NegotiationState) -> NegotiationState:
    prompt = f"""
You're a manager at a {state['business_type']}. You received this message:

"{state['current_message']}"

Please respond realistically:
- Positive: enthusiastic agreement
- Neutral: interest with concerns
- Negative: polite refusal

Previous interactions: {state.get('previous_attempts', [])}
"""
    response = simulator_llm.invoke(prompt)
    return {**state, "response": response}

# ---------------------------
def analyze_and_adapt(state: NegotiationState) -> NegotiationState:
    previous = state.get("previous_attempts", [])
    classification_prompt = f"""
Classify the following response as: positive, neutral, or negative.
Response: {state['response']}
"""
    classification = primary_llm(classification_prompt).lower()
    new_attempt = {
        "message": state["current_message"],
        "response": state["response"],
        "outcome": classification.strip()
    }
    if "positive" in classification:
        status = "succeeded"
    elif len(previous) >= 2:
        status = "failed"
    else:
        status = "ongoing"
    return {**state, "previous_attempts": previous + [new_attempt], "status": status}

# ---------------------------
def should_continue(state: NegotiationState) -> str:
    return "end" if state["status"] != "ongoing" else "retry"

# ---------------------------
# Build Workflow 
# ---------------------------
workflow = StateGraph(NegotiationState)
workflow.add_node("generate_message", generate_initial_message)
workflow.add_node("simulate_response", simulate_business_response)
workflow.add_node("analyze_adapt", analyze_and_adapt)  # Correct node name

workflow.set_entry_point("generate_message")
workflow.add_edge("generate_message", "simulate_response")
workflow.add_edge("simulate_response", "analyze_adapt")  # Fixed target name

# Fixed conditional edge source
workflow.add_conditional_edges(
    "analyze_adapt",  # Correct source node name
    should_continue,
    {"end": END, "retry": "generate_message"}
)
negotiation_graph = workflow.compile()
# ---------------------------
# Manual Test Function 
# ---------------------------
def run_negotiation(business_info: Dict, logistics_data: Dict):
    initial_state = {
        "business_name": business_info["name"],
        "business_type": business_info["type"],
        "items": logistics_data["items"],
        "food_banks": logistics_data.get("food_banks", []),
        "previous_attempts": [],
        "status": "ongoing"
    }
    return negotiation_graph.invoke(initial_state)

# if __name__ == "__main__":
#     business = {"name": "Metro – Ossington Ave", "type": "grocery_store"}
#     logistics_output = {
#         "items": [
#             {"type": "Dairy - Greek Yogurt", "quantity": 5, "expiry": "2023-10-06"},
#             {"type": "Dairy - Skim Milk", "quantity": 20, "expiry": "2023-10-06"},
#             {"type": "Dairy - Greek Yogurt", "quantity": 6, "expiry": "2023-10-06"},
#             {"type": "Dairy - Sour Cream", "quantity": 18, "expiry": "2023-10-06"},
#             {"type": "Packaged - Brown Rice", "quantity": 27, "expiry": "2023-10-21"},
#             {"type": "Packaged - Cereal", "quantity": 26, "expiry": "2023-10-20"},
#             {"type": "Packaged - Granola Bars", "quantity": 49, "expiry": "2023-11-02"},
#             {"type": "Dairy - Mozzarella Cheese", "quantity": 18, "expiry": "2023-10-07"},
#             {"type": "Dairy - Greek Yogurt", "quantity": 47, "expiry": "2023-10-06"},
#             {"type": "Packaged - Potato Chips", "quantity": 15, "expiry": "2023-11-03"}
#         ],
#         "food_banks": [
#             {"name": "Parkdale Community Foodbank", "distance_m": 1830},
#             {"name": "West Lodge Tenant Run Food Bank", "distance_m": 2610}
#         ]
#     }
    
#     result = run_negotiation(business, logistics_output)
#     print("\nFinal Outcome:")
#     print(f"Status: {result['status'].upper()}")
#     print(f"Attempts: {len(result['previous_attempts'])}")
#     for i, attempt in enumerate(result['previous_attempts'], 1):
#         print(f"\nAttempt {i}:")
#         print(f"Message: {attempt['message']}")
#         print(f"Response: {attempt['response']}")
#         print(f"Outcome: {attempt['outcome'].upper()}")
