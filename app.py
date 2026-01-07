import tkinter as tk
from tkinter import ttk
import sqlite3

# DATABASE FUNCTION
def fetch_resources(emotion, intensity):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT category, content
    FROM resources
    WHERE emotion=? AND intensity=?
    """, (emotion, intensity))

    rows = cur.fetchall()
    conn.close()

    result = {"breathing": [], "meditation": [], "coping": []}
    for category, content in rows:
        result[category].append(content)

    insight = f"You are feeling '{emotion}' ({intensity}). Short focused practices will help right now."

    return result, insight


# BUTTON ACTION
def show_resources():
    emotion = emotion_var.get()
    intensity = intensity_var.get()

    resources, insight = fetch_resources(emotion, intensity)

    output.delete("1.0", tk.END)

    output.insert(tk.END, "INSIGHT\n", "title")
    output.insert(tk.END, insight + "\n\n")

    output.insert(tk.END, "BREATHING EXERCISES\n", "title")
    for item in resources["breathing"]:
        output.insert(tk.END, f"• {item}\n")

    output.insert(tk.END, "\nMEDITATION GUIDES\n", "title")
    for item in resources["meditation"]:
        output.insert(tk.END, f"• {item}\n")

    output.insert(tk.END, "\nCOPING STRATEGIES\n", "title")
    for item in resources["coping"]:
        output.insert(tk.END, f"• {item}\n")


# TKINTER UI
root = tk.Tk()
root.title("Emotional Health Resource Library")
root.geometry("650x550")
root.configure(bg="#f2f4f7")

# Title
tk.Label(
    root,
    text="🧠 Emotional Health Resource Finder",
    font=("Arial", 18, "bold"),
    bg="#f2f4f7"
).pack(pady=10)

# Dropdowns
frame = tk.Frame(root, bg="#f2f4f7")
frame.pack(pady=10)

emotion_var = tk.StringVar(value="anxious")
intensity_var = tk.StringVar(value="high")

tk.Label(frame, text="Emotion:", bg="#f2f4f7").grid(row=0, column=0, padx=10)
emotion_menu = ttk.Combobox(
    frame,
    textvariable=emotion_var,
    values=["anxious", "sad", "angry", "calm"],
    state="readonly"
)
emotion_menu.grid(row=0, column=1)

tk.Label(frame, text="Intensity:", bg="#f2f4f7").grid(row=1, column=0, padx=10)
intensity_menu = ttk.Combobox(
    frame,
    textvariable=intensity_var,
    values=["low", "medium", "high"],
    state="readonly"
)
intensity_menu.grid(row=1, column=1)

# Button
tk.Button(
    root,
    text="Get Personalized Resources",
    command=show_resources,
    bg="#4a90e2",
    fg="white",
    font=("Arial", 12),
    padx=10
).pack(pady=10)

# Output Box
output = tk.Text(root, height=18, width=75)
output.pack(pady=10)

output.tag_config("title", font=("Arial", 11, "bold"))

root.mainloop()
