import os
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from tortoise.contrib.fastapi import register_tortoise
from models import User, Location, DispatcherStatus
import aiofiles
from tortoise.exceptions import DoesNotExist
import cloudinary
from tortoise.transactions import in_transaction
import cloudinary.uploader

load_dotenv()

# Config
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SESSION_KEY = os.getenv("SESSION_KEY", secrets.token_urlsafe(32))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals["MAPBOX_TOKEN"] = MAPBOX_TOKEN
templates.env.globals["current_year"] = datetime.utcnow().year

# color palette
COLOR_PALETTE = [
    "#e6194b","#3cb44b","#ffe119","#4363d8","#f58231","#911eb4","#46f0f0","#f032e6","#bcf60c","#fabebe",
    "#008080","#e6beff","#9a6324","#fffac8","#800000","#aaffc3","#808000","#ffd8b1","#000075","#808080"
]

async def assign_color_for_dispatcher():
    used = await DispatcherStatus.all().values_list("color", flat=True)
    for c in COLOR_PALETTE:
        if c not in used:
            return c
    return COLOR_PALETTE[0]

async def get_current_user(request: Request):
    uid = request.session.get("user_id")
    if not uid:
        return None
    return await User.get_or_none(id=uid)



# ---------- Pages ----------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = await get_current_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/signup", response_class=HTMLResponse)
async def signup_get(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "error": None, "user": await get_current_user(request)})

@app.post("/signup", response_class=HTMLResponse)
async def signup_post(request: Request):
    form = await request.form()
    email = form.get("email", "").strip().lower()
    phone = form.get("phone", "").strip()
    first_name = form.get("first_name", "").strip()
    last_name = form.get("last_name", "").strip()
    password = form.get("password", "")
    user_type = form.get("user_type", "user")
    if not email or not password:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "All fields required", "user": await get_current_user(request)})
    if await User.filter(email=email).exists():
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered", "user": await get_current_user(request)})
    user = User(email=email, phone=phone, first_name=first_name or None, last_name=last_name or None, user_type=user_type)
    await user.set_password(password)
    await user.save()
    if user_type == "dispatcher":
        color = await assign_color_for_dispatcher()
        ds = DispatcherStatus(dispatcher=user, online=False, color=color)
        await ds.save()
    request.session["user_id"] = user.id
    return RedirectResponse("/dispatcher/dashboard" if user_type=="dispatcher" else "/dashboard", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "user": await get_current_user(request)})

