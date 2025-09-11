import asyncio
from typing import Optional, List
from pydantic import Field, BaseModel
from datetime import datetime
from pymongo import AsyncMongoClient
from pymongo.collection import Collection
from pydantic import BaseModel
from enum import Enum
from beanie import Document, Link, init_beanie
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()
import os
from loguru import logger

# Get MongoDB URI and database name from environment variables
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "toothsi")  # Default to "toothsi" if not set


class Batch(Document):
    file_name: str
    url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeBase(Document):
    content: str
    embedding: List[float]


class CallStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    FAILED = "failed"
    INITIATED = "ringing"  # For calls that are just initiated
    PENDING = "pending"  # For calls waiting to be processed
    ACTIVE = "active"  # For calls currently active
    DONE = "done"  # For completed calls (alternative to completed)
    ENDED = "ended"  # For ended calls
    TERMINATED = "terminated"  # For terminated calls


class User(BaseModel):
    name: str
    email: str
    phone: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CallResult(BaseModel):
    summary: Optional[str] = None
    transcript: Optional[str] = None
    quality_score: Optional[float] = None
    customer_intent: Optional[str] = None
    recording_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PincodeData(Document):
    pincode: str
    home_scan: str
    clinic_1: Optional[str] = None
    clinic_2: Optional[str] = None
    city: str


class Call(Document):
    batch_id: str
    status: str = CallStatus.PENDING
    user: User
    vapi_call_id: Optional[str] = None
    call_result: Optional[CallResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


async def connect_to_db():
    try:

        if not MONGO_URI:
            raise ValueError("MONGO_URI is not set in environment variables")



        client = AsyncMongoClient(
           "mongodb+srv://bikaxh:bikash1@cluster0.0r9fjmy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        )
        await client.admin.command("ping")
        database = client[DB_NAME]
        await init_beanie(
            database=database, document_models=[Batch, Call, PincodeData, KnowledgeBase]
        )

        logger.info("✅ Successfully connected to MongoDB")
    except Exception as e:

        logger.error("All MongoDB connection attempts failed", str(e))
        raise e
