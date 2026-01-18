from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["UserbotNetwork"]
sessions = db["sessions"]

async def add_session(user_id: int, session_string: str):
    await sessions.update_one(
        {"user_id": user_id},
        {"$set": {"session": session_string}},
        upsert=True
    )

async def remove_session(user_id: int):
    await sessions.delete_one({"user_id": user_id})

async def get_all_sessions():
    cursor = sessions.find({})
    data = []
    async for doc in cursor:
        if "session" in doc:
            data.append(doc["session"])
    return data