@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request):
    form = await request.form()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "").strip()

    user = await User.get_or_none(email=email)
    if not user or not await user.verify_password(password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid credentials",
                "user": await get_current_user(request),
            },
        )

    # Save session
    request.session["user_id"] = user.id

    # Dispatcher dashboard
    if user.user_type == "dispatcher":
        ds = await DispatcherStatus.get_or_none(dispatcher=user)
        if not ds:
            color = await assign_color_for_dispatcher()
            ds = DispatcherStatus(dispatcher=user, online=False, color=color)
            await ds.save()
        return RedirectResponse("/dispatcher/dashboard", status_code=302)

    # Normal user dashboard
    elif user.user_type == "user":
        return RedirectResponse("/dashboard", status_code=302)

    # Default fallback (e.g., admin or undefined)
    return RedirectResponse("/", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse("/", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.user_type != "user":
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse(
        "user_dashboard.html",
        {"request": request, "user": user},
    )
# ---------- Dispatcher dashboard ----------
@app.get("/dispatcher/dashboard", response_class=HTMLResponse)
async def dispatcher_dashboard(request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        return RedirectResponse("/login", status_code=302)
    ds = await DispatcherStatus.get_or_none(dispatcher=user)
    return templates.TemplateResponse("dispatcher_dashboard.html", {"request": request, "user": user, "dispatch_status": ds})

@app.post("/dispatcher/toggle_online")
async def toggle_online(request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        raise HTTPException(status_code=401, detail="Unauthorized")
    ds = await DispatcherStatus.get_or_none(dispatcher=user)
    if not ds:
        color = await assign_color_for_dispatcher()
        ds = await DispatcherStatus(dispatcher=user, online=False, color=color)
    ds.online = not ds.online
    ds.last_seen = datetime.utcnow()
    await ds.save()
    return JSONResponse({"online": ds.online})

@app.post("/dispatcher/update_location")
async def dispatcher_update_location(request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = await request.json()
    ds = await DispatcherStatus.get_or_none(dispatcher=user)
    if not ds:
        color = await assign_color_for_dispatcher()
        ds = await DispatcherStatus.create(dispatcher=user, online=True, color=color, lat=data.get("lat"), long=data.get("long"))
    else:
        ds.lat = data.get("lat")
        ds.long = data.get("long")
        ds.last_seen = datetime.utcnow()
        ds.online = True
        await ds.save()
    return JSONResponse({"ok": True})

@app.get("/api/dispatchers")
async def api_dispatchers():
    # mark expired offline (60s) so front-end keeps markers until 60 seconds without update
    now = datetime.utcnow()
    timeout = timedelta(seconds=60)
    async for ds in DispatcherStatus.all().prefetch_related("dispatcher"):
        if (now - ds.last_seen.replace(tzinfo=None)) > timeout:
            if ds.online:
                ds.online = False
                await ds.save()
    ds_list = await DispatcherStatus.filter(online=True).prefetch_related("dispatcher")
    result = [{
        "id": ds.dispatcher.id,
        "email": ds.dispatcher.email,
        "first_name": ds.dispatcher.first_name,
        "last_name": ds.dispatcher.last_name,
        "phone": ds.dispatcher.phone,
        "lat": ds.lat,
        "long": ds.long,
        "color": ds.color,
        "last_seen": ds.last_seen.isoformat()
    } for ds in ds_list]
    return JSONResponse(result)

# ---------- Locations ----------
@app.post("/save_location")
async def save_location(request: Request):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    form = await request.form()
    lat = float(form.get("lat"))
    long = float(form.get("long"))
    name = form.get("name") or "Saved"
    loc = await Location.create(user=user, name=name, lat=lat, long=long)
    return JSONResponse({"message": "Saved", "id": loc.id})

@app.get("/get_all_locations")
async def get_all_locations(request: Request):
    user = await get_current_user(request)
    if not user:
        return JSONResponse([], status_code=200)
    locs = await Location.filter(user=user).order_by("-created_at").values("id", "name", "lat", "long", "created_at")
    for l in locs:
        if isinstance(l.get("created_at"), datetime):
            l["created_at"] = l["created_at"].isoformat()
    return JSONResponse(locs)

def serialize_tortoise_model(obj):
    from datetime import datetime
    return {
        k: (v.isoformat() if isinstance(v, datetime) else v)
        for k, v in obj.__dict__.items()
        if not k.startswith("_")
    }



@app.delete("/delete_location/{loc_id}")
async def delete_location(loc_id: int):
    loc = await Location.get_or_none(id=loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    await loc.delete()
    return {"success": True}




@app.get("/uploads/{filename}")
async def uploaded_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)

# DB
TORTOISE_ORM = {
    "connections": {"default": DATABASE_URL},
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],  
            "default_connection": "default",
        },
    },

}
register_tortoise(app, config=TORTOISE_ORM, add_exception_handlers=True)

@app.get("/demo/dispatchers")
async def demo_dispatchers():
    """
    Returns a small hard-coded list of demo dispatchers (for local/dev demo pages).
    """
    now_iso = datetime.utcnow().isoformat()
    demo = [
        {
            "id": 1001,
            "first_name": "Ubong",
            "last_name": "Jones",
            "email": "ubong.jones@example.com",
            "phone": "+2348012345678",
            "lat": 5.0321533867828725,
            "long": 7.9411077353157085,
            "color": "#e6194b",
            "last_seen": now_iso,
        },
        {
            "id": 1002,
            "first_name": "Unwana",
            "last_name": "Ambrose",
            "email": "unwana.ambrose@example.com",
            "phone": "+2348098765432",
            "lat": 5.015993712106818,
            "long": 7.9289197784636825,
            "color": "#3cb44b",
            "last_seen": now_iso,
        },
        {
            "id": 1003,
            "first_name": "Ifiok",
            "last_name": "Ambrose",
            "email": "ifiok.ambrose@example.com",
            "phone": "+2348071122334",
            "lat": 5.011504842537115,
            "long": 7.957029326837196,
            "color": "#4363d8",
            "last_seen": now_iso,
        },
    ]
    return JSONResponse(demo)

@app.get("/demo/dashboard", response_class=HTMLResponse)
async def demo_dashboard(request: Request):
    """
    Render the demo dashboard that consumes /demo/dispatchers for hard-coded demo dispatchers.
    """
    user = await get_current_user(request)
    return templates.TemplateResponse("demodashboard.html", {"request": request, "user": user})
