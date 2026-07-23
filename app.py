import streamlit as st
import json
import os
import sys
import anthropic 
import numpy as np
import requests
from dotenv import load_dotenv 
from sentence_transformers import SentenceTransformer
from datetime import datetime
from database import (init_database, save_report, get_all_reports, get_report_by_id, delete_report,
                    save_player, get_squad, delete_player, search_reports, register_coach, login_coach)
from football_api import (search_players, get_player_details, get_player_abilities, map_api_position,
                          search_teams, get_opposition_analysis)


# initialise database on startup
init_database()

load_dotenv()

#--- Password Protection ----
def show_auth_page():
    """Show login and register tabs"""
    st.title("⚽ Football Tactical Analyst")
    st.markdown("---")

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        st.subheader("Coach Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password",
                                  key="login_password")

        if st.button("Login", type="primary", key="login_btn"):
            if not username or not password:
                st.error("Please enter username and password.")
            else:
                coach = login_coach(username, password)
                if coach:
                    st.session_state["coach"] = coach
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tab2:
        st.subheader("Create Account")
        new_username = st.text_input("Choose Username",
                                      key="reg_username")
        new_password = st.text_input("Choose Password",
                                      type="password",
                                      key="reg_password")
        confirm = st.text_input("Confirm Password",
                                 type="password",
                                 key="reg_confirm")

        if st.button("Register", type="primary", key="reg_btn"):
            if not new_username or not new_password:
                st.error("Please fill in all fields.")
            elif new_password != confirm:
                st.error("Passwords don't match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                success = register_coach(new_username, new_password)
                if success:
                    st.success("Account created! Please login.")
                else:
                    st.error("Username already taken.")

# ─── Auth gate ───
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    show_auth_page()
    st.stop()

# ─── Logged in — show coach info in sidebar ───
coach = st.session_state["coach"]
st.sidebar.markdown(f"👤 **{coach['username']}**")
st.sidebar.markdown(f"*{coach['role'].capitalize()}*")
if st.sidebar.button("Logout", key="logout_btn"):
    del st.session_state["authenticated"]
    del st.session_state["coach"]
    st.rerun()
st.sidebar.markdown("---")



# ─── Backend (copied from football_analyst.py) ───
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

coach_id = st.session_state["coach"]["id"]

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

def get_coach_input():
    print("\n=== TACTICAL ANALYST - PRE-MATCH BRIEFING ===\n")

    team = input("Your club name: ")
    opposition = input("Opposition team name: ")
    venue = input("Match venue city: ")
    league = input("League/Competition: ")

    # collect starting 11
    print("\nEnter your starting 11 (name and position):")
    players = []
    for i in range(11):
        player = input(f" Player {i+1} (e.g John Smith - Striker): ")
        players.append(player)

    # collect conditions
    print("\nPlayer conditions (press Enter to skip if all fit):")
    conditions = input("Any fatiqued/injured/returning players? ")

    # opposition formation
    opp_formation = input("\nKnown opposition formation (or press Enter if unknown):")
    if opp_formation == "":
        opp_formation = "Unknown"

    return {
        "team": team,
        "opposition": opposition,
        "venue": venue,
        "league": league,
        "players": players,
        "conditions": conditions,
        "opp_formation": opp_formation
    }

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

    # build opposition analysis section
    opp_analysis = match_context.get("opp_analysis")
    opp_section = ""
    if opp_analysis:
        opp_section = f"""
Real Opposition Data:
Form (last 5): {opp_analysis['form_string']}
Goals scored: {opp_analysis['goals_scored']} | Conceded: {opp_analysis['goals_conceded']}
Attacking strength: {opp_analysis['attacking_strength']}
Defensive strength: {opp_analysis['defensive_strength']}
Recent matches:
{chr(10).join(opp_analysis['recent_matches'])}
"""

    # build the prompt from match context
    context_prompt = f"""
Analyse this match and generate a tactical report:

Team: {match_context['team']}
Opposition: {match_context['opposition']}
League: {match_context['league']}
Venue: {match_context['venue']}

Starting 11:
{players_text}

{opp_section}

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
    

def run_analyst():
    print("="*50)
    print("⚽ FOOTBALL TACTICAL ANALYST")
    print("Powered by AI — Built for Coaches")
    print("="*50)
    
    match_context = get_coach_input()
    report = generate_report(match_context)
    
    print("\n" + "="*50)
    print("TACTICAL REPORT")
    print("="*50)
    print(report)
    
    # save to file
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"tactical_report_{match_context['team']}_vs_{match_context['opposition']}_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"TACTICAL REPORT\n")
        f.write(f"{match_context['team']} vs {match_context['opposition']}\n")
        f.write(f"Generated: {timestamp}\n")
        f.write("="*50 + "\n\n")
        f.write(report)
    
    print(f"\n✅ Report saved to {filename}")


def display_formation(players):
    """Shows players arranged by position on a pitch grid"""
    pos_groups = {
        "GK": [], "LB": [], "CB": [], "RB": [],
        "DMF": [], "LMF": [], "CMF": [], "RMF": [],
        "AMF": [], "LWF": [], "RWF": [],
        "CF": [], "ST": []
    }
    for p in players:
        pos = p["position"]
        if pos in pos_groups and p["name"]:
            condition_icon = "🟢" if p["condition"] == "Fit" else "🟡" if p["condition"] == "Fatigued" else "🔴"
            pos_groups[pos].append(f"{condition_icon}{p['name']}")

    rows = [
        ["LWF", "CF", "ST", "RWF"],
        ["AMF"],
        ["LMF", "CMF", "RMF"],
        ["DMF"],
        ["LB", "CB", "RB"],
        ["GK"]
    ]

    pitch_style = """
    <div style='background: linear-gradient(#1a5c1a, #2d8b2d);
                padding: 20px; border-radius: 10px;
                border: 3px solid white; text-align: center;'>
    """
    for row in rows:
        pitch_style += "<div style='display:flex; justify-content:center; margin:10px 0;'>"
        for pos in row:
            players_in_pos = pos_groups.get(pos, [])
            for player in players_in_pos:
                pitch_style += f"""
                <div style='background:rgba(255,255,255,0.2);
                            border:2px solid white; border-radius:50%;
                            padding:8px 12px; margin:0 10px;
                            color:white; font-size:12px; font-weight:bold;'>
                    {pos}<br>{player}
                </div>"""
        pitch_style += "</div>"
    pitch_style += "</div>"
    st.markdown(pitch_style, unsafe_allow_html=True)


def get_weather_icon(report):
    """Returns weather emoji based on report content"""
    report_lower = report.lower()
    if "rain" in report_lower: return "🌧️ Rainy"
    if "sunny" in report_lower or "clear" in report_lower: return "☀️ Sunny"
    if "cloud" in report_lower: return "⛅ Cloudy"
    if "wind" in report_lower: return "💨 Windy"
    if "snow" in report_lower: return "❄️ Snowy"
    return "🌤️ Mild"


def extract_section(report, keyword):
    """Extracts a section from the report based on a keyword"""
    lines = report.split("\n")
    capturing = False
    section_lines = []

    for line in lines:
        if keyword.lower() in line.lower() and any(
            marker in line for marker in ["#", "1.", "2.", "3.", "4.", "5."]):
            capturing = True
            section_lines.append(line)
            continue

        if capturing:
            # stop at next section header
            if any(marker in line for marker in ["# ", "## ", "### "]) and line != section_lines[0]:
                break
            if any(f"{n}." in line for n in range(1, 6)) and line not in section_lines[:1]:
                if any(keyword2 in line.lower() for keyword2 in
                       ["squad", "weather", "opposition", "formation", "match", "outcome"]):
                    break
            section_lines.append(line)

    return "\n".join(section_lines) if section_lines else None


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

def parse_formations(text):
    """Parse Claude's formation text into 3 separate formation dictionaries"""
    formations = []
    sections = text.split("FORMATION ")
    
    for section in sections[1:]:
        lines = section.strip().split("\n")
        formation = {
            "number": lines[0].strip(":").strip(),
            "name": "",
            "style": "",
            "best_used": "",
            "starting_11": [],
            "tactics": []
        }
        
        current_section = None
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Name:"):
                formation["name"] = line.replace("Name:", "").strip()
            elif line.startswith("Style:"):
                formation["style"] = line.replace("Style:", "").strip()
            elif line.startswith("Best Used When:"):
                formation["best_used"] = line.replace("Best Used When:", "").strip()
            elif "Starting 11" in line:
                current_section = "starting_11"
            elif "Key Tactics" in line:
                current_section = "tactics"
            elif current_section == "starting_11":
                # capture any line with a colon or dash — likely a player entry
                if ":" in line or "-" in line:
                    formation["starting_11"].append(line)
            elif current_section == "tactics":
                if line.startswith("-"):
                    formation["tactics"].append(line.replace("-", "").strip())
        
        if formation["name"]:
            formations.append(formation)
    
    return formations 


# ========== STREAMLIT UI ============

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="Football Tactical Analyst",
    page_icon="⚽",
    layout="wide"
)

