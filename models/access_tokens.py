import datetime

from sqlalchemy import (
    Column, String,
    Text, DateTime
)

from models import db


class AccessTokens(db.Model):
    """
    AccessTokens
    """
    __tablename__ = 'access_tokens'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    user_id = Column(String(128), primary_key=True)
    token = Column(Text, nullable=False)
    register_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    @property
    def serialize(self):
        return {
            'user_id': self.user_id,
            'token': self.token,
            'register_date': self.register_date.strftime('%Y-%m-%d %H:%M:%S'),
        }
