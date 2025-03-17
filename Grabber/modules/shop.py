from fastapi import APIRouter, HTTPException, Request
from pymongo import MongoClient
from pydantic import BaseModel
import hashlib
import hmac
import os
from Grabber import application, user_collection


router = APIRouter()


# Function to verify Telegram Web App data
def verify_telegram_data(init_data: str):
    """Verify data received from Telegram Web App"""
    data_check_string = "\n".join(
        sorted(
            f"{k}={v}"
            for k, v in [
                param.split("=")
                for param in init_data.split("&")
                if param.split("=")[0] != "hash"
            ]
        )
    )
    secret_key = hmac.new(
        key=bytes("WebAppData", "utf-8"),
        msg=bytes(TELEGRAM_BOT_TOKEN, "utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(secret_key, msg=bytes(data_check_string, "utf-8"), digestmod=hashlib.sha256).hexdigest()
    
    received_hash = dict(param.split("=") for param in init_data.split("&"))["hash"]

    return hmac.compare_digest(calculated_hash, received_hash)

class PurchaseRequest(BaseModel):
    user_id: int
    character_id: str

@router.get("/characters")
async def get_characters():
    """Retrieve all available characters for purchase"""
    characters = list(character_collection.find({}, {"_id": 0}))
    return {"characters": characters}

@router.post("/purchase")
async def purchase_character(data: PurchaseRequest):
    """Allow users to purchase characters using their balance"""
    user = user_collection.find_one({"id": data.user_id})
    character = character_collection.find_one({"id": data.character_id})

    if not user or not character:
        raise HTTPException(status_code=400, detail="Invalid user or character")

    if user["balance"] < character["price"]:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Deduct balance
    user_collection.update_one({"id": data.user_id}, {"$inc": {"balance": -character["price"]}})
    
    # Add character to user's inventory
    user_collection.update_one({"id": data.user_id}, {"$push": {"inventory": data.character_id}})

    return {"success": True, "message": "Character purchased successfully!"}
  
