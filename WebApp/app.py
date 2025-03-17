import os
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from Grabber import user_collection, collection as character_collection  # Ensure correct imports

app = FastAPI()

@app.get("/")
async def home():
    return JSONResponse(content={"message": "Welcome to the Telegram WebApp Shop!"})

@app.get("/shop/balance")
async def get_balance(user_id: int = Query(..., description="Telegram User ID")):
    """Fetch user's balance from MongoDB"""
    user = await user_collection.find_one({"id": user_id}, projection={"balance": 1})
    balance = user.get("balance", 0) if user else 0
    return {"balance": balance}

@app.get("/shop/characters")
async def list_characters():
    """Fetch available characters from the database"""
    characters = await character_collection.find({}, projection={"_id": 0, "id": 1, "name": 1, "price": 1}).to_list(length=100)
    return {"characters": characters}

@app.post("/shop/purchase")
async def purchase_character(user_id: int = Query(..., description="Telegram User ID"), character_id: int = Query(...)):
    """Allow a user to purchase a character"""
    # Get user details
    user = await user_collection.find_one({"id": user_id}, projection={"balance": 1, "owned_characters": 1})
    if not user:
        return JSONResponse(status_code=400, content={"error": "User not found"})

    balance = user.get("balance", 0)
    owned_characters = user.get("owned_characters", [])

    # Get character details
    character = await character_collection.find_one({"id": character_id}, projection={"_id": 0, "name": 1, "price": 1})
    if not character:
        return JSONResponse(status_code=400, content={"error": "Character not found"})

    character_price = character["price"]

    # Check if the user already owns the character
    if character_id in owned_characters:
        return JSONResponse(status_code=400, content={"error": "You already own this character."})

    # Check if user has enough balance
    if balance < character_price:
        return JSONResponse(status_code=400, content={"error": "Insufficient balance."})

    # Deduct balance and add character
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": -character_price}, "$push": {"owned_characters": character_id}}
    )

    return JSONResponse(content={"message": f"✅ Successfully purchased {character['name']}!", "remaining_balance": balance - character_price})

# Run locally for testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    
