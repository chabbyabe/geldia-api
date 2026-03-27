from .base import *

CORS_ALLOWED_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
DEBUG = True

# DATABASE
USE_POSTGRES=True
DATABASE_NAME="test_db"
DATABASE_USER="postgres"
DATABASE_PASSWORD="postgres"
DATABASE_HOST="127.0.0.1"
DATABASE_PORT="5432"