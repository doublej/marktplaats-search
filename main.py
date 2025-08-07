import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI # Import FastAPI here
from database import create_db_and_tables, AsyncSessionLocal
from models import User # Import User model for creating a default user
from sqlalchemy.future import select # For querying User table
from scheduler import initialize_scheduler, shutdown_scheduler
from config import settings
from auth import generate_secure_token, hash_token, generate_user_identifier

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def _create_default_user_if_not_exists(): # Renamed to indicate internal use
    """Creates a default user and API token if configured and in dev mode."""
    # Only create default user if explicitly enabled and in dev mode
    if not settings.create_default_user or not settings.dev_mode:
        logger.info("Default user creation disabled (secure mode)")
        return
    
    # Use environment-provided credentials or generate secure ones
    if settings.default_user_token and settings.default_user_name:
        # Use provided values from environment (development only)
        default_token = settings.default_user_token
        default_user_identifier = settings.default_user_name
        logger.warning("Using environment-provided default credentials (DEV MODE ONLY)")
    else:
        # Generate secure credentials
        default_token = generate_secure_token()
        default_user_identifier = generate_user_identifier("dev")
        logger.info(f"Generated secure default credentials")
    
    # Hash the token for storage
    token_hash = hash_token(default_token)

    async with AsyncSessionLocal() as db:
        # Check if any users exist
        result = await db.execute(select(User))
        existing_users = result.scalars().all()
        
        if not existing_users:
            logger.info(f"Creating default user '{default_user_identifier}'")
            user = User(
                user_identifier=default_user_identifier,
                api_token_hash=token_hash,
                is_active=True
            )
            db.add(user)
            await db.commit()
            
            # Log the token only in dev mode
            if settings.dev_mode:
                logger.info(f"Default user API token: {default_token}")
                logger.warning("SAVE THIS TOKEN - it cannot be retrieved again")
        else:
            logger.info(f"Users already exist, skipping default user creation")

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
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=settings.api_reload # Enable auto-reload based on settings
    )

if __name__ == "__main__":
    run_server()
