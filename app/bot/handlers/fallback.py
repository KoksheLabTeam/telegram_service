from aiogram import Router
from aiogram.types import Message
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message()
async def handle_unprocessed_messages(message: Message):
    logger.warning(f"Необработанное сообщение: {message}")
    await message.answer("Извините, я не понял вашего сообщения. Попробуйте использовать команды или кнопки.")