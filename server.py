import sys
sys.setrecursionlimit(3000)

from flask import Flask, request, jsonify, send_from_directory
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
import json
import os
import datetime

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={API_KEY}"

MEMORY_FILE = "memory.json"

SYSTEM_PROMPT = """Ты J.A.R.V.I.S — умный AI-ассистент с доступом к интернету и собственной памятью.

У тебя есть инструменты:
- web_search: поиск информации в интернете. Используй когда нужна актуальная информация, факты, новости.
- read_webpage: чтение содержимого веб-страницы по URL.
- save_memory: сохранение важной информации в долговременную память. Сохраняй полезные факты, которые могут пригодиться в будущем.
- get_memory: получение всех сохранённых знаний из памяти.

Активно используй поиск в интернете для ответов на вопросы о текущих событиях, фактах и данных.
Сохраняй в память ключевые факты, которые узнаёшь.
Отвечай на русском языке, если пользователь пишет на русском. Будь дружелюбным и полезным."""


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_memory_to_file(memory_list):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_list, f, ensure_ascii=False, indent=2)


# --- Tool functions ---

def web_search(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "Ничего не найдено."
        output = []
        for r in results:
            output.append(f"**{r['title']}**\n{r['body']}\nURL: {r['href']}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Ошибка поиска: {str(e)}"


def read_webpage(url):
    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:5000]
    except Exception as e:
        return f"Ошибка чтения страницы: {str(e)}"


def save_memory(fact, category="general"):
    memory = load_memory()
    entry = {
        "fact": fact,
        "category": category,
        "date": datetime.datetime.now().isoformat()
    }
    memory.append(entry)
    save_memory_to_file(memory)
    return f"Сохранено в память: {fact}"


def get_memory():
    memory = load_memory()
    if not memory:
        return "Память пуста."
    output = []
    for m in memory:
        output.append(f"[{m.get('category', 'general')}] {m['fact']} ({m['date'][:10]})")
    return "\n".join(output)


TOOL_FUNCTIONS = {
    "web_search": lambda args: web_search(args["query"]),
    "read_webpage": lambda args: read_webpage(args["url"]),
    "save_memory": lambda args: save_memory(args["fact"], args.get("category", "general")),
    "get_memory": lambda args: get_memory(),
}

TOOLS_SCHEMA = [
    {
        "function_declarations": [
            {
                "name": "web_search",
                "description": "Search the internet for current information, facts, news.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "read_webpage",
                "description": "Read and extract text content from a webpage URL.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "url": {"type": "STRING", "description": "URL of the webpage"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "save_memory",
                "description": "Save a fact to long-term memory for future reference.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "fact": {"type": "STRING", "description": "The fact to save"},
                        "category": {"type": "STRING", "description": "Category: science, history, tech, user_info, general"}
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "get_memory",
                "description": "Retrieve all saved knowledge from long-term memory.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {},
                    "required": []
                }
            }
        ]
    }
]


def call_gemini(contents):
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "tools": TOOLS_SCHEMA,
    }
    resp = requests.post(GEMINI_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


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
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Call Gemini and handle tool calls
        for _ in range(3):
            result = call_gemini(contents)

            candidates = result.get("candidates", [])
            if not candidates:
                return jsonify({"reply": "Не удалось получить ответ."})

            parts = candidates[0].get("content", {}).get("parts", [])
            function_calls = [p for p in parts if "functionCall" in p]

            if not function_calls:
                # No tool calls — extract text reply
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                reply = "\n".join(text_parts) or "Не удалось получить ответ."
                return jsonify({"reply": reply})

            # Execute tools and continue
            contents.append(candidates[0]["content"])

            func_response_parts = []
            for fc in function_calls:
                fn_name = fc["functionCall"]["name"]
                fn_args = fc["functionCall"].get("args", {})

                try:
                    if fn_name in TOOL_FUNCTIONS:
                        tool_result = TOOL_FUNCTIONS[fn_name](fn_args)
                    else:
                        tool_result = f"Unknown function: {fn_name}"
                except Exception as e:
                    tool_result = f"Tool error: {str(e)}"

                func_response_parts.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"result": tool_result}
                    }
                })

            contents.append({"role": "user", "parts": func_response_parts})

        return jsonify({"reply": "Не удалось получить ответ."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=True, port=port)
