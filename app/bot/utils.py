import aiohttp
import logging

logger = logging.getLogger(__name__)


async def api_request(method: str, url: str, telegram_id: int | None = None, data: dict | None = None,
                      auth: bool = True) -> dict | list:
    """
    Выполняет HTTP-запрос к API с опциональной авторизацией через заголовок x-telegram-id.

    :param method: HTTP-метод (GET, POST, PATCH и т.д.)
    :param url: URL запроса
    :param telegram_id: Telegram ID для авторизации (если auth=True)
    :param data: Данные для отправки в теле запроса (для POST/PATCH)
    :param auth: Использовать ли авторизацию (по умолчанию True)
    :return: Ответ API в виде словаря или списка
    """
    headers = {"x-telegram-id": str(telegram_id)} if auth and telegram_id else {}
    logger.info(f"Выполняется запрос: {method} {url} с headers={headers if auth else 'без авторизации'}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, headers=headers, json=data) as response:
                status_code = response.status
                if status_code >= 400:
                    error_text = await response.text()
                    logger.error(f"Ошибка при выполнении запроса {method} {url}: Ошибка {status_code}: {error_text}")
                    raise Exception(f"Ошибка {status_code}: {error_text}")
                result = await response.json()
                return result
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса {method} {url}: {e}")
            raise