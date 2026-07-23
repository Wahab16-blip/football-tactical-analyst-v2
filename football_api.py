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


def search_teams(name):
    """Search for a team by name"""
    try:
        url = f"{BASE_URL}/api/v1/search/teams/{name}/more"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        data = response.json()
        teams = []
        for t in data.get("teams", []):
            # only include men's senior clubs
            if t.get("gender") == "M" and not t.get("national", False):
                teams.append({
                    "id": t["id"],
                    "name": t["name"],
                    "country": t.get("country", {}).get("name", "Unknown"),
                    "code": t.get("nameCode", "")
                })
        return teams[:5]
    except Exception as e:
        print(f"Team search error: {e}")
        return []

def get_opposition_analysis(team_id, team_name):
    """Get opposition recent form and stats"""
    try:
        url = f"{BASE_URL}/api/v1/team/{team_id}/events/last/0"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()

        all_events = data.get("events", [])
        last_5 = all_events[-5:]

        form = []
        goals_scored = 0
        goals_conceded = 0
        matches = []

        for match in last_5:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            home_score = match.get("homeScore", {}).get("current", 0) or 0
            away_score = match.get("awayScore", {}).get("current", 0) or 0
            winner = match.get("winnerCode", 0)
            tournament = match.get("tournament", {}).get("name", "Unknown")

            is_home = team_name.lower() in home.lower()

            if winner == 3:
                result = "D"
            elif (winner == 1 and is_home) or (winner == 2 and not is_home):
                result = "W"
            else:
                result = "L"

            if is_home:
                goals_scored += home_score
                goals_conceded += away_score
            else:
                goals_scored += away_score
                goals_conceded += home_score

            form.append(result)
            matches.append(
                f"{home} {home_score}-{away_score} {away} ({tournament})"
            )

        # analyse form
        wins = form.count("W")
        draws = form.count("D")
        losses = form.count("L")

        if wins >= 3:
            form_rating = "Excellent"
        elif wins >= 2:
            form_rating = "Good"
        elif wins >= 1:
            form_rating = "Average"
        else:
            form_rating = "Poor"

        # defensive/attacking assessment
        avg_scored = goals_scored / max(len(last_5), 1)
        avg_conceded = goals_conceded / max(len(last_5), 1)

        attacking = "Strong" if avg_scored >= 2 else "Moderate" if avg_scored >= 1 else "Weak"
        defensive = "Solid" if avg_conceded <= 1 else "Vulnerable" if avg_conceded >= 2 else "Moderate"

        return {
            "team": team_name,
            "form": form,
            "form_string": " ".join(form),
            "form_rating": form_rating,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "attacking_strength": attacking,
            "defensive_strength": defensive,
            "recent_matches": matches
        }

    except Exception as e:
        print(f"Opposition analysis error: {e}")
        return None














