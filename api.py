from fastapi import FastAPI, HTTPException 
from pydantic import BaseModel
from typing import List, Optional
import uvicorn 
import os
from dotenv import load_dotenv
import anthropic
import requests
import numpy as np
from sentence_transformers import SentenceTransformer 

load_dotenv()

# --- Clients ----
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- FastAPI App ----
app = FastAPI(
    title="Football Tactical Analyst API",
    description="AI-powered tactical analysis for football coaches",
    version="1.0.0"
)


# --- Data Models ----
class Player(BaseModel):
    name: str
    position: str
    condition: str = "Fit"

class MatchRequest(BaseModel):
    team: str
    opposition: str
    venue: str
    league: str
    players: List[Player]
    opp_formation: str = "Unknown"
    opp_notes: str = ""

class SquadPlayer(BaseModel):
    name: str
    position: str
    form: str
    abilities: dict

class SquadRequest(BaseModel):
    players: List[SquadPlayer]


def ask_claude(messages, system):
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=messages
        )
        return message.content[0].text
    except anthropic.APIConnectionError:
        return "Anthropic connection failed."
    except anthropic.AuthenticationError:
        return "Invalid API key. Check your .env file"
    except anthropic.RateLimitError:
        return "Anthropic rate limit hit. Try again."
    except Exception as e:
        return f"Something went wrong: {e}"
    

def get_weather(city):
    for attempt in range(2):
        try:
            url = f"https://wttr.in/{city}?format=j1"
            response = requests.get(url, timeout=30)
            break 
        except requests.exceptions.ConnectTimeout:
            print(f"Attempt: {attempt + 1}, timed out. Retrying.... ")
        except requests.exceptions.ConnectionError:
            if attempt == 0:
                print("Connection failed. Retrying....")
            else:
                print("Could not connect. Check your internet and try again.")
                return 
            
    try:
        if response.status_code != 200:
            print(f"City '{city}' not found")
            return
        
        data = response.json()

        current = data["current_condition"][0]
        temp = current.get("temp_C", "N/A")
        description = current["weatherDesc"][0]["value"]

        return f"{city}: {temp}°C, {description}."
    
    except Exception as e:
        print(f"Something went wrong: {e}")


def build_knowledge_base():
    return [
        # Formations
        "The 4-3-3 formation uses three forwards and is ideal for teams with fast wingers who press high. It is weak against teams with strong defensive midfielders.",
        "The 4-4-2 is a balanced formation with two strikers. It is effective for counter-attacking but vulnerable to teams with a creative number 10.",
        "The 3-5-2 uses three centre-backs and two wing-backs. It is strong defensively and effective against wide attacking teams.",
        "The 4-2-3-1 provides a double pivot in midfield for protection. It is best used against high-pressing teams to maintain possession.",
        "The 5-3-2 is a defensive formation with five defenders. It is ideal when protecting a lead or facing a superior attacking team.",

        # Play styles
        "High press tactics require high fitness levels from all outfield players. Fatigued players should never be asked to press high as it leaves defensive gaps.",
        "Counter-attacking play suits teams with fast strikers and a low defensive block. It is most effective on large pitches with space in behind.",
        "Possession-based play requires technically skilled players and is less effective in wet or windy conditions where ball control is harder.",
        "A low block defensive shape reduces the space behind the defence. It is recommended when facing stronger opposition or protecting a lead.",
        "Direct play using long balls is effective when the opposition defence is high and there is a strong aerial striker available.",

        # Weather impact
        "In heavy rain, long passing accuracy drops significantly. Coaches should use short ground passes and avoid aerial balls.",
        "In strong wind, high balls become unpredictable. Teams should play along the ground and adjust set piece routines accordingly.",
        "In extreme heat above 30 degrees, pressing intensity should be reduced by 40 percent to prevent player fatigue and cramps.",
        "In cold conditions below 5 degrees, players are slower to react in the first 20 minutes. A cautious start with defensive solidity is recommended.",

        # Player conditions
        "Fatigued players should be substituted if possible. If unavailable, drop the defensive line and reduce pressing to minimise their running load.",
        "Players returning from injury should be protected with a midfielder covering their side. Avoid placing them in physical duel situations.",
    ]

def get_embedding(text):
    return embedding_model.encode(text)

