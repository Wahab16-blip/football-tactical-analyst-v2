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


#Test both
#search_players("ronaldo")
#get_player(750)    # Ronaldo's id from search result
get_player_attributes(750)


























