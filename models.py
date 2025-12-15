from tortoise import fields, models
import datetime

class User(models.Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, unique=True)
    password_hash = fields.CharField(max_length=255)
    full_name = fields.CharField(max_length=255)
    phone = fields.CharField(max_length=20, null=True)
    is_admin = fields.BooleanField(default=False)

class Cylinder(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    image_url = fields.CharField(max_length=255, default="https://via.placeholder.com/150")

class Order(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='orders', null=True)
    # Guest details (if we want to allow guest checkout, though we will prioritize logged in users)
    guest_name = fields.CharField(max_length=100, null=True)
    
    # Location
    latitude = fields.CharField(max_length=50, null=True)
    longitude = fields.CharField(max_length=50, null=True)
    
    # Payment & Product
    cylinder = fields.ForeignKeyField('models.Cylinder', related_name='orders')
    amount_paid = fields.DecimalField(max_digits=10, decimal_places=2)
    paystack_ref = fields.CharField(max_length=100, unique=True)
    is_paid = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)