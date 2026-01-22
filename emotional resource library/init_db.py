import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emotion TEXT,
    intensity TEXT,
    category TEXT,
    content TEXT
)
""")

data = [
    ("anxious", "high", "breathing", "Box Breathing (4-4-4-4)"),
    ("anxious", "high", "meditation", "Emergency Calm Meditation (5 min)"),
    ("anxious", "high", "coping", "Cold water splash"),

    ("sad", "medium", "breathing", "Slow Resonance Breathing"),
    ("sad", "medium", "meditation", "Self-Compassion Meditation"),
    ("sad", "medium", "coping", "Take a short walk"),

    ("angry", "high", "breathing", "Extended Exhale Breathing"),
    ("angry", "high", "meditation", "Observe the Emotion Meditation"),
    ("angry", "high", "coping", "Physical movement"),

    ("calm", "low", "breathing", "Mindful Natural Breathing"),
    ("calm", "low", "meditation", "Focus Meditation"),
    ("calm", "low", "coping", "Set daily intention")
]

cur.executemany("""
INSERT INTO resources (emotion, intensity, category, content)
VALUES (?, ?, ?, ?)
""", data)

conn.commit()
conn.close()

print("✅ Database initialized successfully")
