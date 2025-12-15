import httpx
from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from tortoise.contrib.fastapi import register_tortoise
from passlib.context import CryptContext
from models import User, Cylinder, Order

import shutil
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

# Config
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# --- MOUNT STATIC FILES ---
# This allows us to access images at http://localhost:8000/static/uploads/filename.jpg
app.mount("/static", StaticFiles(directory="static"), name="static")
# 1. SECURITY & CONFIG
SECRET_KEY = "super-secret-key-change-this"
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Paystack & Mapbox Keys
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET")
PAYSTACK_PUBLIC = os.getenv("PAYSTACK_PUBLIC")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- HELPER: SAVE IMAGE ---
def save_image(file: UploadFile) -> str:
    # Create a unique filename to prevent overwriting
    file_extension = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"static/uploads/{file_name}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return f"/{file_path}" # Return web-accessible path

# --- HELPERS ---
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if user_id:
        return await User.get_or_none(id=user_id)
    return None

# --- AUTH ROUTES ---

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, full_name: str = Form(...), email: str = Form(...), password: str = Form(...), phone: str = Form(...)):
    if await User.filter(email=email).exists():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already exists"})
    
    hashed = get_password_hash(password)
    await User.create(full_name=full_name, email=email, password_hash=hashed, phone=phone)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = await User.get_or_none(email=email)
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    request.session["user_id"] = user.id
    # Redirect admin to dashboard, user to home
    if user.is_admin:
        return RedirectResponse(url="/admin", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# --- CORE ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = await get_current_user(request)
    cylinders = await Cylinder.all()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user": user, 
        "cylinders": cylinders,
        "paystack_key": PAYSTACK_PUBLIC
    })

@app.post("/verify-payment")
async def verify_payment(request: Request, data: dict):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please login first")

    reference = data.get('reference')
    cylinder_id = data.get('cylinder_id')
    coords = data.get('coords', {})

    # Verify with Paystack
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
    
    if resp.status_code == 200 and resp.json()['data']['status'] == 'success':
        paystack_data = resp.json()['data']
        cylinder = await Cylinder.get(id=cylinder_id)
        
        await Order.create(
            user=user,
            guest_name=user.full_name,
            cylinder=cylinder,
            amount_paid=paystack_data['amount'] / 100,
            paystack_ref=reference,
            is_paid=True,
            latitude=coords.get('lat'),
            longitude=coords.get('lng')
        )
        return JSONResponse({"status": "success"})
    
    raise HTTPException(status_code=400, detail="Verification failed")



@app.get("/my-orders", response_class=HTMLResponse)
async def my_orders(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
  
    orders = await Order.filter(user=user).all().order_by('-created_at').prefetch_related('cylinder')
    return templates.TemplateResponse("my_orders.html", {"request": request, "user": user, "orders": orders})

# --- ADMIN ROUTES ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = await get_current_user(request)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login")
    
    # Fetch Orders
    orders = await Order.filter(is_paid=True).all().order_by('-created_at').prefetch_related('cylinder', 'user')
    # Fetch Products (Cylinders) for the Inventory Tab
    cylinders = await Cylinder.all().order_by('price')
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user, 
        "orders": orders,
        "cylinders": cylinders
    })

# --- PRODUCT MANAGEMENT ROUTES ---

@app.post("/admin/cylinder/add")
async def add_cylinder(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    file: UploadFile = File(...) # Expect a file now
):
    user = await get_current_user(request)
    if not user or not user.is_admin: return RedirectResponse("/")

    # Save the file to disk
    image_url = save_image(file)

    await Cylinder.create(name=name, price=price, image_url=image_url)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/cylinder/edit/{id}")
async def edit_cylinder(
    request: Request,
    id: int,
    name: str = Form(...),
    price: float = Form(...),
    file: UploadFile = File(None) # File is Optional here
):
    user = await get_current_user(request)
    if not user or not user.is_admin: return RedirectResponse("/")

    cylinder = await Cylinder.get(id=id)
    
    # Update text fields
    cylinder.name = name
    cylinder.price = price

    # Only update image if a NEW file was uploaded
    if file and file.filename:
        # (Optional: You could delete the old image file here to save space)
        cylinder.image_url = save_image(file)

    await cylinder.save()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin/cylinder/delete/{id}")
async def delete_cylinder(request: Request, id: int):
    user = await get_current_user(request)
    if not user or not user.is_admin: return RedirectResponse("/")

    await Cylinder.filter(id=id).delete()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = await get_current_user(request)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login")
        
    orders = await Order.filter(is_paid=True).all().order_by('-created_at').prefetch_related('cylinder', 'user')
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "orders": orders})

@app.get("/admin/track/{order_id}", response_class=HTMLResponse)
async def track_order(request: Request, order_id: int):
    user = await get_current_user(request)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login")

    order = await Order.get(id=order_id).prefetch_related('cylinder', 'user')
    return templates.TemplateResponse("tracking.html", {
        "request": request, 
        "order": order, 
        "mapbox_token": os.getenv("MAPBOX_TOKEN")
    })


@app.on_event("startup")
async def startup_event():
    # Seed Data
    if await Cylinder.all().count() == 0:
        await Cylinder.create(name="3kg Camp Gas", price=2500)
        await Cylinder.create(name="12.5kg Home Cylinder", price=12500)
        await Cylinder.create(name="50kg Industrial", price=45000)
    
    # Create Default Admin (Email: admin@gas.com, Pass: admin123)
    if not await User.filter(email="admin@gas.com").exists():
        hashed = get_password_hash("admin123")
        await User.create(full_name="Super Admin", email="admin@gas.com", password_hash=hashed, is_admin=True)

register_tortoise(
    app,
    db_url=os.getenv("DATABASE_URL"),
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)