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
    max_retries = 3
    retry_delay = 2  # seconds
    connection_timeout = 60  # 60 seconds total timeout for entire connection process
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 MongoDB connection attempt {attempt + 1}/{max_retries}")
            
            if not MONGO_URI:
                raise ValueError("MONGO_URI is not set in environment variables")

            # Wrap the entire connection process with a timeout
            await asyncio.wait_for(
                _establish_connection(),
                timeout=connection_timeout
            )
            
            logger.info("✅ Successfully connected to MongoDB")
            return  # Success, exit the retry loop
            
        except asyncio.TimeoutError:
            logger.error(f"❌ MongoDB connection timeout after {connection_timeout}s on attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise Exception(f"MongoDB connection timeout after {connection_timeout}s and {max_retries} attempts")
        except Exception as e:
            logger.error(f"❌ MongoDB connection attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("❌ All MongoDB connection attempts failed")
                raise e

async def _establish_connection():
    """Internal function to establish MongoDB connection with detailed configuration"""
    logger.info(f"�� Establishing MongoDB connection to: {MONGO_URI}")
    
    # Configure MongoDB client with Atlas-specific settings for replica sets
    client = AsyncMongoClient(
        MONGO_URI,
        # Timeout settings
        serverSelectionTimeoutMS=30000,  # 30 seconds for Atlas replica sets
        connectTimeoutMS=30000,         # 30 seconds connection timeout
        socketTimeoutMS=30000,          # 30 seconds socket timeout
        
        # Connection pool settings
        maxPoolSize=50,                 # Maximum connections in pool
        minPoolSize=5,                  # Minimum connections in pool
        maxIdleTimeMS=30000,            # Close idle connections after 30s
        
        # Retry settings
        retryWrites=True,               # Enable retryable writes
        retryReads=True,                # Enable retryable reads
        
        # Heartbeat and monitoring
        heartbeatFrequencyMS=10000,     # Send heartbeat every 10 seconds
        
        # Atlas-specific settings
        directConnection=False,         # Allow replica set discovery
        readPreference='primaryPreferred',  # Prefer primary, fallback to secondary
        
        # SSL/TLS settings for Atlas
        tls=True,                       # Enable TLS for Atlas
        tlsAllowInvalidCertificates=False,  # Validate certificates
        tlsAllowInvalidHostnames=False,     # Validate hostnames
    )
    
    # Test the connection with a ping
    logger.info("🏓 Testing MongoDB connection with ping...")
    await client.admin.command('ping')
    logger.info("✅ MongoDB ping successful")
    
    # Initialize Beanie with the database
    logger.info(f"📊 Initializing Beanie with database: {DB_NAME}")
    database = client[DB_NAME]
    await init_beanie(
        database=database, 
        document_models=[Batch, Call, PincodeData, KnowledgeBase]
    )
    
    logger.info("✅ Beanie initialization successful")
    """Internal function to establish MongoDB connection with detailed configuration"""
    logger.info(f"�� Establishing MongoDB connection to: {MONGO_URI}")
    
    # Configure MongoDB client with Atlas-specific settings for replica sets
    client = AsyncMongoClient(
        MONGO_URI,
        # Timeout settings
        serverSelectionTimeoutMS=30000,  # 30 seconds for Atlas replica sets
        connectTimeoutMS=30000,         # 30 seconds connection timeout
        socketTimeoutMS=30000,          # 30 seconds socket timeout
        
        # Connection pool settings
        maxPoolSize=50,                 # Maximum connections in pool
        minPoolSize=5,                  # Minimum connections in pool
        maxIdleTimeMS=30000,            # Close idle connections after 30s
        
        # Retry settings
        retryWrites=True,               # Enable retryable writes
        retryReads=True,                # Enable retryable reads
        
        # Heartbeat and monitoring
        heartbeatFrequencyMS=10000,     # Send heartbeat every 10 seconds
        
        # Atlas-specific settings
        directConnection=False,         # Allow replica set discovery
        readPreference='primaryPreferred',  # Prefer primary, fallback to secondary
        
        # SSL/TLS settings for Atlas
        tls=True,                       # Enable TLS for Atlas
        tlsAllowInvalidCertificates=False,  # Validate certificates
        tlsAllowInvalidHostnames=False,     # Validate hostnames
    )
    
    # Test the connection with a ping
    logger.info("🏓 Testing MongoDB connection with ping...")
    await client.admin.command('ping')
    logger.info("✅ MongoDB ping successful")
    
    # Initialize Beanie with the database
    logger.info(f"📊 Initializing Beanie with database: {DB_NAME}")
    database = client[DB_NAME]
    await init_beanie(
        database=database, 
        document_models=[Batch, Call, PincodeData, KnowledgeBase]
    )
    
    logger.info("✅ Beanie initialization successful")