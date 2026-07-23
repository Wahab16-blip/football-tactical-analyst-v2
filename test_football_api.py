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

def search_players(name):
    url = f"{BASE_URL}/api/v1/search/players/{name}/more"
    response = requests.get(url, headers=headers)
    print(f"Search Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2)[:3000])   # first 3000 chars

def get_player(player_id):
    url = f"{BASE_URL}/api/v1/player/{player_id}"
    response = requests.get(url, headers=headers)
    print(f"Player Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2)[:3000])

def get_player_attributes(player_id):
    url = f"{BASE_URL}/api/v1/player/{player_id}/attribute-overviews"
    response = requests.get(url, headers=headers)
    print(f"Attributes Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2)[:3000])

def search_teams(name):
    url = f"{BASE_URL}/api/v1/search/teams/{name}/more"
    response = requests.get(url, headers=headers)
    print(f"Teams Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2)[:3000])

def get_team_events(team_id):
    url = f"{BASE_URL}/api/v1/team/{team_id}/events/next/0"
    response = requests.get(url, headers=headers)
    print(f"Next Events Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2)[:3000])

def get_team_last_events(team_id):
    url = f"{BASE_URL}/api/v1/team/{team_id}/events/last/0"
    response = requests.get(url, headers=headers)
    print(f"Last Events Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2)[:3000])

def get_team_form(team_id, team_name):
    url = f"{BASE_URL}/api/v1/team/{team_id}/events/last/0"
    response = requests.get(url, headers=headers)
    data = response.json()

    all_events = data.get("events", [])   # ← renamed to all_events
    last_5 = all_events[-5:]              # ← use all_events not events
    
    form = []
    goals_scored = 0
    goals_conceded = 0
    
    for match in last_5:                  # ← renamed to match
        home = match["homeTeam"]["name"]
        away = match["awayTeam"]["name"]
        home_score = match.get("homeScore", {}).get("current", 0) or 0
        away_score = match.get("awayScore", {}).get("current", 0) or 0
        winner = match.get("winnerCode", 0)
        
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
        print(f"{home} {home_score}-{away_score} {away} → {result}")
    
    print(f"\nForm: {' '.join(form)}")
    print(f"Goals scored: {goals_scored} | Conceded: {goals_conceded}")
    
    return {
        "form": form,
        "goals_scored": goals_scored,
        "goals_conceded": goals_conceded
    }



#Test both
#search_players("ronaldo")
#get_player(750)    # Ronaldo's id from search result
#get_player_attributes(750)
#search_teams("chelsea")
#get_team_last_events(38)
get_team_form(38, "Chelsea")

























