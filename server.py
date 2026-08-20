from flask import Flask, request, jsonify, send_from_directory
from google import genai
import os

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY)

SYSTEM_PROMPT = "Ты полезный AI-ассистент. Отвечай на русском языке, если пользователь пишет на русском. Будь дружелюбным и лаконичным."


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "Нет сообщений"}), 400

    try:
        # Build contents for Gemini
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config={"system_instruction": SYSTEM_PROMPT},
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
