from tortoise import fields
from tortoise.models import Model
import bcrypt
from datetime import datetime, timedelta
import uuid

class User(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=254, unique=True)
    phone = fields.CharField(max_length=20, null=True)
    first_name = fields.CharField(max_length=100, null=True)
    last_name = fields.CharField(max_length=100, null=True)
    password_hash = fields.CharField(max_length=255)
    user_type = fields.CharField(max_length=20, default="user")  # "user" or "dispatcher"
    created_at = fields.DatetimeField(auto_now_add=True)

    async def set_password(self, plain_password: str):
        # bcrypt only accepts up to 72 bytes — truncate safely
        safe_pw = plain_password[:72].encode("utf-8")
        hashed = bcrypt.hashpw(safe_pw, bcrypt.gensalt())
        self.password_hash = hashed.decode("utf-8")

    async def verify_password(self, plain_password: str) -> bool:
        safe_pw = plain_password[:72].encode("utf-8")
        return bcrypt.checkpw(safe_pw, self.password_hash.encode("utf-8"))

    def __str__(self):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return f"{name or self.email} ({self.user_type})"

class Location(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="locations", on_delete=fields.CASCADE)
    name = fields.CharField(max_length=100, null=True)
    lat = fields.FloatField()
    long = fields.FloatField()
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name or 'Unnamed'} ({self.lat}, {self.long})"


class DispatcherStatus(Model):
    id = fields.IntField(pk=True)
    dispatcher = fields.ForeignKeyField("models.User", related_name="status", unique=True, on_delete=fields.CASCADE)
    online = fields.BooleanField(default=False)
    lat = fields.FloatField(null=True)
    long = fields.FloatField(null=True)
    color = fields.CharField(max_length=20, null=True)
    last_seen = fields.DatetimeField(auto_now=True)

    @property
    def expired(self):
        return datetime.utcnow() - self.last_seen.replace(tzinfo=None) > timedelta(seconds=60)

    def __str__(self):
        return f"{self.dispatcher.email} ({'Online' if self.online else 'Offline'})"

