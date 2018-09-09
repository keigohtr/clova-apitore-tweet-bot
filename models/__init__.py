from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(
    session_options={
        "autocommit": False,
        "autoflush": False
    }
)

from models.notifications import Notifications
from models.access_tokens import AccessTokens
