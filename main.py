import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from tortoise.contrib.fastapi import register_tortoise
from datetime import datetime
import aiofiles
from models import User, Location, Order, DispatcherStatus
from datetime import timedelta
# ---------- ENV ----------
load_dotenv()
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
SESSION_KEY = os.getenv("SESSION_KEY", "change-me")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------- APP ----------
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_KEY)
templates = Jinja2Templates(directory="templates")
templates.env.globals["MAPBOX_TOKEN"] = MAPBOX_TOKEN
from datetime import datetime
templates.env.globals['current_year'] = datetime.now().year

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- DISPATCHER COLORS ----------
COLOR_PALETTE = [
    "#e6194b","#3cb44b","#ffe119","#4363d8","#f58231","#911eb4","#46f0f0",
    "#f032e6","#bcf60c","#fabebe","#008080","#e6beff","#9a6324","#fffac8",
    "#800000","#aaffc3","#808000","#ffd8b1","#000075","#808080"
]

# ---------- UTILS ----------
async def get_current_user(request: Request):
    """Return current logged in user or None"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return await User.get_or_none(id=user_id)

async def assign_color_for_dispatcher():
    """Assign unique color for dispatcher"""
    used = await DispatcherStatus.all().values_list("color", flat=True)
    for c in COLOR_PALETTE:
        if c not in used:
            return c
    return COLOR_PALETTE[0]

# ---------- AUTH ROUTES ----------
@app.get("/signup", response_class=HTMLResponse)
async def signup_get(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})


@app.post("/signup", response_class=HTMLResponse)
async def signup_post(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    user_type = form.get("user_type", "user")

    if not username or not password:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "All fields are required"})

    if await User.filter(username=username).exists():
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Username already exists"})

    user = User(username=username, user_type=user_type)
    await user.set_password(password)
    await user.save()

    # If dispatcher, create a DispatcherStatus record
    if user_type == "dispatcher":
        color = await assign_color_for_dispatcher()
        await DispatcherStatus.create(dispatcher=user, online=False, color=color)

    # ✅ Initialize session after signup
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["user_type"] = user_type

    # ✅ Redirect to proper dashboard
    if user_type == "dispatcher":
        return RedirectResponse("/dispatcher/dashboard", status_code=303)
    return RedirectResponse("/user/dashboard", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    user = await User.get_or_none(username=username)
    if not user or not await user.verify_password(password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})

    # ✅ Initialize session
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["user_type"] = user.user_type

    # ✅ Ensure dispatcher has status record
    if user.user_type == "dispatcher":
        if not await DispatcherStatus.get_or_none(dispatcher=user):
            color = await assign_color_for_dispatcher()
            await DispatcherStatus.create(dispatcher=user, online=False, color=color)
        return RedirectResponse("/dispatcher/dashboard", status_code=303)
    return RedirectResponse("/user/dashboard", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    """Clear session and logout"""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

# ---------- USER DASHBOARD ----------
@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "user":
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("user_dashboard.html", {"request": request, "user": user, "mapbox_token": MAPBOX_TOKEN})

# ---------- DISPATCHER DASHBOARD ----------
@app.get("/dispatcher/dashboard", response_class=HTMLResponse)
async def dispatcher_dashboard(request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        return RedirectResponse("/login", status_code=303)

    ds = await DispatcherStatus.get_or_none(dispatcher=user)
    orders = await Order.filter(status__in=["Pending", "Accepted", "In Transit"]).prefetch_related("user", "location")

    return templates.TemplateResponse(
        "dispatcher_dashboard.html",
        {"request": request, "user": user, "dispatch_status": ds, "orders": orders, "mapbox_token": MAPBOX_TOKEN}
    )

# ---------- AJAX ENDPOINTS ----------
@app.post("/dispatcher/toggle_online")
async def toggle_online(request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        raise HTTPException(401, "Unauthorized")

    ds = await DispatcherStatus.get_or_none(dispatcher=user)
    if not ds:
        color = await assign_color_for_dispatcher()
        ds = await DispatcherStatus.create(dispatcher=user, online=False, color=color)

    ds.online = not ds.online
    ds.last_seen = datetime.utcnow()
    await ds.save()

    return JSONResponse({"online": ds.online})


@app.post("/dispatcher/update_location")
async def dispatcher_update_location(request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        raise HTTPException(401, "Unauthorized")

    data = await request.json()
    ds = await DispatcherStatus.get_or_none(dispatcher=user)
    if not ds:
        color = await assign_color_for_dispatcher()
        ds = await DispatcherStatus.create(dispatcher=user, online=True, color=color)

    ds.lat = data.get("lat")
    ds.long = data.get("long")
    ds.last_seen = datetime.utcnow()
    await ds.save()

    return JSONResponse({"ok": True})



@app.get("/api/dispatchers")
async def api_dispatchers():
    now = datetime.utcnow()
    timeout = timedelta(days=1)  # they stay online for 1 day unless manually marked offline

    async for ds in DispatcherStatus.all().prefetch_related("dispatcher"):
        if (now - ds.last_seen.replace(tzinfo=None)) > timeout:
            if ds.online:
                ds.online = False
                await ds.save()

    ds_list = await DispatcherStatus.filter(online=True).prefetch_related("dispatcher")
    result = [{
        "id": ds.dispatcher.id,
        "username": ds.dispatcher.username,
        "lat": ds.lat,
        "long": ds.long,
        "color": ds.color,
        "last_seen": ds.last_seen.isoformat()
    } for ds in ds_list]
    return JSONResponse(result)


@app.post("/api/update_status/{dispatcher_id}")
async def update_status(dispatcher_id: int, lat: float, long: float):
    ds = await DispatcherStatus.get_or_none(dispatcher_id=dispatcher_id)
    if ds:
        ds.lat, ds.long = lat, long
        ds.last_seen = datetime.utcnow()
        ds.online = True
        await ds.save()
        return {"status": "updated"}
    return {"status": "not found"}


# ---------- ORDERS ----------
@app.post("/place_order")
async def place_order(
    request: Request,
    title: str = Form(...),
    location_id: int = Form(...),
    quantity: int = Form(1),
    cylinder_type: str = Form(None),
    image: UploadFile = File(...)
):
    user = await get_current_user(request)
    if not user or user.user_type != "user":
        raise HTTPException(401, "Unauthorized")

    loc = await Location.get_or_none(id=location_id, user=user)
    if not loc:
        raise HTTPException(400, "Invalid location")

    safe_name = f"{int(datetime.utcnow().timestamp())}_{image.filename.replace(' ', '_')}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)
    async with aiofiles.open(save_path, 'wb') as out_file:
        await out_file.write(await image.read())

    order = await Order.create(
        user=user,
        location=loc,
        title=title,
        image_path=save_path,
        quantity=quantity,
        cylinder_type=cylinder_type,
        status="Pending"
    )
    return JSONResponse({"message": "Order placed", "order_id": order.id})


@app.post("/dispatcher/accept_order/{order_id}")
async def accept_order(order_id: int, request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        raise HTTPException(401, "Unauthorized")

    order = await Order.get_or_none(id=order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    order.status = "Accepted"
    order.dispatcher = user
    await order.save()

    return JSONResponse({"message": "Order accepted"})


@app.post("/dispatcher/decline_order/{order_id}")
async def decline_order(order_id: int, request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        raise HTTPException(401, "Unauthorized")

    order = await Order.get_or_none(id=order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    order.status = "Declined"
    await order.save()

    return JSONResponse({"message": "Order declined"})

# ---------- STATIC FILES ----------
@app.get("/uploads/{filename}")
async def uploaded_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Not found")
    return FileResponse(path)

# ---------- DATABASE CONFIG ----------
TORTOISE_ORM = {
    "connections": {"default": DATABASE_URL},
    "apps": {"models": {"models": ["models", "aerich.models"], "default_connection": "default"}},
}

register_tortoise(app, config=TORTOISE_ORM, add_exception_handlers=True)
