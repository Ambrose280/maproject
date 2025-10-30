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
from models import User, Location, Order, DispatcherStatus, OrderShareCode
import aiofiles
from tortoise.exceptions import DoesNotExist
import cloudinary
from tortoise.transactions import in_transaction
import cloudinary.uploader

load_dotenv()

# Config
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
SESSION_KEY = os.getenv("SESSION_KEY", secrets.token_urlsafe(32))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Cloudinary
CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUD_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUD_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUD_AVAILABLE = CLOUD_NAME and CLOUD_KEY and CLOUD_SECRET
if CLOUD_AVAILABLE:
    cloudinary.config(cloud_name=CLOUD_NAME, api_key=CLOUD_KEY, api_secret=CLOUD_SECRET, secure=True)

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

async def save_upload(file: UploadFile):
    name = f"{int(datetime.utcnow().timestamp())}_{file.filename.replace(' ', '_')}"
    local_path = os.path.join(UPLOAD_DIR, name)
    async with aiofiles.open(local_path, "wb") as out:
        content = await file.read()
        await out.write(content)
    if CLOUD_AVAILABLE:
        try:
            res = cloudinary.uploader.upload(local_path, folder="quasar_uploads")
            return res.get("secure_url") or local_path
        except Exception:
            return local_path
    return local_path

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
    username = form.get("username", "").strip()
    password = form.get("password", "")
    user_type = form.get("user_type", "user")
    if not username or not password:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "All fields required", "user": await get_current_user(request)})
    if await User.filter(username=username).exists():
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Username taken", "user": await get_current_user(request)})
    user = User(username=username, user_type=user_type)
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
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    user = await User.get_or_none(username=username)
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
        "username": ds.dispatcher.username,
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

# ---------- Orders ----------
@app.post("/place_order")
async def place_order(request: Request, title: str = Form(...), location_id: int = Form(...), quantity: int = Form(1), cylinder_type: str = Form(None), image: UploadFile = File(...)):
    user = await get_current_user(request)
    if not user or user.user_type != "user":
        raise HTTPException(status_code=401, detail="Unauthorized")
    loc = await Location.get_or_none(id=location_id, user=user)
    if not loc:
        raise HTTPException(status_code=400, detail="Invalid location")
    saved = await save_upload(image)
    code = secrets.token_urlsafe(8)
    order = await Order.create(
        code=code,
        user=user,
        location=loc,
        title=title,
        image_path=saved,
        quantity=int(quantity),
        cylinder_type=cylinder_type,
        status="Pending"
    )
    return JSONResponse({"message": "Order placed", "order_id": order.id, "code": code})
def serialize_tortoise_model(obj):
    from datetime import datetime
    return {
        k: (v.isoformat() if isinstance(v, datetime) else v)
        for k, v in obj.__dict__.items()
        if not k.startswith("_")
    }

@app.get("/my_orders_json")
async def my_orders_json(request: Request):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    orders = await Order.filter(user=user).all()
    return JSONResponse([serialize_tortoise_model(o) for o in orders])

@app.delete("/delete_location/{loc_id}")
async def delete_location(loc_id: int):
    loc = await Location.get_or_none(id=loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    await loc.delete()
    return {"success": True}

@app.get("/api/orders")
async def api_orders(request: Request):
    orders = await Order.filter(status__in=["Pending"]).prefetch_related("user", "location").order_by("created_at")
    out = []
    for o in orders:
        out.append({
            "id": o.id,
            "title": o.title,
            "status": o.status,
            "image_path": o.image_path,
            "location": {"name": o.location.name if o.location else None, "lat": o.location.lat if o.location else None, "long": o.location.long if o.location else None},
            "code": o.code
        })
    return JSONResponse(out)


@app.post("/generate_share_link/{order_id}")
async def generate_share_link(order_id: int, request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    order = await Order.get_or_none(id=order_id, user_id=user_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    share_code = await order.generate_share_code()
    link = str(request.base_url).rstrip("/") + f"/share/{share_code.code}"
    return JSONResponse({"link": link})


@app.get("/share/{code}", response_class=HTMLResponse, name="view_shared_order")
async def view_shared_order(request: Request, code: str):
    share = await OrderShareCode.get_or_none(code=code).prefetch_related(
        "order", "order__location", "order__user"
    )

    if not share:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    return templates.TemplateResponse("order_detail.html", {
        "request": request,
        "order": share.order,
        "share": share
    })

@app.post("/share/{code}/accept")
async def accept_shared_order(code: str, request: Request):
    data = await request.json()
    lat = data.get("lat")
    long = data.get("long")

    share = await OrderShareCode.get_or_none(code=code).prefetch_related("order")
    if not share:
        raise HTTPException(status_code=404, detail="Invalid share code")

    if share.accepted:
        raise HTTPException(status_code=400, detail="This order has already been accepted")

    async with in_transaction():
        share.accepted = True
        share.accepted_lat = lat
        share.accepted_long = long
        await share.save()

        order = share.order
        order.status = "accepted"
        await order.save()

    return {
        "message": "Order accepted successfully",
        "order_id": order.id,
        "status": order.status
    }


@app.post("/dispatcher/decline_order/{order_id}")
async def decline_order(order_id: int, request: Request):
    user = await get_current_user(request)
    if not user or user.user_type != "dispatcher":
        raise HTTPException(status_code=401, detail="Unauthorized")
    order = await Order.get_or_none(id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = "Declined"
    await order.save()
    return JSONResponse({"message": "Declined", "order_id": order.id})

@app.get("/order_status/{order_id}")
async def order_status(order_id: int, request: Request):
    order = await Order.get_or_none(id=order_id).prefetch_related("dispatcher", "location")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    dispatcher_coords = {}
    if order.dispatcher:
        ds = await DispatcherStatus.get_or_none(dispatcher=order.dispatcher)
        if ds:
            dispatcher_coords = {"dispatcher": order.dispatcher.username, "dispatcher_lat": ds.lat, "dispatcher_long": ds.long}
    return JSONResponse({
        "id": order.id,
        "status": order.status,
        "dispatcher": order.dispatcher.username if order.dispatcher else None,
        "image_path": order.image_path,
        "location": {"name": order.location.name if order.location else None, "lat": order.location.lat if order.location else None, "long": order.location.long if order.location else None},
        **dispatcher_coords,
        "updated_at": order.updated_at.isoformat()
    })

@app.get("/track/{code}", response_class=HTMLResponse)
async def track_code(code: str, request: Request):
    order = await Order.get_or_none(code=code).prefetch_related("location", "dispatcher")
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    return templates.TemplateResponse("track.html", {"request": request, "order": order})

@app.get("/accepted_orders_json")
async def get_accepted_orders():
    orders = await Order.filter(status="accepted").values("id", "title", "status")
    return orders

@app.post("/dispatch_order")
async def dispatch_order(order_id: int = Form(...)):
    order = await Order.get_or_none(id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Example: create a dispatch record (you can make a Dispatch model)
    dispatch = await Dispatch.create(order=order, status="enroute")
    order.status = "dispatched"
    await order.save()

    return {"message": "Order dispatched successfully", "dispatch_id": dispatch.id}

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
