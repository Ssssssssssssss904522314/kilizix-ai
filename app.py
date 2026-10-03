import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

def get_client():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "Введите сообщение."}), 400

    client = get_client()
    if not client:
        return jsonify({"error": "Kilizix AI ещё не подключён к модели. Добавьте OPENAI_API_KEY в Render Environment Variables."}), 503

    safe_messages = []
    for m in messages[-20:]:
        role = m.get("role")
        content = str(m.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            safe_messages.append({"role": role, "content": content})

    try:
        response = client.responses.create(
            model=os.getenv("AI_MODEL", "gpt-5-mini"),
            instructions="Ты Kilizix AI — дружелюбный, полезный ИИ-помощник. Отвечай на русском, если пользователь пишет по-русски. Не выдумывай факты.",
            input=safe_messages,
        )
        return jsonify({"reply": response.output_text})
    except Exception as e:
        return jsonify({"error": f"Ошибка Kilizix AI: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
