from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "username" VARCHAR(100) NOT NULL UNIQUE,
    "password_hash" VARCHAR(255) NOT NULL,
    "user_type" VARCHAR(20) NOT NULL DEFAULT 'user',
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "dispatcherstatus" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "online" INT NOT NULL DEFAULT 0,
    "lat" REAL,
    "long" REAL,
    "color" VARCHAR(20),
    "last_seen" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "dispatcher_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "location" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100),
    "lat" REAL NOT NULL,
    "long" REAL NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "order" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "image_path" TEXT,
    "quantity" INT NOT NULL DEFAULT 1,
    "status" VARCHAR(50) NOT NULL DEFAULT 'pending',
    "code" VARCHAR(50) NOT NULL UNIQUE DEFAULT '',
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "location_id" INT REFERENCES "location" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "ordersharecode" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "code" VARCHAR(100) NOT NULL UNIQUE,
    "accepted" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "accepted_by_id" INT REFERENCES "user" ("id") ON DELETE CASCADE,
    "order_id" INT NOT NULL REFERENCES "order" ("id") ON DELETE CASCADE
) /* Unique share link that someone can open to accept an order */;
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "/xA1pl75BVppZdNTFq82/wMe4egO"
)
