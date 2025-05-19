import uvicorn
import asyncio
import logging

from api import app # Import the FastAPI app instance from api.py
from database import create_db_and_tables, AsyncSessionLocal
from models import User # Import User model for creating a default user
from sqlalchemy.future import select # For querying User table
from scheduler import initialize_scheduler, shutdown_scheduler

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_default_user_if_not_exists():
    """Creates a default user and API token if one doesn't exist."""
    default_token = "test_token_123" # Keep this secure in a real app
    default_user_identifier = "user_alpha"

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.api_token == default_token))
        existing_user = result.scalars().first()
        if not existing_user:
            logger.info(f"Creating default user '{default_user_identifier}' with token '{default_token}'")
            user = User(user_identifier=default_user_identifier, api_token=default_token)
            db.add(user)
            await db.commit()
        else:
            logger.info(f"Default user '{default_user_identifier}' already exists.")

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: Initializing database and scheduler...")
    await create_db_and_tables()
    logger.info("Database tables checked/created.")
    await create_default_user_if_not_exists()
    logger.info("Default user checked/created.")
    await initialize_scheduler()
    logger.info("Scheduler initialized and jobs loaded.")
    logger.info("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown: Shutting down scheduler...")
    await shutdown_scheduler()
    logger.info("Scheduler shutdown complete.")
    # Note: SQLAlchemy engine connections are typically managed by the connection pool
    # and don't require explicit closing here unless specific non-pooled connections were made.
    logger.info("Application shutdown complete.")

def run_server():
    """
    Configures and runs the Uvicorn server.
    """
    uvicorn.run(
        "main:app", # Points to the app instance in this file (main.py)
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True # Enable auto-reload for development
    )

if __name__ == "__main__":
    run_server()
