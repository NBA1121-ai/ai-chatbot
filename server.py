from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
import json
import os
import datetime

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY)

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

def web_search(query: str) -> str:
    """Search the internet using DuckDuckGo."""
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


def read_webpage(url: str) -> str:
    """Read and extract text from a webpage."""
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


def save_memory(fact: str, category: str = "general") -> str:
    """Save a fact to long-term memory."""
    memory = load_memory()
    entry = {
        "fact": fact,
        "category": category,
        "date": datetime.datetime.now().isoformat()
    }
    memory.append(entry)
    save_memory_to_file(memory)
    return f"Сохранено в память: {fact}"


def get_memory() -> str:
    """Retrieve all saved knowledge from memory."""
    memory = load_memory()
    if not memory:
        return "Память пуста."
    output = []
    for m in memory:
        output.append(f"[{m.get('category', 'general')}] {m['fact']} ({m['date'][:10]})")
    return "\n".join(output)


# --- Tool definitions for Gemini ---

tools = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="web_search",
            description="Search the internet for current information, facts, news, or any topic. Use this when you need up-to-date information.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(type="STRING", description="Search query")
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="read_webpage",
            description="Read and extract text content from a webpage URL.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "url": types.Schema(type="STRING", description="URL of the webpage to read")
                },
                required=["url"]
            )
        ),
        types.FunctionDeclaration(
            name="save_memory",
            description="Save an important fact or piece of knowledge to long-term memory for future reference.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "fact": types.Schema(type="STRING", description="The fact or knowledge to save"),
                    "category": types.Schema(type="STRING", description="Category: science, history, tech, user_info, general")
                },
                required=["fact"]
            )
        ),
        types.FunctionDeclaration(
            name="get_memory",
            description="Retrieve all previously saved knowledge from long-term memory.",
            parameters=types.Schema(
                type="OBJECT",
                properties={},
                required=[]
            )
        ),
    ])
]

TOOL_FUNCTIONS = {
    "web_search": lambda args: web_search(args["query"]),
    "read_webpage": lambda args: read_webpage(args["url"]),
    "save_memory": lambda args: save_memory(args["fact"], args.get("category", "general")),
    "get_memory": lambda args: get_memory(),
}


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
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))

        # Call Gemini with tools
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=tools,
            ),
        )

        # Handle tool calls in a loop
        max_iterations = 5
        iteration = 0

        while response.candidates[0].content.parts and iteration < max_iterations:
            has_function_call = False
            function_responses = []

            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_function_call = True
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args) if part.function_call.args else {}

                    # Execute the tool
                    if fn_name in TOOL_FUNCTIONS:
                        result = TOOL_FUNCTIONS[fn_name](fn_args)
                    else:
                        result = f"Unknown function: {fn_name}"

                    function_responses.append(types.Part.from_function_response(
                        name=fn_name,
                        response={"result": result}
                    ))

            if not has_function_call:
                break

            # Add model's response and tool results to contents
            contents.append(response.candidates[0].content)
            contents.append(types.Content(
                role="user",
                parts=function_responses
            ))

            # Call Gemini again with tool results
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=tools,
                ),
            )
            iteration += 1

        reply = response.text or "Не удалось получить ответ."
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=True, port=port)
