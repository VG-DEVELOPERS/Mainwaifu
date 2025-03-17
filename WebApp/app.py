import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from Grabber import user_collection, collection as character_collection
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
 
# FastAPI instance
app = FastAPI()

# MongoDB connection

# Prices based on rarity
RARITY_PRICES = {
    "Common": 1000,
    "Medium": 2500,
    "Rare": 5000,
    "Legendary": 10000
}

# Special user with unlimited balance
ADMIN_USER_ID = 7717913705


class PurchaseRequest(BaseModel):
    user_id: int
    character_id: int


@app.get("/")
async def home():
    return JSONResponse(content={"message": "Welcome to the Telegram WebApp Character Shop!"})


@app.get("/shop/balance")
async def get_balance(user_id: int = Query(..., description="Telegram User ID")):
    """Fetch user's balance from MongoDB"""
    user = await user_collection.find_one({"id": user_id}, projection={"balance": 1})
    return {"balance": user.get("balance", 0) if user else 0}


@app.get("/shop/characters")
async def get_characters():
    """Fetch available characters from the database"""
    characters_cursor = character_collection.find({}, projection={"id": 1, "name": 1, "rarity": 1, "image_url": 1})
    characters = []
    async for character in characters_cursor:
        character["price"] = RARITY_PRICES.get(character["rarity"], 1000)  # Default to 1000 if rarity is unknown
        characters.append(character)
    return {"characters": characters}


@app.post("/shop/purchase")
async def purchase_character(request: PurchaseRequest):
    """Handles character purchases"""
    user_id = request.user_id
    character_id = request.character_id

    # Fetch character details
    character = await character_collection.find_one({"id": character_id}, projection={"name": 1, "rarity": 1})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    price = RARITY_PRICES.get(character["rarity"], 1000)  # Default price if rarity is missing

    # If the user is the admin, allow unlimited purchases
    if user_id == ADMIN_USER_ID:
        return {"message": f"✅ You have successfully obtained {character['name']} (Admin Privileges)"}

    # Fetch user's balance
    user = await user_collection.find_one({"id": user_id}, projection={"balance": 1})
    if not user or user.get("balance", 0) < price:
        raise HTTPException(status_code=400, detail="❌ Insufficient balance.")

    # Deduct balance and confirm purchase
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -price}})
    
    return {"message": f"✅ Successfully purchased {character['name']} for {price} coins."}


# Run locally for testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
        
