import motor.motor_asyncio
from dotenv import load_dotenv
import os
load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client["dental_clinic"]

appointments_collection = db["appointments"]
conversations_collection =db["conversations"]

