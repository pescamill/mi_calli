from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db.database import SessionLocal
from app.models import Property, Room, RoomImage, Contract
from app.schemas import RoomCreate, RoomUpdate, RoomResponse

router = APIRouter()

def room_to_response(room, db) -> dict:
    active_contract = db.query(Contract).filter(
        Contract.room_id == room.id,
        Contract.terminated_at == None
    ).first()
    data = RoomResponse.from_orm(room).dict()
    data["occupied"] = active_contract is not None
    return data

@router.post("/rooms", response_model=RoomResponse)
def create_room(data: RoomCreate):
    db: Session = SessionLocal()
    prop = db.query(Property).filter(Property.id == data.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="property not found")
    room = Room(
        property_id=data.property_id,
        name=data.name,
        default_amount=data.default_amount,
        default_pay_day=data.default_pay_day,
        default_duration_months=data.default_duration_months,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    result = room_to_response(room, db)
    db.close()
    return result


@router.get("/rooms", response_model=list[RoomResponse])
def get_rooms(property_id: int | None = None):
    db: Session = SessionLocal()
    query = db.query(Room).options(joinedload(Room.images))
    if property_id:
        query = query.filter(Room.property_id == property_id)
    rooms = query.all()
    result = [room_to_response(r, db) for r in rooms]
    db.close()
    return result

@router.get("/rooms/{room_id}", response_model=RoomResponse)
def get_room(room_id: int):
    db: Session = SessionLocal()
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="room not found")
    result = room_to_response(room, db)
    db.close()
    return result

@router.patch("/rooms/{room_id}", response_model=RoomResponse)
def update_room(room_id: int, data: RoomUpdate):
    db: Session = SessionLocal()
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="room not found")
    if data.name is not None:
        room.name = data.name
    if data.default_amount is not None:
        room.default_amount = data.default_amount
    if data.default_pay_day is not None:
        room.default_pay_day = data.default_pay_day
    if data.default_duration_months is not None:
        room.default_duration_months = data.default_duration_months
    db.add(room)
    db.commit()
    db.refresh(room)
    result = room_to_response(room, db)
    db.close()
    return result

@router.post("/rooms/{room_id}/images")
def add_room_image(room_id: int, payload: dict):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    db: Session = SessionLocal()
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="room not found")
    img = RoomImage(room_id=room_id, url=url)
    db.add(img)
    db.commit()
    db.refresh(img)
    db.close()
    return {"id": img.id, "url": img.url}

@router.delete("/rooms/{room_id}/images/{image_id}")
def delete_room_image(room_id: int, image_id: int):
    db: Session = SessionLocal()
    img = db.query(RoomImage).filter(
        RoomImage.id == image_id,
        RoomImage.room_id == room_id
    ).first()
    if not img:
        raise HTTPException(status_code=404, detail="image not found")
    db.delete(img)
    db.commit()
    db.close()
    return {"deleted": True}