import asyncio
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from sqlalchemy.exc import OperationalError
from app.bot.bot_runner import main
from app.core.database.helper import SessionLocal
from app.core.models.city import City
from app.core.services.city import create_city
from app.core.schemas.city import CityCreate

@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(5),
    retry=retry_if_exception_type(OperationalError)
)
def init_db_with_retry():
    with SessionLocal() as session:
        try:
            if not session.query(City).first():
                city_data = CityCreate(name="Кокшетау")
                create_city(session, city_data)
                session.commit()
                print("Город 'Кокшетау' добавлен в базу данных.")
            else:
                print("База данных уже содержит города, инициализация не требуется.")
        except Exception as e:
            print(f"Ошибка при инициализации базы данных: {e}")
            session.rollback()
            raise

if __name__ == "__main__":
    try:
        init_db_with_retry()
    except Exception as e:
        print(f"Не удалось инициализировать базу данных после нескольких попыток: {e}")
        exit(1)
    asyncio.run(main())  # Запуск polling бота