# Sidebar navigation
st.sidebar.title("⚽ Tactical Analyst")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["New Report", "Squad Manager", "View Reports", "Compare Reports"]
)

# Main Title
st.title("⚽ Football Tactical Analyst")
st.markdown("*AI-powered tactical analysis for coaches*")
st.markdown("---")

# Page routing
if page == "New Report":
    st.header("📋 Match Briefing")
    st.markdown("Fill in the details below to generate your tactical report.")

    #---- Check if formation was pre-selected from Squad Manager ------
    if "selected_formation" in st.session_state:
        formation = st.session_state["selected_formation"]
        st.success(f"✅ Formation pre-loaded: {formation['name']} — {formation['style']}")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Starting 11 from Squad Manager:**")
            for player in formation["starting_11"]:
                st.markdown(f"• {player}")
        with col2:
            if st.button("❌ Clear Formation", key="clear_formation"):
                del st.session_state["selected_formation"]
                st.rerun()
        
        st.markdown("---")

    # ---- Section 1: Match Details ----
    st.subheader("🏟️ Match Details")
    col1, col2 = st.columns(2)
    with col1:
        team = st.text_input("Your Club Name", placeholder="e.g. Arsenal")
        league = st.text_input("League / Competition", placeholder="e.g. Premier League")
    with col2:
        opposition = st.text_input("Opposition Team", placeholder="e.g. Chelsea")
        venue = st.text_input("Match Venue City", placeholder="e.g. London")

    st.markdown("---")

    # pre-fill players from selected formation if available
    pre_filled = []   # ← list, not dict
    if "selected_formation" in st.session_state:
        formation = st.session_state["selected_formation"]

        valid_positions = ["GK","CB","LB","RB","DMF","CMF",    # ← add here
                       "AMF","LMF","RMF","LWF","RWF","CF","ST"]

        for line in formation["starting_11"]:
            if ":" in line:
                parts = line.split(":", 1)   # ← split on first colon only
                pos = parts[0].strip()
                
                if pos in valid_positions and len(parts) > 1:   # ← validate position
                    rest = parts[1].split("-")[0].strip()
                    pre_filled.append({"name": rest, "position": pos})

    # ---- Section 2: Startin 11 ----
    st.subheader("👥 Starting 11")

    positions = ["GK", "CB", "LB", "RB", "DMF", "CMF", "AMF",
                 "LMF", "RMF", "LWF", "RWF", "CF", "ST"]
    conditions = ["Fit", "Fatigued", "Injured", "Returning from injury","Suspended","Private issues"]

    players = []
    for i in range(11):
        col1, col2, col3 = st.columns([3, 2, 2])

        # find pre-filled name for this position slot
        default_name = ""
        default_pos_idx = 0
        if i < len(pre_filled):
            default_name = pre_filled[i]["name"]
            pos = pre_filled[i]["position"]
            if pos in positions:
                default_pos_idx = positions.index(pos)

        with col1:
            name = st.text_input(f"Player {i+1}",
                                value=default_name,
                                placeholder="Player name",
                                key=f"nr_name_{i}")
        with col2:
            position = st.selectbox("Position", positions,
                                    index=default_pos_idx,
                                    key=f"nr_pos_{i}")
        with col3:
            condition = st.selectbox("Condition", conditions,
                                    key=f"nr_cond_{i}")

        players.append({
            "name": name,
            "position": position,
            "condition": condition
        })

    st.markdown("---")

    # ---- Section 3: Opposition ---
    st.subheader("🎯 Opposition Analysis")

    # ─── Live opposition search ───
    st.markdown("**Search Opposition Team (optional)**")
    opp_col1, opp_col2 = st.columns([3, 1])
    with opp_col1:
        opp_search = st.text_input(
            "Search team name",
            placeholder="e.g. Chelsea, Real Madrid...",
            key="nr_opp_search"
        )
    with opp_col2:
        opp_search_btn = st.button("Search", key="nr_opp_search_btn")

    if opp_search_btn and opp_search:
        with st.spinner(f"Searching for {opp_search}..."):
            team_results = search_teams(opp_search)
        st.session_state["opp_team_results"] = team_results

    if "opp_team_results" in st.session_state:
        teams = st.session_state["opp_team_results"]
        if not teams:
            st.warning("No teams found.")
        else:
            for i, team in enumerate(teams):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{team['name']}**")
                with col2:
                    st.caption(team['country'])
                with col3:
                    if st.button("Analyse", key=f"nr_analyse_{i}"):
                        with st.spinner(f"Fetching {team['name']} data..."):
                            analysis = get_opposition_analysis(
                                team["id"], team["name"]
                            )
                        if analysis:
                            st.session_state["opp_analysis"] = analysis
                            del st.session_state["opp_team_results"]
                            st.rerun()

    # ─── Show opposition analysis if fetched ───
    if "opp_analysis" in st.session_state:
        opp = st.session_state["opp_analysis"]
        st.success(f"✅ Opposition data loaded: {opp['team']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Form", opp["form_string"])
            st.caption(f"W{opp['wins']} D{opp['draws']} L{opp['losses']}")
        with col2:
            st.metric("Attacking", opp["attacking_strength"])
            st.caption(f"{opp['goals_scored']} goals in 5 matches")
        with col3:
            st.metric("Defensive", opp["defensive_strength"])
            st.caption(f"{opp['goals_conceded']} conceded in 5 matches")

        st.markdown("**Recent Matches:**")
        for match in opp["recent_matches"]:
            result = opp["form"][opp["recent_matches"].index(match)]
            icon = "✅" if result == "W" else "⚖️" if result == "D" else "❌"
            st.caption(f"{icon} {match}")

        if st.button("❌ Clear Opposition Data", key="nr_clear_opp"):
            del st.session_state["opp_analysis"]
            st.rerun()

    st.markdown("---")

    # ─── Manual opposition fields ───
    col1, col2 = st.columns(2)
    with col1:
        opp_formations = ["Unknown","4-3-3","4-4-2","3-5-2",
                        "4-2-3-1","5-3-2","4-1-4-1","3-4-3"]
        opp_formation = st.selectbox("Known Opposition Formation",
                                    opp_formations)
    with col2:
        opp_notes = st.text_area(
            "Additional Notes",
            placeholder="Any known opposition strengths, key players...",
            height=100
        )
        
        st.markdown("---")

        fatigued = [p["name"] for p in players if p["condition"] != "Fit" and p["name"]]
        if fatigued:
            st.warning(f"⚠️ Players not at full fitness: {', '.join(fatigued)}")
        
        #---- Generate Button ----
        if st.button("⚽ Generate Tactical Report", type="primary", key="generate_formations_btn"):
            # validate inputs
            if not team or not opposition or not venue:
                st.error("Please fill in Club Name, Opposition, and Venue before generating.")
            elif not any(p["name"] for p in players):
                st.error("Please enter at least one player name.")
            else:
                # build match context
                match_context = {
                    "team": team,
                    "opposition": opposition,
                    "venue": venue,
                    "league": league,
                    "players": players,
                    "opp_formation": opp_formation,
                    "opp_notes": opp_notes,
                    "opp_analysis": st.session_state.get("opp_analysis", None)
                }

                with st.status("⚽ Generating tactical report...", expanded=True) as status:
                    st.write("☁️ Checking weather conditions...")
                    st.write("📚 Searching tactical knowledge base...")
                    st.write("🧠 Claude is analysing your squad...")
                    try:
                        # try API first
                        api_response = requests.post(
                            "http://localhost:8000/analyse",
                            json={
                                "team": match_context["team"],
                                "opposition": match_context["opposition"],
                                "venue": match_context["venue"],
                                "league": match_context["league"],
                                "players": match_context["players"],
                                "opp_formation": match_context["opp_formation"],
                                "opp_notes": match_context.get("opp_notes", ""),
                            },
                            timeout=5
                        )
                        if api_response.status_code == 200:
                            report = api_response.json()["report"]
                        else:
                            report = generate_report(match_context)

                    except:
                        # fall back to direct Claude call
                        report = generate_report(match_context)

                    st.session_state["report"] = report
                    st.session_state["match_context"] = match_context
                    st.session_state["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    status.update(label="✅ Report ready!", state="complete")

    # display report if it exits
    if "report" in st.session_state:
        st.markdown("---")
        st.subheader("📊 Tactical Report")
        st.caption(f"Generated: {st.session_state['timestamp']}")
        st.markdown(st.session_state["report"])

        # formation display
        st.markdown("---")
        st.subheader("🟢 Formation")
        display_formation(st.session_state["match_context"]["players"])

        # weather icon
        weather_icon = get_weather_icon(st.session_state["report"])
        st.markdown(f"### Weather: {weather_icon}")

        # save button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Report", key="nr_save_btn"):
                ctx = st.session_state["match_context"]
                save_report(
                    coach_id=coach_id,
                    team=ctx["team"],
                    opposition=ctx["opposition"],
                    league=ctx["league"],
                    venue=ctx["venue"],
                    players=ctx["players"],
                    report=st.session_state["report"],
                    opp_formation=ctx["opp_formation"]
                )
                st.success("✅ Report saved to database!")
        with col2:
            st.download_button(
                label="📥 Download Report",
                data=st.session_state["report"],
                file_name=f"tactical_report_{team}_vs_{opposition}.txt",
                mime="text/plain"
            )

elif page == "Squad Manager":
    st.header("👥 Squad Manager")

    POSITION_ABILITIES = {
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

    form_ratings = ["Poor", "Average", "Good", "Excellent"]
    ability_ratings = ["Poor", "Average", "Good", "Excellent"]
    positions = list(POSITION_ABILITIES.keys())

    squad = get_squad(coach_id)   

    tab1, tab2, tab3 = st.tabs(["🔍 Search Real Players", "➕ Manage Squad", "⚽ Generate Formations"])

    #----- TAB1: Search Real Players -----
    with tab1:
        st.subheader("🔍 Search Real Players")

        # clear search if importing
        if "importing_player" in st.session_state:
            if "search_results" in st.session_state:
                del st.session_state["search_results"]

        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            player_search = st.text_input(
                "Search by player name",
                placeholder="e.g. Bellingham, Salah, Mbappe...",
                key="sm_player_search"
            )
        with search_col2:
            search_btn = st.button("Search", key="sm_search_btn")

        if search_btn and player_search:
            with st.spinner(f"Searching for {player_search}..."):
                results = search_players(player_search)
            st.session_state["search_results"] = results

        if "search_results" in st.session_state:
            results = st.session_state["search_results"]
            if not results:
                st.warning("No players found. Try a different name.")
            else:
                st.markdown(f"**{len(results)} players found:**")
                for i, player in enumerate(results[:5]):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        st.markdown(f"**{player['name']}**")
                        st.caption(player['country'])
                    with col2:
                        st.caption(player['team'])
                    with col3:
                        st.caption(f"Position: {player['position']}")
                    with col4:
                        if st.button("Import", key=f"sm_import_{i}"):
                            st.session_state["importing_player"] = player
                            del st.session_state["search_results"]
                            st.rerun()

    #----- TAB2: Add Players -----
    with tab2:
        st.subheader("Add New Player")
        col1, col2, col3 = st.columns(3)
        with col1:
            p_name = st.text_input("Player Name",
                                   placeholder="e.g. Vinicius Jr",
                                   key="sm_player_name")
        with col2:
            p_position = st.selectbox("Position", positions,
                                      key="sm_position")
        with col3:
            p_form = st.selectbox("Current Form", form_ratings,
                                  index=2, key="sm_form")

        st.markdown("**Ability Ratings** *(position-specific)*")
        relevant     = POSITION_ABILITIES[p_position]
        ability_cols = st.columns(len(relevant))
        abilities    = {}
        for idx, ability in enumerate(relevant):
            with ability_cols[idx]:
                abilities[ability] = st.selectbox(
                    ability, ability_ratings,
                    index=2,
                    key=f"sm_ab_{p_position}_{ability}"
                )

        if st.button("➕ Add Player", type="primary", key="sm_add_btn"):
            if not p_name:
                st.error("Please enter a player name.")
            elif any(p["name"].lower() == p_name.lower() for p in squad):
                st.warning(f"{p_name} is already in the squad.")
            else:
                success = save_player(coach_id, p_name, p_position, p_form, abilities)
                if success:
                    st.success(f"✅ {p_name} added to database!")
                    st.rerun()
                else:
                    st.warning(f"{p_name} already exists in the squad.")

        st.markdown("---")
        st.subheader(f"Current Squad ({len(squad)} players)")

        if not squad:
            st.info("No players added yet.")
        else:
            pos_order = ["GK","CB","LB","RB","DMF","CMF",
                         "LMF","RMF","AMF","LWF","RWF","CF","ST"]
            form_icon = {
                "Poor":"🔴","Average":"🟡",
                "Good":"🟢","Excellent":"⭐"
            }
            for pos in pos_order:
                pos_players = [p for p in squad if p["position"] == pos]
                if pos_players:
                    st.markdown(f"**{pos}**")
                    for p in pos_players:
                        c1, c2, c3, c4 = st.columns([3, 2, 3, 1])
                        with c1:
                            st.markdown(
                                f"{form_icon[p['form']]} **{p['name']}**"
                            )
                        with c2:
                            st.caption(f"Form: {p['form']}")
                        with c3:
                            st.caption(" | ".join(
                                f"{k}: {v}"
                                for k, v in p["abilities"].items()
                            ))
                        with c4:
                            if st.button("🗑️", key=f"sm_del_{p['name']}"):
                                delete_player(coach_id, p["name"])
                                st.rerun()

    with tab3:
        st.subheader("Generate Formations")

        if len(squad) < 11:
            st.warning(
                f"Need at least 11 players. "
                f"Current squad: {len(squad)}"
            )
        else:
            st.markdown(f"**Squad loaded: {len(squad)} players**")
            st.markdown(
                "Claude will analyse your squad "
                "and suggest 3 optimal formations."
            )

            if st.button("⚽ Generate 3 Formations",
                         type="primary",
                         key="sm_generate_btn"):
                with st.spinner("Analysing squad..."):
                    raw = generate_formations(squad)
                    st.session_state["sm_raw_formations"] = raw
                    st.session_state["sm_parsed"] = parse_formations(raw)

            if "sm_raw_formations" in st.session_state:
                parsed = st.session_state.get("sm_parsed", [])

                if parsed:
                    for i, formation in enumerate(parsed):
                        with st.expander(
                            f"Formation {i+1}: "
                            f"{formation['name']} — "
                            f"{formation['style']}",
                            expanded=(i == 0)
                        ):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(
                                    f"**Formation:** {formation['name']}"
                                )
                                st.markdown(
                                    f"**Style:** {formation['style']}"
                                )
                                st.markdown(
                                    f"**Best used when:** "
                                    f"{formation['best_used']}"
                                )
                                st.markdown("**Key Tactics:**")
                                for tactic in formation["tactics"]:
                                    st.markdown(f"- {tactic}")
                            with col2:
                                st.markdown("**Starting 11:**")
                                for player in formation["starting_11"]:
                                    st.markdown(f"• {player}")

                            if st.button(
                                "✅ Use This Formation",
                                key=f"sm_use_{i}",
                                type="primary"
                            ):
                                st.session_state["selected_formation"] = (
                                    formation
                                )
                                st.success(
                                    "Formation selected! "
                                    "Go to New Report."
                                )
                else:
                    st.markdown(
                        st.session_state["sm_raw_formations"]
                    )

    # ─── OUTSIDE tabs — import confirmation ───
    if "importing_player" in st.session_state:
        p = st.session_state["importing_player"]
        st.markdown("---")
        st.subheader(f"📥 Importing {p['name']}")
        st.caption(f"{p['team']} | {p['country']}")

        mapped_pos = map_api_position(p["position"])

        col1, col2 = st.columns(2)
        with col1:
            import_pos = st.selectbox(
                "Confirm Position", positions,
                index=positions.index(mapped_pos) if mapped_pos in positions else 0,
                key="sm_import_pos"
            )
        with col2:
            import_form = st.selectbox(
                "Current Form", form_ratings,
                index=2, key="sm_import_form"
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Import", key="sm_confirm_import", type="primary"):
                with st.spinner("Fetching player abilities..."):
                    abilities = get_player_abilities(p["id"], import_pos)

                if abilities:
                    success = save_player(
                        coach_id, p["name"],
                        import_pos, import_form, abilities
                    )
                    if success:
                        st.success(f"✅ {p['name']} imported with real stats!")
                        del st.session_state["importing_player"]
                        st.rerun()
                    else:
                        st.warning(f"{p['name']} already in squad.")
                        del st.session_state["importing_player"]
                else:
                    st.warning("Couldn't fetch abilities — add manually.")
                    del st.session_state["importing_player"]
        with col2:
            if st.button("❌ Cancel", key="sm_cancel_import"):
                del st.session_state["importing_player"]
                st.rerun()

elif page == "View Reports":
    st.header("📁 Saved Reports")
    # Search bar
    search_query = st.text_input("🔍 Search reports", 
                                placeholder="Search by team or opposition...",
                                key="report_search")
    
    if search_query:
        reports = search_reports(coach_id, search_query)
    else:
        reports = get_all_reports(coach_id)


    if not reports:
        st.info("No reports saved yet. Generate your first tactical analysis.")
        st.info("Click 'New Report' in the sidebar to get started.") 
    else:
        st.markdown(f"**{len(reports)} report(s) saved.**")
        st.markdown("---")

        # check if viewing a specific report
        if "viewing_report" in st.session_state:
            report_data = st.session_state["viewing_report"]

            # back button
            if st.button("⬅️ Back to Reports"):
                del st.session_state["viewing_report"]
                st.rerun()

            st.subheader(f"⚽ {report_data['team']} vs {report_data['opposition']}")
            st.caption(f"{report_data['league']} | {report_data['venue']} | {report_data['timestamp']}")
            st.markdown("---")
            st.markdown(report_data["report"])
            st.markdown("---")
            display_formation(report_data["players"])

            st.download_button(
                label="📥 Download Report",
                data=report_data["report"],
                file_name=f"report_{report_data['team']}_vs_{report_data['opposition']}.txt",
                mime="text/plain"
            )

        else:
            # show summary cards
            for i, report in enumerate(reversed(reports)):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"### ⚽ {report['team']} vs {report['opposition']}")
                        st.caption(f"{report['league']} | {report['venue']}")
                    with col2:
                        st.markdown(f"**Formation:** {report['opp_formation']}")
                        st.caption(f"📅 {report['timestamp']}")
                    with col3:
                        if st.button("View Report", key=f"view_{i}"):
                            st.session_state["viewing_report"] = report
                            st.rerun()
                    st.markdown("---")

elif page == "Compare Reports":
    st.header("⚖️ Compare Reports")

    if not os.path.exists("reports.json"):
        st.info("No rports saved yet. Generate at least two reports to compare.")
    else:
        with open("reports.json", "r", encoding="utf-8") as f:
            reports =json.load(f)

        if len(reports) < 2:
            st.info("You need at least two saved reports to compare.")
        else:
            # build labels for dropdowns#
            labels = [
                f"{r['team']} vs {r['opposition']} ({r['timestamp']})"
                for r in reports
            ]

            st.markdown("Select two reports to compare side by side.")
            col1, col2 = st.columns(2)
            with col1:
                report1_idx = st.selectbox("Report 1", range(len(labels)),
                                           format_func=lambda x: labels[x],
                                           key="compare_1")
            with col2:
                report2_idx = st.selectbox("Report 2", range(len(labels)),
                                           format_func=lambda x: labels[x],
                                           key="compare_2",
                                           index=min(1, len(reports)-1))

            if st.button("⚖️ Compare", type="primary"):
                if report1_idx == report2_idx:
                    st.error("Please select two different reports.")
                else:
                    r1 = reports[report1_idx]
                    r2 = reports[report2_idx]

                    st.markdown("---")

                    # headers
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"⚽ {r1['team']} vs {r1['opposition']}")
                        st.caption(f"{r1['league']} | {r1['timestamp']}")
                    with col2:
                        st.subheader(f"⚽ {r2['team']} vs {r2['opposition']}")
                        st.caption(f"{r2['league']} | {r2['timestamp']}")

                    st.markdown("---")

                    # ── Comparison 1: Opposition Strengths & Weaknesses ──
                    st.markdown("### 🎯 Opposition Strengths & Weaknesses")
                    col1, col2 = st.columns(2)
                    with col1:
                        opp_section1 = extract_section(r1["report"], "Opposition")
                        st.markdown(opp_section1 if opp_section1 else "*Not found in report*")
                    with col2:
                        opp_section2 = extract_section(r2["report"], "Opposition")
                        st.markdown(opp_section2 if opp_section2 else "*Not found in report*")

                    st.markdown("---")

                    # ── Comparison 2: Team Flaws ──
                    st.markdown("### ⚠️ Team Condition & Flaws")
                    col1, col2 = st.columns(2)
                    with col1:
                        squad_section1 = extract_section(r1["report"], "Squad")
                        st.markdown(squad_section1 if squad_section1 else "*Not found in report*")
                    with col2:
                        squad_section2 = extract_section(r2["report"], "Squad")
                        st.markdown(squad_section2 if squad_section2 else "*Not found in report*")

                    st.markdown("---")

                    # ── Comparison 3: Formation & Tactics based on Weather ──
                    st.markdown("### 🌤️ Recommended Formation & Tactics")
                    col1, col2 = st.columns(2)
                    with col1:
                        tactics1 = extract_section(r1["report"], "Formation")
                        weather1 = get_weather_icon(r1["report"])
                        st.markdown(f"**Weather:** {weather1}")
                        st.markdown(tactics1 if tactics1 else "*Not found in report*")
                    with col2:
                        tactics2 = extract_section(r2["report"], "Formation")
                        weather2 = get_weather_icon(r2["report"])
                        st.markdown(f"**Weather:** {weather2}")
                        st.markdown(tactics2 if tactics2 else "*Not found in report*")

                    st.markdown("---")

                    # ── Formations side by side ──
                    st.markdown("### 🟢 Formations")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"{r1['team']} vs {r1['opposition']}")
                        display_formation(r1["players"])
                    with col2:
                        st.caption(f"{r2['team']} vs {r2['opposition']}")
                        display_formation(r2["players"])
















































