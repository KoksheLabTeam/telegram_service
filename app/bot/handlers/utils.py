import aiohttp
from aiogram.types import Message
import logging

logger = logging.getLogger(__name__)

async def api_request(method: str, url: str, telegram_id: int, data: dict = None):
    headers = {"x-telegram-id": str(telegram_id)}
    logger.info(f"Выполняется запрос: {method} {url} с headers={headers}")
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url, headers=headers) as response:
                logger.info(f"Ответ: статус {response.status}, тело: {await response.text()}")
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ошибка {response.status}: {error_text}")
                return await response.json()
        elif method == "POST":
            async with session.post(url, headers=headers, json=data) as response:
                if response.status not in (200, 201):
                    raise Exception(f"Ошибка {response.status}: {await response.text()}")
                return await response.json()
        elif method == "DELETE":
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Ошибка {response.status}: {await response.text()}")
                return None
        elif method == "PATCH":
            async with session.patch(url, headers=headers, json=data) as response:
                if response.status != 200:
                    raise Exception(f"Ошибка {response.status}: {await response.text()}")
                return await response.json()

def get_user_telegram_id(message: Message) -> int:
    return message.from_user.id