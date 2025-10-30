from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ordersharecode" ADD "accepted_lat" REAL;
        ALTER TABLE "ordersharecode" ADD "accepted_long" REAL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ordersharecode" DROP COLUMN "accepted_lat";
        ALTER TABLE "ordersharecode" DROP COLUMN "accepted_long";"""


MODELS_STATE = (
    "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"
)
