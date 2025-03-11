from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.models.city import City
from app.core.schemas.city import CityCreate, CityUpdate

def create_city(session: Session, data: CityCreate) -> City:
    city = City(**data.model_dump())
    session.add(city)
    try:
        session.commit()
        session.refresh(city)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="City with this name already exists")
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create city: {e}")
    return city

def get_city_by_id(session: Session, id: int) -> City:
    city = session.get(City, id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    return city

def get_all_cities(session: Session) -> list[City]:
    return session.scalars(select(City)).all()

def update_city_by_id(session: Session, data: CityUpdate, id: int) -> City:
    city = get_city_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(city, key, value)
    try:
        session.commit()
        session.refresh(city)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="City with this name already exists")
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update city: {e}")
    return city

def delete_city_by_id(session: Session, id: int):
    city = get_city_by_id(session, id)
    session.delete(city)
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete city: {e}")