import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://sportapi7.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "sportapi7.p.rapidapi.com",
    "Content-Type": "application/json"
}


def score_to_rating(score):
    """Convert numeric score to Poor/Average/Excellent"""
    if score >= 70: return "Excellent"
    if score >= 55: return "Good"
    if score >= 40: return "Average"
    return "Poor"

def search_players(name):
    """Search for players by name"""
    try: 
        url = f"{BASE_URL}/api/v1/search/players/{name}/more"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        data = response.json()
        players = []
        for p in data.get("players", []):
            players.append({
                "id": p["id"],
                "name": p["name"],
                "short_name": p.get("shortName", p["name"]),
                "position": p.get("position", "Unknown"),
                "team": p.get("team", {}).get("name", "Unknown"),
                "country": p.get("country", {}).get("name", "Unknown"),
                "jersey": p.get("jerseyNumber", "")
            })
        return players
    except Exception as e:
        print(f"Search error: {e}")
        return []

def get_player_details(player_id):
    """Get full player info"""
    try:
        url = f"{BASE_URL}/api/v1/player/{player_id}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        p = data.get("player", {})
        return {
            "id": p.get("id"),
            "name": p.get("name"),
            "position": p.get("position", "Unknown"),
            "team": p.get("team", {}).get("name", "Unknown"),
            "country": p.get("country", {}).get("name", "Unknown"),
            "jersey": p.get("jerseyNumber", "")
        }
    except Exception as e:
        print(f"Player details error {e}")
        return None

def get_player_abilities(player_id, position):
    """Get player attributes and convert to ability ratings"""
    try:
        url = f"{BASE_URL}/api/v1/player/{player_id}/attribute-overviews"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()

        # get most recent attributes  (yearShift=0)
        attrs = data.get("playerAttributeOverviews", [])
        if not attrs:
            return None

        latest = attrs[0]   # yearShift=0 is most recent

        # map API attributes to your ability system by position
        position_map = {
            "GK":  ["Positioning", "Defending", "Aerial"],
            "CB":  ["Positioning", "Defending", "Aerial", "Passing"],
            "LB":  ["Positioning", "Defending", "Passing", "Speed", "Stamina"],
            "RB":  ["Positioning", "Defending", "Passing", "Speed", "Stamina"],
            "DMF": ["Positioning", "Defending", "Passing", "Stamina"],
            "CMF": ["Positioning", "Passing", "Stamina", "Dribbling"],
            "LMF": ["Passing", "Stamina", "Dribbling", "Speed"],
            "RMF": ["Passing", "Stamina", "Dribbling", "Speed"],
            "AMF": ["Positioning", "Passing", "Dribbling", "Shooting"],
            "LWF": ["Speed", "Dribbling", "Shooting", "Passing"],
            "RWF": ["Speed", "Dribbling", "Shooting", "Passing"],
            "CF":  ["Positioning", "Aerial", "Shooting", "Dribbling"],
            "ST":  ["Positioning", "Aerial", "Shooting", "Stamina"]
        }

        # map API scores to your ability names
        api_to_ability = {
            "Positioning": score_to_rating(latest.get("tactical", 50)),
            "Defending":   score_to_rating(latest.get("defending", 50)),
            "Passing":     score_to_rating(latest.get("creativity", 50)),
            "Dribbling":   score_to_rating(latest.get("technical", 50)),
            "Shooting":    score_to_rating(latest.get("attacking", 50)),
            "Aerial":      score_to_rating(latest.get("attacking", 50)),
            "Stamina":     score_to_rating(latest.get("tactical", 50)),
            "Speed":       score_to_rating(latest.get("technical", 50)),
            "Leadership":  score_to_rating(latest.get("tactical", 50))
        }

        # return only abilities relevant to this position
        relevant = position_map.get(position, list(api_to_ability.keys()))
        return {ability: api_to_ability[ability] for ability in relevant}

    except Exception as e:
        print(f"Abilities error: {e}")
        return None

def map_api_position(api_position):
    """Convert API position code to your position system"""
    mapping = {
        "G":  "GK",
        "GK": "GK",
        "D":  "CB",
        "DC": "CB",
        "DL": "LB",
        "DR": "RB",
        "M":  "CMF",
        "MC": "CMF",
        "ML": "LMF",
        "MR": "RMF",
        "DM": "DMF",
        "AM": "AMF",
        "F":  "ST",
        "FC": "ST",
        "FL": "LWF",
        "FR": "RWF",
        "FW": "ST"
    }
    return mapping.get(api_position, "CMF")

















