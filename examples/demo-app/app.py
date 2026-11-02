import os

DATABASE_URL = os.environ["DATABASE_URL"]
SECRET_KEY = os.getenv("SECRET_KEY")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")
DEBUG = os.getenv("DEBUG", "false") == "true"
