import sqlite3
import os
import json
from datetime import datetime
import bcrypt

DATABASE = "tactical_analyst.db"

def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row   # returns rows as dictionaries
    return conn

def init_database():
    """Create tables if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL UNIQUE,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'coach',
            created_at  TEXT NOT NULL
        )
    """)

    # Reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports(
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            coach_id    INTEGER NOT NULL,
            team        TEXT NOT NULL,
            opposition  TEXT NOT NULL,
            league      TEXT,
            venue       TEXT,
            players     TEXT,
            report      TEXT NOT NULL,
            opp_formation   TEXT,
            timestamp   TEXT NOT NULL,
            FOREIGN KEY (coach_id)  REFERENCES users(id)            
        )
    """)

    # Squad table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS squad (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            coach_id   INTEGER NOT NULL,
            name       TEXT NOT NULL UNIQUE,
            position   TEXT NOT NULL,
            form       TEXT NOT NULL,
            abilities  TEXT NOT NULL,
            FOREIGN KEY (coach_id) REFERENCES user(id)
        )
   """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialised successfully")

def register_coach(username, password):
    """Register a new coach - returns True if success, False if username taken"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # hash the password before storing
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )
        cursor.execute(""" 
            INSERT INTO users (username, password, role, created_at)
            VALUES (?, ?, 'coach', ?)
        """, (
            username,
            hashed.decode("utf-8"),   # store as string
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()
        return True
    except sqlite3.Integrity:
        return False  # username already taken
    finally:
        conn.close()

def login_coach(username, password):
    """Check credentials - returns coach dict if valid, None if not"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None  # username not found
    
    coach = dict(row)
    password_matches = bcrypt.checkpw(
        password.encode("utf-8"),
        coach["password"].encode("utf-8")
    )

    if password_matches:
        return coach   # return full coach dict
    return None   # wrong password

def get_coach_by_id(coach_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (coach_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None 


# ---- Report functions ----
def save_report(coach_id, team, opposition, league, venue, players, report, opp_formation):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports (coach_id, team, opposition, league, venue, players, report, opp_formation, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
     """, (
        coach_id,
        team, opposition, league, venue, 
        json.dumps(players),  # convert list to JSON string  
        report, opp_formation,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    conn.commit()
    conn.close()

def get_all_reports(coach_id):
    """Get only THIS coach's reports"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE coach_id = ? ORDER BY timestamp DESC", (coach_id,))
    rows = cursor.fetchall()
    conn.close()

    reports = []
    for row in rows:
        r = dict(row)
        r["players"] = json.loads(r["players"]) # convert back to list
        reports.append(r)
    return reports

def get_report_by_id(report_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        r = dict(row)
        r["players"] = json.loads(r["players"])
        return r
    return None

def delete_report(report_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()

# --- Squad functions ---
def save_player(coach_id, name, position, form, abilities):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO squad (coach_id, name, position, form, abilities)
            VALUES (?, ?, ?, ?, ?)
        """, (coach_id, name, position, form, json.dumps(abilities)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # player already exists (UNIQUE constraint)
    finally:
        conn.close()

def get_squad(coach_id):
    """Get only THIS coach's squad"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM squad WHERE coach_id = ? ORDER BY position", (coach_id,))
    rows = cursor.fetchall()
    conn.close()
    players = []
    for row in rows:
        p = dict(row)
        p["abilities"] = json.loads(p["abilities"])
        players.append(p)
    return players

def delete_player(coach_id, name):
    """Only delete if it belongs to this coach"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM squad WHERE name = ? AND coach_id = ?", (name, coach_id))
    conn.commit()
    conn.close()

def search_reports(coach_id, query):
    """Search reports by team or opposition name"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM reports 
        WHERE coach_id = ?
        AND (team LIKE ? OR opposition LIKE ?)
        ORDER BY timestamp DESC
    """, (coach_id, f"%{query}%", f"%{query}%"))
    rows = cursor.fetchall()
    conn.close()
    reports = []
    for row in rows:
        r = dict(row)
        r["players"] = json.loads(r["players"])
        reports.append(r)
    return reports

if __name__ == "__main__":
    init_database()























