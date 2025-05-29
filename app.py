from flask import Flask, request, render_template, jsonify
import sqlite3
import os
# from dotenv import load_dotenv
import google.generativeai as genai
import json
# Load API Key
# load_dotenv()
# API_KEY = os.getenv("AIzaSyByYgdkIFo7WhE_Lo1bq7Zotzv34wi2X9o")
genai.configure(api_key='AIzaSyBw2E86j0PXnF0kslOMXj7Zsm9MIHJYadE')
model = genai.GenerativeModel("models/gemini-1.5-flash")
# Init Flask App
app = Flask(__name__)

# Initialize SQLite DB
def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                raw_data TEXT,
                narrative TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

def detect_anomalies(data):
    try:
        overs = data["innings"][0]["overs"]
    except (KeyError, IndexError):
        return []

    runs = []
    for over in overs:
        over_total = sum(ball["runs"]["total"] for ball in over["deliveries"] if "runs" in ball)
        runs.append(over_total)

    anomalies = []
    for i in range(1, len(runs)):
        change = runs[i] - runs[i-1]
        if abs(change) >= 10:  # threshold for anomaly
            anomalies.append({
                "over": i,
                "change": change,
                "type": "spike" if change > 0 else "drop"
            })
    return anomalies

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate_report():
    data = request.json
    title = data.get("title")
    raw_data = data.get("data")
    try:
        parsed_data = json.loads(raw_data)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"})
    anomalies = detect_anomalies(parsed_data)
    anomaly_descriptions = "\n".join([f"Over {a['over']}: {'⬆️ Spike' if a['type'] == 'spike' else '⬇️ Drop'} of {abs(a['change'])} runs" for a in anomalies])
    # Prompt Gemini to generate narrative
    prompt = f"""Generate a clear, insightful business narrative from the following data: {raw_data} 
    Also comment on the trends and anomalies such as spikes or drops. Here are the detected anomalies: {anomaly_descriptions}"""
    response = model.generate_content(prompt)
    narrative = response.text

    # Store in DB
    with sqlite3.connect("database.db") as conn:
        conn.execute(
            "INSERT INTO reports (title, raw_data, narrative) VALUES (?, ?, ?)",
            (title, raw_data, narrative)
        )
    return jsonify({"narrative": narrative,"anomalies": anomalies})

@app.route('/history')
def history():
    with sqlite3.connect("database.db") as conn:
        reports = conn.execute("SELECT id, title, narrative, timestamp FROM reports ORDER BY timestamp DESC").fetchall()
    return jsonify([dict(zip(["id", "title", "narrative", "timestamp"], row)) for row in reports])

if __name__ == '__main__':
    init_db()
    # app.run(debug=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
