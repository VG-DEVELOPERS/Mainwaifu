from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from Grabber import user_collection, collection  # Import collections from Grabber
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI()

# Allow CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PurchaseRequest(BaseModel):
    user_id: int
    character_id: str

@app.get("/shop/balance")
async def get_balance(user_id: int):
    """Fetch user balance"""
    user = await user_collection.find_one({"id": user_id}, {"_id": 0, "balance": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"balance": user["balance"]}

@app.get("/shop/characters")
async def get_characters():
    """Retrieve all available characters for purchase"""
    characters = await collection.find({}, {"_id": 0}).to_list(100)
    return {"characters": characters}

@app.post("/shop/purchase")
async def purchase_character(data: PurchaseRequest):
    """Handle character purchase"""
    user = await user_collection.find_one({"id": data.user_id})
    character = await collection.find_one({"id": data.character_id})

    if not user or not character:
        raise HTTPException(status_code=400, detail="Invalid user or character")

    if user["balance"] < character["price"]:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Deduct balance & add character to inventory
    await user_collection.update_one({"id": data.user_id}, {"$inc": {"balance": -character["price"]}})
    await user_collection.update_one({"id": data.user_id}, {"$push": {"inventory": data.character_id}})

    return {"success": True, "message": "Character purchased successfully!"}
  
