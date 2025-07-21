import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai

# Создание экземпляра приложения FastAPI
app = FastAPI()

# Загрузка API ключей из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")
currents_api_key = os.getenv("CURRENTS_API_KEY")

# Проверка наличия всех необходимых API ключей
if not openai.api_key:
    raise ValueError("Переменная окружения OPENAI_API_KEY не установлена.")
if not currents_api_key:
    raise ValueError("Переменная окружения CURRENTS_API_KEY не установлена.")

# Модель запроса от пользователя
class Topic(BaseModel):
    topic: str

# Функция получения последних новостей по теме
def get_recent_news(topic: str) -> str:
    url = "https://api.currentsapi.services/v1/latest-news"
    params = {
        "language": "en",
        "keywords": topic,
        "apiKey": currents_api_key
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении новостей: {response.text}")

    news = response.json().get("news", [])

    if not news:
        return "No recent news found."

    # Формируем строку из заголовков первых 5 новостей
    return "\n".join([f"- {article['title']}" for article in news[:5]])

# Функция генерации контента с использованием OpenAI
def generate_content(topic: str) -> dict:
    try:
        recent_news = get_recent_news(topic)

        # Генерация заголовка
        title_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Придумай привлекательный заголовок статьи на тему '{topic}', используя эти новости:\n{recent_news}"
            }],
            max_tokens=20,
            temperature=0.6
        )
        title = title_response.choices[0].message.content.strip()

        # Генерация мета-описания
        meta_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Напиши мета-описание для статьи с заголовком '{title}', включая ключевые слова и краткое содержание темы."
            }],
            max_tokens=20,
            temperature=0.5
        )
        meta_description = meta_response.choices[0].message.content.strip()

        # Генерация основного контента
        content_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""
Напиши статью на тему '{topic}', используя следующие актуальные новости:
{recent_news}

Требования:
- Вступление, основная часть, заключение
- Четкая структура с подзаголовками
- Примеры из новостей
- Не менее 1500 символов
- Язык — живой и понятный
"""
            }],
            max_tokens=1500,
            temperature=0.7,
            presence_penalty=0.6,
            frequency_penalty=0.6
        )
        post_content = content_response.choices[0].message.content.strip()

        return {
            "title": title,
            "meta_description": meta_description,
            "post_content": post_content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации контента: {str(e)}")

# Эндпоинт генерации поста
@app.post("/generate-post")
async def generate_post_api(topic: Topic):
    return generate_content(topic.topic)

# Эндпоинт проверки работы сервиса
@app.get("/")
async def root():
    return {"message": "Content generation service is running."}

# Эндпоинт heartbeat для мониторинга
@app.get("/heartbeat")
async def heartbeat():
    return {"status": "OK"}

# Точка входа при запуске через `python main.py`
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
