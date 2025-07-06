import openrouteservice
from openrouteservice import convert
from typing import List, Dict, Tuple
from dotenv import load_dotenv, os

load_dotenv(dotenv_path="./secrets.env")
client = openrouteservice.Client(key=os.getenv("ORS_API_KEY"))



def get_route(start: Tuple[float, float], end: Tuple[float, float]) -> Dict:
    try:
        route = client.directions(
            coordinates=[start, end],
            profile='driving-car',
            format='geojson'
        )
        summary = route['features'][0]['properties']['summary']
        return {
            "distance_km": round(summary['distance'] / 1000, 2),
            "duration_min": round(summary['duration'] / 60, 2)
        }
    except Exception as e:
        return {"error": str(e)}

def get_best_routes(start_coords: Tuple[float, float], food_banks: List[Dict], expiry_level: str) -> List[Dict]:
    routes = []
    for fb in food_banks:
        end_coords = (fb['longitude'], fb['latitude'])
        route = get_route(start_coords, end_coords)
        if "error" not in route:
            fb.update(route)
            routes.append(fb)

    # Sort by distance or urgency
    if expiry_level == "red_alert":
        return sorted(routes, key=lambda x: x["distance_km"])[:3]
    elif expiry_level == "warning":
        return sorted(routes, key=lambda x: x["duration_min"])[:5]
    else:
        return sorted(routes, key=lambda x: x["distance_km"])
