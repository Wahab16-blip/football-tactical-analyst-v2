BEFORE every git commit — run this check:
git diff --cached

Look for any lines starting with:
sk-ant    → Anthropic key
sk-        → OpenAI key  
gsk_       → Groq key

If you see any → stop, remove from .gitignore, 
                  unstage with git rm --cached

GOLDEN RULE:
→ API keys NEVER go in code files
→ API keys NEVER get committed
→ Always use .env + .gitignore
→ Always check .gitignore BEFORE git add .


SQLITE BASICS:
─────────────────────────────────────────
sqlite3.connect("file.db")  → open/create db
conn.row_factory = sqlite3.Row → rows as dicts
cursor.execute("SQL", (params,)) → run query
conn.commit() → save changes
conn.close()  → always close connection

SQL COMMANDS USED:
─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS → safe table creation
INSERT INTO table VALUES   → add a row
SELECT * FROM table        → get all rows
DELETE FROM table WHERE    → remove specific row
LIKE '%query%'             → partial text search

SAFETY RULES:
─────────────────────────────────────────
Always use ? placeholders — never f-strings in SQL
cursor.execute("SELECT * WHERE id=?", (id,))  ✅
cursor.execute(f"SELECT * WHERE id={id}")     ❌ SQL injection risk

json.dumps() → store lists/dicts as text in DB
json.loads() → restore lists/dicts when reading


BCRYPT PATTERN:
─────────────────────────────────────────
# Register — hash before saving
hashed = bcrypt.hashpw(
    password.encode("utf-8"),
    bcrypt.gensalt()
)
store hashed.decode("utf-8") in database

# Login — compare without decrypting
bcrypt.checkpw(
    typed.encode("utf-8"),
    stored_hash.encode("utf-8")
) → True or False

NEVER store plain text passwords
NEVER decrypt hashes — impossible by design

DATA ISOLATION PATTERN:
─────────────────────────────────────────
Every query filters by coach_id:
SELECT * FROM reports WHERE coach_id = ?

coach_id comes from:
st.session_state["coach"]["id"]

This ensures coaches never see each other's data

FOREIGN KEY:
─────────────────────────────────────────
FOREIGN KEY (coach_id) REFERENCES users(id)
→ links two tables together
→ coach_id in reports must exist in users.id
→ prevents orphaned data


































