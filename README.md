# ⚽ Football Tactical Analyst v2

> AI-powered tactical analysis platform for football coaches — built with Python, Claude AI, and Streamlit

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-red?style=flat)](https://football-tactical-analyst-39lecabfsgfatuwaat2cce.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat&logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=flat&logo=streamlit)](https://streamlit.io)

---

## What This Does

A full-stack AI application that gives football coaches professional-grade tactical analysis in seconds.

A coach inputs their squad, the opposition, and match details. The system:
1. Pulls **live weather** at the match venue
2. Fetches **real opposition form** — last 5 results, goals scored/conceded
3. Searches a **tactical knowledge base** using RAG
4. Generates a **5-section tactical report** via Claude AI
5. Displays the **recommended formation on a pitch canvas**

---

## Features

### 🔐 Multi-Coach Authentication
- Individual coach accounts with bcrypt password hashing
- Each coach sees only their own reports and squad
- Register, login, logout — full session management

### 👥 Squad Manager
- Add players manually with position-specific ability ratings
- **Search real players** by name via SportAPI
- Import real player stats — automatically converted to ability ratings
- Generate 3 AI formation recommendations from your squad
- Select a formation — pre-fills the New Report form

### 📋 New Report
- 11-player starting lineup with position and condition
- **Live opposition search** — real match form, goals, attacking/defensive strength
- AI agent loop: weather → knowledge base → tactical report
- Formation displayed on green HTML pitch with condition indicators
- Save and download reports

### 📁 View Reports
- Summary cards for all saved reports
- Full report view with formation display
- Search reports by team or opposition name

### ⚖️ Compare Reports
- Side-by-side comparison of two saved reports
- Opposition strengths, team flaws, formation comparison

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Backend API | FastAPI + uvicorn |
| AI Model | Anthropic Claude (claude-haiku) |
| Knowledge Retrieval | RAG — sentence-transformers + cosine similarity |
| Football Data | SportAPI via RapidAPI |
| Weather Data | wttr.in |
| Database | SQLite with bcrypt auth |
| Deployment | Streamlit Community Cloud |

---

## Architecture

```
Coach (Browser)
      ↓
Streamlit (app.py)          ← UI layer
      ↓
FastAPI (api.py)            ← API layer (optional)
      ↓
Agent Loop                  ← AI reasoning
  ├── get_weather()         ← live weather
  ├── search_tactics()      ← RAG knowledge base
  └── Claude generates      ← tactical report
      
football_api.py             ← external football data
database.py                 ← SQLite operations
```

---

## Local Setup

```bash
# Clone the repository
git clone https://github.com/Wahab16-blip/football-tactical-analyst-v2.git
cd football-tactical-analyst-v2

# Install dependencies
pip install -r requirements.txt

# Create .env file
ANTHROPIC_API_KEY=your-key-here
FOOTBALL_API_KEY=your-rapidapi-key

# Initialise database
python database.py

# Run the app
streamlit run app.py
```

---

## Project Structure

```
├── app.py              # Streamlit UI — all pages
├── api.py              # FastAPI backend endpoints
├── database.py         # SQLite — all DB operations
├── football_api.py     # SportAPI integration
├── requirements.txt    # Dependencies
└── .streamlit/
    └── secrets.toml    # API keys (gitignored)
```

---

## What I Learned Building This

- Designing multi-user systems with proper data isolation
- Building RAG pipelines from scratch without frameworks
- Agent loops with tool routing and self-correction
- bcrypt authentication and session management
- Connecting multiple external APIs in one system
- Deploying full-stack Python apps to the cloud
- Git security — preventing API key exposure

---

## Roadmap

- [ ] Opposition player analysis (key threats by position)
- [ ] Historical head-to-head records
- [ ] PDF report export
- [ ] PostgreSQL migration for production scale
- [ ] Mobile app via React Native

---

**Built by Wahab · CS Student · University of Sunderland · 2026**
