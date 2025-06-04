#!/usr/bin/env python3
"""
Script to initialize MongoDB with required collections and indexes
"""

import asyncio
import os
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import logging
from models.schemas import get_schema_validation_commands

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def init_db():
    """Initialize MongoDB collections and indexes"""
    client = None
    try:
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            logger.error("MONGODB_URI environment variable not set")
            return
        
        logger.info(f"Connecting to MongoDB at {mongodb_uri}")
        client = AsyncIOMotorClient(mongodb_uri)
        
        # Extract database name from URI
        db_name = "mookitTesting"
        db = client[db_name]
        
        # Create collections if they don't exist
        if "lectures" not in await db.list_collection_names():
            await db.create_collection("lectures")
            logger.info("Created lectures collection")
        
        if "notes" not in await db.list_collection_names():
            await db.create_collection("notes")
            logger.info("Created notes collection")
        
        # Create indexes
        await db.lectures.create_index("videoId", unique=True)
        logger.info("Created index on lectures.videoId")
        
        await db.lectures.create_index("status")
        logger.info("Created index on lectures.status")
        
        await db.notes.create_index("lectureId")
        logger.info("Created index on notes.lectureId")
        
        # Apply schema validation
        schema_commands = get_schema_validation_commands()
        for command in schema_commands:
            try:
                await db.command(command)
                logger.info(f"Applied schema validation to collection {command['collMod']}")
            except pymongo.errors.OperationFailure as e:
                logger.warning(f"Could not apply schema validation to {command['collMod']}: {e}")
        
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    asyncio.run(init_db())
