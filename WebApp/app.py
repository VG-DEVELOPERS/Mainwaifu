import os
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from Grabber import user_collection  # Ensure correct import

app = FastAPI()

@app.get("/")
async def home():
    return JSONResponse(content={"message": "Welcome to the Telegram WebApp Shop!"})

@app.get("/shop/balance")
async def get_balance(user_id: int = Query(..., description="Telegram User ID")):
    """Fetch user's balance from MongoDB"""
    user = await user_collection.find_one({"id": user_id}, projection={"balance": 1})
    return {"balance": user.get("balance", 0) if user else 0}

# Run locally for testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    
