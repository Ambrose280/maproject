import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
import secrets
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from tortoise.contrib.fastapi import register_tortoise
from models import User, Location, Order
from tortoise.exceptions import DoesNotExist

# --- Load environment variables ---
load_dotenv()
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

# --- FastAPI setup ---
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="replace-this-with-a-secure-random-key")
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

async def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return await User.get_or_none(id=user_id)




# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user_id = request.session.get("user_id")
    user = None
    locations = []

    if user_id:
        user = await User.get_or_none(id=user_id)
        if user:
            locations = await Location.filter(user=user).order_by("-created_at").all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "locations": locations,
        "mapbox_token": MAPBOX_TOKEN
    })


@app.get("/signup", response_class=HTMLResponse)
async def signup_get(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})


@app.post("/signup", response_class=HTMLResponse)
async def signup_post(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")

    if not username or not password:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Username and password required"})

    exists = await User.filter(username=username).exists()
    if exists:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Username already taken"})

    user = User(username=username)
    await user.set_password(password)  # 🔐 Hash password before saving
    await user.save()

    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")

    user = await User.get_or_none(username=username)
    if not user or not await user.verify_password(password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse("/", status_code=302)

@app.get("/get_latest_location")
async def get_latest_location(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    location = await Location.filter(user_id=user_id).order_by("-created_at").first()
    if not location:
        return JSONResponse({"message": "No location found"}, status_code=404)

    return JSONResponse({"name": location.name, "lat": location.lat, "long": location.long, "created_at": str(location.created_at)})

@app.get("/get_all_locations")
async def get_all_locations(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse([], status_code=200)

    locations = await Location.filter(user_id=user_id).order_by('-created_at').values(
        "id", "name", "lat", "long", "created_at"
    )

    for loc in locations:
        if isinstance(loc.get("created_at"), datetime):
            loc["created_at"] = loc["created_at"].isoformat()

    return JSONResponse(locations)

@app.delete("/delete_location/{loc_id}")
async def delete_location(request: Request, loc_id: int):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    location = await Location.get_or_none(id=loc_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Security Check: Ensure the location belongs to the logged-in user
    if location.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this location")

    await location.delete()
    return {"status": "deleted"}

@app.post("/save_location")
async def save_location(request: Request):
    data = await request.json()

    lat = data.get("lat")
    long = data.get("long")
    name = data.get("name")

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    user = await User.get_or_none(id=user_id)
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    loc = await Location.create(user=user, name=name, lat=lat, long=long)
    
    new_loc_data = {
        "id": loc.id,
        "name": loc.name,
        "lat": loc.lat,
        "long": loc.long,
        "created_at": str(loc.created_at)
    }
    return JSONResponse({"message": "Location saved", "data": new_loc_data})


@app.get("/order", response_class=HTMLResponse)
async def order_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    if user.delivery:
        return RedirectResponse("/orders", status_code=303)

    locations = await Location.filter(user=user)
    return templates.TemplateResponse("order.html", {"request": request, "locations": locations, "user": user})



@app.get("/orders", response_class=HTMLResponse)
async def list_orders(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not user.delivery:
        return RedirectResponse("/", status_code=303)

    orders = await Order.all().prefetch_related("location", "user")

    order_data = [
        {
            "id": order.id,
            "customer_name": order.user.username if order.user else "Unknown",
            "location_name": order.location.name if order.location else "No location",
        }
        for order in orders
    ]

    return templates.TemplateResponse(
        "orders.html",
        {"request": request, "orders": order_data, "user": user}
    )


@app.post("/place_order")
async def place_order(request: Request):
    data = await request.json()
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if user.delivery:
        return JSONResponse({"error": "Delivery men cannot place orders"}, status_code=403)
    
    cylinder_type = data.get("cylinder_type")
    quantity = int(data.get("quantity", 1))
    location_id = data.get("location_id")
    
    location = await Location.get_or_none(id=location_id, user_id=user.id)
    if not location:
        return JSONResponse({"error": "Invalid location"}, status_code=400)
    
    order = await Order.create(
        user=user,
        location=location,
        cylinder_type=cylinder_type,
        quantity=quantity
    )
    return JSONResponse({"message": "Order placed", "order": jsonable_encoder(order)})

@app.get("/route/{order_id}", response_class=HTMLResponse)
async def delivery_route(request: Request, order_id: int):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not user.delivery:
        return RedirectResponse("/", status_code=303)

    order = await Order.get_or_none(id=order_id).prefetch_related("location", "user")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    customer_location = {
        "name": order.location.name,
        "lat": order.location.lat,
        "long": order.location.long
    }

    return templates.TemplateResponse(
        "route.html",
        {
            "request": request,
            "mapbox_token": MAPBOX_TOKEN,
            "customer_location": customer_location,
            "order_id": order.id,
            "user": user
        }
    )
@app.get("/my-orders", response_class=HTMLResponse)
async def my_orders(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please log in first.")

    user = await User.get_or_none(id=user_id).prefetch_related("orders__location")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Convert order data
    orders = []
    for order in user.orders:
        location_name = getattr(order.location, "name", "No location")
        orders.append({
            "id": order.id,
            "status": getattr(order, "status", "Pending"),
            "location": location_name,
            "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return templates.TemplateResponse(
        "my_orders.html",
        {"request": request, "user": user, "orders": orders},
    )

@app.get("/test-db")
async def test_db():
    user = await User.get(username='IFKLogistics')
    user.delivery = True
    await user.save()
#     # await User.all().delete()
#     user = User(username='IFKLogistics')
#     await user.set_password('12345678')
#     await user.save()




TORTOISE_ORM = {
    "connections": {"default": os.getenv("DATABASE_URL")},
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        },
    },
}

register_tortoise(
    app,
    config=TORTOISE_ORM,
    add_exception_handlers=True,
)


# aerich init -t main.TORTOISE_ORM
# aerich init-db
# aerich migrate
# aerich upgrade
