import datetime

from sqlalchemy import (
    Column, Integer, String,
    Text, DateTime
)

from models import db


class Notifications(db.Model):
    """
    Notifications
    """
    __tablename__ = 'notification'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    register_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'register_date': self.register_date.strftime('%Y-%m-%d %H:%M:%S'),
        }
