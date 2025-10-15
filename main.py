import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
import random
import string
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from tortoise.contrib.fastapi import register_tortoise
from models import User, Location

# --- Load environment variables ---
load_dotenv()
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

# --- FastAPI setup ---
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="replace-this-with-a-secure-random-key")
templates = Jinja2Templates(directory="templates")


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
# --- Database registration ---
register_tortoise(
    app,
    db_url="sqlite://./db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
