import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI # Import FastAPI here
from database import create_db_and_tables, AsyncSessionLocal
from models import User # Import User model for creating a default user
from sqlalchemy.future import select # For querying User table
from scheduler import initialize_scheduler, shutdown_scheduler

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def _create_default_user_if_not_exists(): # Renamed to indicate internal use
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

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup logic
    logger.info("Application startup: Initializing database and scheduler...")
    await create_db_and_tables()
    logger.info("Database tables checked/created.")
    await _create_default_user_if_not_exists()
    logger.info("Default user checked/created.")
    await initialize_scheduler()
    logger.info("Scheduler initialized and jobs loaded.")
    logger.info("Application startup complete.")
    
    yield # Application runs here
    
    # Shutdown logic
    logger.info("Application shutdown: Shutting down scheduler...")
    await shutdown_scheduler()
    logger.info("Scheduler shutdown complete.")
    logger.info("Application shutdown complete.")

# The FastAPI app instance will be created in api.py and imported,
# or created here if api.py only defines routes/routers.
# For now, assuming app is still primarily defined in api.py and we pass lifespan to it.
# If app were defined here, it would be: app = FastAPI(lifespan=lifespan)

# This run_server function will now use the app from api.py,
# which needs to be initialized with the lifespan manager.
# We will adjust api.py to accept the lifespan.

def run_server():
    """
    Configures and runs the Uvicorn server.
    The 'app' instance is now expected to be imported from api.py,
    initialized with the lifespan manager from this file.
    """
    # Ensure api.py's app is initialized with this lifespan
    # This requires a slight modification in how 'app' is defined/imported.
    # For simplicity, we'll assume api.py imports 'lifespan' from 'main'
    # and uses it when creating its FastAPI instance.
    uvicorn.run(
        "api:app", # Points to the app instance in api.py
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True # Enable auto-reload for development
    )

if __name__ == "__main__":
    run_server()