def cosine_similarity (a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def semantic_search(query, documents, top_k=2):
    query_embedding = get_embedding(query)

    results =[]
    for doc in documents:
        doc_embedding = get_embedding(doc)
        score = cosine_similarity(query_embedding, doc_embedding)
        results.append((doc, score))

    results = sorted(results, key=lambda x: x[1], reverse=True)
    print(f"\nQuery: '{query}'")
    print(f"Top {top_k} results:")
    print("="*50)
    
    return results[:top_k]

def search_tactics(query):
    knowledge_base = build_knowledge_base()
    results = semantic_search(query, knowledge_base, top_k=2)
    if results:
        found = []
        for doc, score in results:
            found.append(f"({score:.2f}): {doc}")
        return "\n".join(found)
    return "No relevant tactical information found."

def generate_report(match_context):
    system = """You are an expert football tactical analyst assistant.
You have acces to these tools:
- get_weather(city) → gets current weather at the match venue
- search_tactics(query) → searches football tactical knowledge base

RULES:
- Call ONE tool at a time
- Wait for result before calling another
- Output TOOL: or ANSWER: as the VERY FIRST thing
- No explanation before TOOL: or ANSWER:

After gathering all information, generate a structured report with these sections:
1. Squad Condition Assessment
2. Weather & Pitch Conditions
3. Opposition Analysis
4. Recommended Formation & Tactics
5. Match Outcome Prediction

Format it clearly with section headers."""

    players_text = "\n".join([
    f"{p['position']}: {p['name']} ({p['condition']})"
    for p in match_context['players']
    if p['name']  # only include players with names
    ])

    # build the prompt from match context
    context_prompt = f"""
Analyse this match and generate a tactical report:

Team: {match_context['team']}
Opposition: {match_context['opposition']}
League: {match_context['league']}
Venue: {match_context['venue']}

Starting 11:
{players_text}

Known Opposition Formation: {match_context['opp_formation']} 
Additional Notes: {match_context.get('opp_notes', 'None')}

Please:
1. Get the weather at {match_context['venue']}
2. Search for tactics against {match_context['opp_formation']} formation
3. Search for how conditions affect tactics
4. Generate the full tactical report
"""
    messages = [{"role": "user", "content": context_prompt}]

    print("\n⚽ Generating tactical report...\n")
    
    while True:
        response = ask_claude(messages, system)
        print(f"Analyst: {response}\n")
        
        if response.startswith("ANSWER:"):
            return response.replace("ANSWER:", "").strip()
        
        elif "TOOL:" in response:
            for line in response.split("\n"):
                if line.strip().startswith("TOOL:"):
                    tool_call = line.replace("TOOL:", "").strip()
                    result = execute_tool(tool_call)
                    print(f"Tool result: {result}\n")
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": f"Tool result: {result}"})
                    break
        else:
            return response
        

def execute_tool(tool_call):
    parts = tool_call.split("(")
    tool_name = parts[0].strip()
    argument = parts[1].replace(")", "").strip()

    if tool_name == "get_weather":
        return get_weather(argument)
    elif tool_name == "search_tactics":
        return search_tactics(argument)
    else:
        return f"Unknown tool: {tool_name}"
    
def generate_formations(squad):
    """Ask Claude to generate 3 formations based on squad data"""
    system = """You are an expert football tactical analyst. 
Analyse the squad provided and generate exactly 3 different formation recommendations.

RULES:
- Output ANSWER: as the very first thing
- No explanation before ANSWER:
- Each formation must be genuinely different in style
- Base recommendations on actuall player abilities and form
- Be specific about which players start where

Format each formation EXACTLY like this:

FORMATION 1:
Name: [formation name e.g. 4-3-3]
Style: [play style e.g. High Press, Attacking]
Best Used When: [situation]
Starting 11:
[position]: [player name] - [reason]
(list all 11)
Key Tactics:
- [tactic 1]
- [tactic 2]
- [tactic 3]

FORMATION 2:
[same format]

FORMATION 3:
[same format]"""

    if not squad:
        return "No squad data provided."

    squad_text = "\n".join([
        f"{p['name']} | {p['position']} | Form: {p['form']} | "
        f"Abilities: {', '.join([f'{k}: {v}' for k, v in p['abilities'].items()])}"
        for p in squad
        if p.get('name')
    ])

    if not squad_text.strip():
        return "Squad data is empty - please add players first."

    messages = [{
        "role": "user",
        "content": f"""Analyse this squad and generate 3 formation recommendations:
{squad_text}

Generate 3 distinct formations (attacking, balanced, defensive)
that best utilise these players based on their form and abilities."""
    }]

    response = ask_claude(messages, system)
    if response.startswith("ANSWER:"):
        return response.replace("ANSWER:", "").strip()
    return response


# ---- Health Check -----
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Football Tactical Analyst API",
        "version": "1.0.0"
    }

# --- Analyse Match Endpoint ----
@app.post("/analyse")
async def analyse_match(request: MatchRequest):
    try:
        # validate player count
        if len(request.players) < 11:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 11 players. Got {len(request.players)}"
            )

        # build match context from request
        match_context = {
            "team": request.team,
            "opposition": request.opposition,
            "venue": request.venue,
            "league": request.league,
            "players": [p.dict() for p in request.players],
            "opp_formation": request.opp_formation,
            "opp_notes": request.opp_notes
        }
        report = generate_report(match_context)
        return {
            "status": "success",
            "team": request.team,
            "opposition": request.opposition,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# --- Generate Formations Endpoint ----
@app.post("/formations")
async def get_formations(request: SquadRequest):
    try:
        squad = [p.dict() for p in request.players]
        if len(squad) < 11:
            raise HTTPException(
                status_code=400,
                deatail=f"Need at least 11. Got {len(squad)}"
            )
        formations = generate_formations(squad)
        return {
            "status": "success",
            "formation": formations 
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ─── Get Squad Endpoint ───
@app.get("/squad")
async def get_squad():
    try:
        import json
        if os.path.exists("squad.json"):
            with open("squad.json", "r", encoding="utf-8") as f:
                squad = json.load(f)
            return {"status": "success", "squad": squad, "count": len(squad)}
        return {"status": "success", "squad": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Run the server ----
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
























































