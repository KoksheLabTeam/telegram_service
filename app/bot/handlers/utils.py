import httpx
from app.bot.config import API_URL, BOT_TOKEN
import logging
from typing import Union  # Добавлено
from aiogram.types import Message, CallbackQuery  # Добавлено

logger = logging.getLogger(__name__)

async def get_user_info():
    async with httpx.ClientSession() as session:
        try:
            async with session.get('http://localhost:8011/api/user/me') as response:
                return await response.json()
        except httpx.ClientConnectionError as e:
            logger.error(f"Не удалось подключиться к API: {e}")
            return None

async def api_request(method: str, endpoint: str, telegram_id: int, data: dict = None) -> dict:
    headers = {"X-Telegram-Id": str(telegram_id), "Authorization": f"Bot {BOT_TOKEN}"}
    url = f"{API_URL}{endpoint}"
    timeout = httpx.Timeout(30.0)  # Увеличиваем таймаут до 30 секунд
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(method, url, headers=headers, json=data)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при запросе {method} {url}: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Ошибка {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при запросе {method} {url}: {e}")
            raise Exception(f"Ошибка: {e}")

async def api_request_no_auth(method: str, endpoint: str) -> dict:
    url = f"{API_URL}{endpoint}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(method, url)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при запросе без авторизации {method} {url}: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Ошибка {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при запросе без авторизации {method} {url}: {e}")
            raise Exception(f"Ошибка: {e}")

async def get_user_telegram_id(message_or_callback: Union[Message, CallbackQuery]) -> int:
    """Извлекает Telegram ID из объекта сообщения или коллбэка."""
    if isinstance(message_or_callback, Message):
        return message_or_callback.from_user.id
    elif isinstance(message_or_callback, CallbackQuery):
        return message_or_callback.from_user.id
    else:
        raise ValueError("Аргумент должен быть Message или CallbackQuery")