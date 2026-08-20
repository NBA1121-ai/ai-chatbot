# AI Чат-бот

Веб-приложение для общения с искусственным интеллектом. Красивый тёмный интерфейс, бэкенд на Flask, AI на базе Google Gemini 3.6 Flash.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![Gemini](https://img.shields.io/badge/Google%20Gemini-3.6%20Flash-orange)

![Скриншот](screenshot.png)

## Возможности

- Общение с AI на любом языке
- Тёмный интерфейс в стиле ChatGPT
- История диалога в рамках сессии
- Кнопки-подсказки для быстрого старта
- Анимация набора текста
- Адаптивный дизайн (мобильные устройства)
- Отправка по Enter, новая строка по Shift+Enter

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/NBA1121-ai/ai-chatbot.git
cd ai-chatbot
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Получить API-ключ (бесплатно)

Перейдите на [aistudio.google.com/apikey](https://aistudio.google.com/apikey) и создайте ключ.

### 4. Установить ключ

```bash
export GEMINI_API_KEY="ваш-ключ"
```

### 5. Запустить сервер

```bash
python server.py
```

### 6. Открыть в браузере

```
http://localhost:5000
```

## Структура проекта

```
ai-chatbot/
├── index.html         # Фронтенд (HTML/CSS/JS)
├── server.py          # Бэкенд (Flask + Google Gemini)
├── requirements.txt   # Зависимости
└── README.md
```

## Технологии

- **Фронтенд:** HTML, CSS, JavaScript
- **Бэкенд:** Python, Flask
- **AI:** Google Gemini 3.6 Flash (бесплатный API)
