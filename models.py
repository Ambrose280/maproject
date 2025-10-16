from tortoise import fields
from tortoise.models import Model
import bcrypt


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=100, unique=True)
    password_hash = fields.CharField(max_length=255)
    delivery = fields.BooleanField(default=False)

    async def set_password(self, plain_password: str):
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
        self.password_hash = hashed.decode('utf-8')

    async def verify_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), self.password_hash.encode('utf-8'))


class Location(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=False)
    user = fields.ForeignKeyField("models.User", related_name="locations")
    lat = fields.FloatField()
    long = fields.FloatField()
    created_at = fields.DatetimeField(auto_now_add=True)

class Order(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="orders")
    location = fields.ForeignKeyField("models.Location", related_name="orders")
    cylinder_type = fields.CharField(max_length=50)  # e.g. "Big", "Small"
    quantity = fields.IntField(default=1)
    status = fields.CharField(max_length=20, default="Pending")
    created_at = fields.DatetimeField(auto_now_add=True)