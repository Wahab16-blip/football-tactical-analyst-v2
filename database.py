import sqlite3
import os
import json
from datetime import datetime

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

    # Reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports(
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            team        TEXT NOT NULL,
            opposition  TEXT NOT NULL,
            league      TEXT,
            venue       TEXT,
            players     TEXT,
            report      TEXT NOT NULL,
            opp_formation   TEXT,
            timestamp   TEXT NOT NULL       
        )
    """)

    # Squad table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS squad (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            position   TEXT NOT NULL,
            form       TEXT NOT NULL,
            abilities  TEXT NOT NULL
        )
   """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialised successfully")

# ---- Report functions ----
def save_report(team, opposition, league, venue, players, report, opp_formation):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports (team, opposition, league, venue, players, report, opp_formation, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
     """, (
        team, opposition, league, venue, 
        json.dumps(players),  # convert list to JSON string  
        report, opp_formation,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    conn.commit()
    conn.close()

def get_all_reports():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports ORDER BY timestamp DESC")
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
def save_player(name, position, form, abilities):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO squad (name, position, form, abilities)
            VALUES (?, ?, ?, ?)
        """, (name, position, form, json.dumps(abilities)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # player already exists (UNIQUE constraint)
    finally:
        conn.close()

def get_squad():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM squad ORDER BY position")
    rows = cursor.fetchall()
    conn.close()
    players = []
    for row in rows:
        p = dict(row)
        p["abilities"] = json.loads(p["abilities"])
        players.append(p)
    return players

def delete_player(name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM squad WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def search_reports(query):
    """Search reports by team or opposition name"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM reports 
        WHERE team LIKE ? OR opposition LIKE ?
        ORDER BY timestamp DESC
    """, (f"%{query}%", f"%{query}%"))
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























