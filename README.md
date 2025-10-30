# Quasar Logistics - FastAPI + Tortoise + Tailwind + Mapbox + Cloudinary

## Setup
1. Create `.env` with:
   - MAPBOX_TOKEN=...
   - DATABASE_URL=sqlite://db.sqlite3
   - SESSION_KEY=some-secret
   - CLOUDINARY_CLOUD_NAME=...
   - CLOUDINARY_API_KEY=...
   - CLOUDINARY_API_SECRET=...

2. Install requirements:
   pip install -r requirements.txt

3. Initialize DB & migrations:
   aerich init -t main.TORTOISE_ORM
   aerich init-db
   aerich migrate
   aerich upgrade

4. Run:
   uvicorn main:app --reload

## Notes
- Use Cloudinary to store uploaded images; fallback to local `static/uploads` when Cloudinary not configured.
- Dispatcher expiry default = 60s; change in `main.py` (/api/dispatchers).
