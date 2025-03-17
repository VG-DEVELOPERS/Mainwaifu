import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from Grabber import user_collection, application  # Ensure correct import

app = FastAPI()

# Serve the WebApp UI from the static folder
@app.get("/", response_class=FileResponse)
async def serve_index():
    return "WebApp/static/index.html"

# API route example (modify as needed)
@app.get("/shop/balance")
async def get_balance(user_id: int):
    user = await user_collection.find_one({"id": user_id}, projection={"balance": 1})
    if user:
        return {"balance": user.get("balance", 0)}
    return {"balance": 0}

# Run only if executed directly (not needed for Heroku)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    
