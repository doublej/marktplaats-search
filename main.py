import uvicorn
# Ensure api.py is in the same directory or Python path
from api import app

def main():
    """
    Runs the FastAPI application using Uvicorn.
    """
    # The app instance is imported from api.py
    # Uvicorn will look for an 'app' variable in the 'api' module.
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")

if __name__ == "__main__":
    main()
