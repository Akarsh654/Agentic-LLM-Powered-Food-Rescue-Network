import os
from dotenv import load_dotenv
import overpy
from geopy.distance import geodesic
import openrouteservice
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Tuple

# ---------------------------
# Environment Setup
# ---------------------------
load_dotenv(dotenv_path="./secrets.env")
ORS_API_KEY = os.getenv("ORS_API_KEY")

client = openrouteservice.Client(key=ORS_API_KEY)
api = overpy.Overpass()

# ---------------------------
# Define State
# ---------------------------
class RouteState(TypedDict):
    lat: float
    lon: float
    expiry_level: str
    food_banks: List[Dict]
    routes: List[Dict]
    justification: str

# ---------------------------
# Define Functions
# ---------------------------
def query_food_banks_node(state: RouteState) -> RouteState:
    lat, lon = state['lat'], state['lon']
    radius_km = 5
    delta = radius_km / 111
    lat_min = lat - delta
    lat_max = lat + delta
    lon_min = lon - delta
    lon_max = lon + delta

    query = f"""
    (
      node["amenity"="food_bank"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["amenity"="food_bank"]({lat_min},{lon_min},{lat_max},{lon_max});
      node["social_facility"="food_bank"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["social_facility"="food_bank"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    out center;
    """
    result = api.query(query)
    food_banks = []

    for node in result.nodes:
        distance_m = int(geodesic((lat, lon), (node.lat, node.lon)).meters)
        food_banks.append({
            "name": node.tags.get("name", "Unnamed Food Bank"),
            "latitude": node.lat,
            "longitude": node.lon,
            "distance_m": distance_m
        })

    for way in result.ways:
        if way.center_lat and way.center_lon:
            distance_m = int(geodesic((lat, lon), (way.center_lat, way.center_lon)).meters)
            food_banks.append({
                "name": way.tags.get("name", "Unnamed Food Bank"),
                "latitude": way.center_lat,
                "longitude": way.center_lon,
                "distance_m": distance_m
            })

    food_banks = sorted(food_banks, key=lambda x: x["distance_m"])
    return {**state, "food_banks": food_banks}

def get_best_routes_node(state: RouteState) -> RouteState:
    start_coords = (state['lon'], state['lat'])
    expiry_level = state['expiry_level']
    food_banks = state['food_banks']
    routes = []

    for fb in food_banks:
        end_coords = (fb['longitude'], fb['latitude'])

        # Ensure that Decimal values are converted to float
        start_coords = tuple(map(float, start_coords))
        end_coords = tuple(map(float, end_coords))

        try:
            route = client.directions(
                coordinates=[start_coords, end_coords],
                profile='driving-car',
                format='geojson'
            )
            summary = route['features'][0]['properties']['summary']
            fb.update({
                "distance_km": round(summary['distance'] / 1000, 2),
                "duration_min": round(summary['duration'] / 60, 2)
            })
            routes.append(fb)
        except Exception as e:
            print(f"An error occurred while fetching route: {e}")
            continue

    if expiry_level == "red_alert":
        sorted_routes = sorted(routes, key=lambda x: x["distance_km"])[:3]
    elif expiry_level == "warning":
        sorted_routes = sorted(routes, key=lambda x: x["duration_min"])[:5]
    else:
        sorted_routes = sorted(routes, key=lambda x: x["distance_km"])

    return {**state, "routes": sorted_routes}

# ---------------------------
# Define Justification Agent
# ---------------------------
def justification_node(state: RouteState) -> RouteState:
    expiry_level = state['expiry_level']

    if expiry_level == "red_alert":
        justification = (
            "The selected food banks are the closest to the location, "
            "prioritizing minimal travel distance to ensure urgent delivery."
        )
    elif expiry_level == "warning":
        justification = (
            "The selected food banks are chosen based on the shortest travel time, "
            "to ensure timely delivery while considering slightly less urgent needs."
        )
    else:
        justification = (
            "The selected food banks are chosen based on proximity, "
            "as there are no urgent expiry concerns."
        )

    return {**state, "justification": justification}

# ---------------------------
# Run the Flow
# ---------------------------
if __name__ == "__main__":
    # ---------------------------
    # LangGraph Setup
    # ---------------------------
    workflow = StateGraph(RouteState)
    workflow.add_node("query_food_banks", query_food_banks_node)
    workflow.add_node("get_routes", get_best_routes_node)
    workflow.add_node("justify_selection", justification_node)

    workflow.set_entry_point("query_food_banks")
    workflow.add_edge("query_food_banks", "get_routes")
    workflow.add_edge("get_routes", "justify_selection")
    workflow.add_edge("justify_selection", END)

    graph = workflow.compile()

    result = graph.invoke({
        "lat": 43.6485,
        "lon": -79.4205,
        "expiry_level": "red_alert"
    })

    for r in result['routes']:
        print(f"Food Bank: {r['name']}")
        print(f"Distance: {r['distance_km']} km")
        print(f"Duration: {r['duration_min']} min\n")

    # Print the justification
    print("\n--- Justification ---")
    print(result['justification'])