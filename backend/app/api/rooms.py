from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.models import Property, Room, RoomImage, Contract
from app.schemas.rooms import RoomCreate, RoomUpdate, RoomResponse

router = APIRouter()

def enrich_room(room: Room, db: Session) -> dict:
    active_contract = db.query(Contract).filter(
        Contract.room_id == room.id,
        Contract.terminated_at == None
    ).first()
    data = {
        "id": room.id,
        "property_id": room.property_id,
        "name": room.name,
        "default_amount": float(room.default_amount) if room.default_amount else None,
        "default_pay_day": room.default_pay_day,
        "default_duration_months": room.default_duration_months,
        "created_at": room.created_at,
        "images": [{"id": img.id, "url": img.url, "created_at": img.created_at} for img in room.images],
        "occupied": active_contract is not None,
    }
    return data

@router.post("/rooms", response_model=RoomResponse)
def create_room(data: RoomCreate, db: Session = Depends(get_db)):
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
    room = db.query(Room).options(joinedload(Room.images)).filter(Room.id == room.id).first()
    return enrich_room(room, db)

@router.get("/rooms", response_model=list[RoomResponse])
def get_rooms(property_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Room).options(joinedload(Room.images))
    if property_id:
        query = query.filter(Room.property_id == property_id)
    rooms = query.all()
    return [enrich_room(r, db) for r in rooms]

@router.get("/rooms/{room_id}", response_model=RoomResponse)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).options(joinedload(Room.images)).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="room not found")
    return enrich_room(room, db)

@router.patch("/rooms/{room_id}", response_model=RoomResponse)
def update_room(room_id: int, data: RoomUpdate, db: Session = Depends(get_db)):
    room = db.query(Room).options(joinedload(Room.images)).filter(Room.id == room_id).first()
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
    room = db.query(Room).options(joinedload(Room.images)).filter(Room.id == room_id).first()
    return enrich_room(room, db)

@router.post("/rooms/{room_id}/images")
def add_room_image(room_id: int, payload: dict, db: Session = Depends(get_db)):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="room not found")
    img = RoomImage(room_id=room_id, url=url)
    db.add(img)
    db.commit()
    db.refresh(img)
    return {"id": img.id, "url": img.url}

@router.delete("/rooms/{room_id}/images/{image_id}")
def delete_room_image(room_id: int, image_id: int, db: Session = Depends(get_db)):
    img = db.query(RoomImage).filter(
        RoomImage.id == image_id,
        RoomImage.room_id == room_id
    ).first()
    if not img:
        raise HTTPException(status_code=404, detail="image not found")
    db.delete(img)
    db.commit()
    return {"deleted": True}