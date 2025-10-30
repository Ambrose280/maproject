from tortoise import fields
from tortoise.models import Model
import bcrypt
from datetime import datetime, timedelta


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=100, unique=True)
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
        return f"{self.username} ({self.user_type})"


class Location(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="locations", on_delete=fields.CASCADE)
    name = fields.CharField(max_length=100, null=True)
    lat = fields.FloatField()
    long = fields.FloatField()
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name or 'Unnamed'} ({self.lat}, {self.long})"


class Order(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="orders", on_delete=fields.CASCADE)
    location = fields.ForeignKeyField("models.Location", related_name="orders", null=True, on_delete=fields.SET_NULL)
    title = fields.CharField(max_length=200, null=True)
    image_path = fields.CharField(max_length=255, null=True)
    cylinder_type = fields.CharField(max_length=50, null=True)
    quantity = fields.IntField(default=1)
    status = fields.CharField(max_length=20, default="Pending")  # Pending / Accepted / Declined / In Transit / Delivered
    dispatcher = fields.ForeignKeyField("models.User", related_name="assigned_orders", null=True, on_delete=fields.SET_NULL)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.status}"


class DispatcherStatus(Model):
    """
    Live dispatcher status for map display and online/offline toggling.
    """
    id = fields.IntField(pk=True)
    dispatcher = fields.ForeignKeyField("models.User", related_name="status", unique=True, on_delete=fields.CASCADE)
    online = fields.BooleanField(default=False)
    lat = fields.FloatField(null=True)
    long = fields.FloatField(null=True)
    color = fields.CharField(max_length=20, null=True)  # map pulse color
    last_seen = fields.DatetimeField(auto_now=True)

    @property
    def expired(self):
        """Session expires if last seen > 10 seconds ago"""
        return datetime.utcnow() - self.last_seen.replace(tzinfo=None) > timedelta(seconds=10)

    def __str__(self):
        return f"{self.dispatcher.username} ({'Online' if self.online else 'Offline'})"
