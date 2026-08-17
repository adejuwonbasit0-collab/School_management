import sys
import os
from dotenv import load_dotenv

# Ensure the project root directory is in the Python path for PythonAnywhere
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env file
dotenv_path = os.path.join(project_home, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app

# PythonAnywhere looks for the WSGI entry point named 'application'
application = app = create_app(os.environ.get("FLASK_ENV", "production"))

if __name__ == "__main__":
    app.run()
