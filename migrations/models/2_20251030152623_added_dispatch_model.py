from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "dispatch" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "status" VARCHAR(50) NOT NULL DEFAULT 'enroute',
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "order_id" INT NOT NULL REFERENCES "order" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "dispatch";"""


MODELS_STATE = (
    "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"
)
