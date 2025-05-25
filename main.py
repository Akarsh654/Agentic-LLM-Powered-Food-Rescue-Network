import pandas as pd
from geopy.geocoders import Nominatim
from scout_agent import classify_items_by_expiry
from logistics_agent import query_food_banks_node, get_best_routes_node, justification_node
from negotiation_agent import generate_initial_message, simulate_business_response, analyze_and_adapt

# Load dataset
df = pd.read_csv("./data/merged_dataset.csv")

# Initialize geocoder
geolocator = Nominatim(user_agent="donation_agent")

# Get unique stores
unique_stores = df["store_name"].dropna().unique()

for store in unique_stores:
    print(f"\n===== Processing Store: {store} =====")
    expiry_zones = classify_items_by_expiry(df, store)

    for expiry_level in ["red_alert", "warning"]:
        items_df = expiry_zones[expiry_level]
        if items_df.empty:
            continue

        # Directly use lat/lon from dataset
        store_rows = df[df["store_name"] == store]
        if store_rows.empty:
            print(f"No data found for store: {store}")
            continue
        lat = store_rows["latitude"].iloc[0]
        lon = store_rows["longitude"].iloc[0]

        # ---- Logistics Agent (manual call of each node) ----
        state = {
            "lat": lat,
            "lon": lon,
            "expiry_level": expiry_level,
            "food_banks": [],
            "routes": [],
            "justification": ""
        }

        state = query_food_banks_node(state)
        state = get_best_routes_node(state)
        state = justification_node(state)
        selected_routes = state["routes"]

        # ---- Prepare items for negotiation agent ----
        grouped = items_df.groupby(["food_item", "food_category", "expiry_date", "unit"])["quantity"].sum().reset_index()
        grouped = grouped.rename(columns={"food_item": "type"})
        grouped["expiry"] = grouped["expiry_date"].astype(str)
        item_list = grouped[["type", "quantity", "expiry"]].to_dict(orient="records")

        print(f"\nItems in {expiry_level.upper()} zone:")
        for idx, row in items_df.iterrows():
            expiry_date = row['expiry_date'].strftime("%Y-%m-%d")
            print(f"{row['food_category']} - {row['food_item']} | Quantity: {row['quantity']} {row['unit']} | Expiry Date: {expiry_date} (in {row['days_to_expiry']} days)")


        # ---- Negotiation Agent ----
        negotiation_state = {
            "business_name": store,
            "business_type": "grocery_store",
            "items": item_list,
            "food_banks": selected_routes,
            "previous_attempts": [],
            "current_message": None,
            "response": None,
            "status": "ongoing"
        }

        while negotiation_state["status"] == "ongoing":
            negotiation_state = generate_initial_message(negotiation_state)
            negotiation_state = simulate_business_response(negotiation_state)
            negotiation_state = analyze_and_adapt(negotiation_state)

        # ---- Output Results ----
        print(f"\nNegotiation Result for {store} ({expiry_level.upper()} items):")
        print(f"Status: {negotiation_state['status'].upper()}")
        for i, attempt in enumerate(negotiation_state["previous_attempts"], 1):
            print(f"\nAttempt {i}:")
            print(f"Message:\n{attempt['message']}")
            print(f"Response:\n{attempt['response']}")
            print(f"Outcome: {attempt['outcome'].upper()}")

print("\n=== All Stores Processed ===")
