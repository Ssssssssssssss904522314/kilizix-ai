# Kilizix AI

Отдельный AI-проект с веб-интерфейсом, Flask backend и подготовкой к деплою на Render.

## Запуск

```bash
pip install -r requirements.txt
python app.py
```

Для ответов модели нужен `OPENAI_API_KEY`.

## Render

Build Command:
`pip install -r requirements.txt`

Start Command:
`gunicorn app:app`

Переменные окружения:
- `OPENAI_API_KEY`
- `AI_MODEL` (по умолчанию `gpt-5-mini`)
