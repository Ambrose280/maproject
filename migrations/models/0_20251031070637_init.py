from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(254) NOT NULL UNIQUE,
    "phone" VARCHAR(20),
    "first_name" VARCHAR(100),
    "last_name" VARCHAR(100),
    "password_hash" VARCHAR(255) NOT NULL,
    "user_type" VARCHAR(20) NOT NULL DEFAULT 'user',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "dispatcherstatus" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "online" BOOL NOT NULL DEFAULT False,
    "lat" DOUBLE PRECISION,
    "long" DOUBLE PRECISION,
    "color" VARCHAR(20),
    "last_seen" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "dispatcher_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "location" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100),
    "lat" DOUBLE PRECISION NOT NULL,
    "long" DOUBLE PRECISION NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmm1v2joUx78KyqtO4k4tg22678JDNe4oTEDvnTZNkUkMRDU2i511aOp3v7bz4MR5GF"
    "kLhSqvWo7PiY9/Pnb+tvLL2BAHIvq679ItYPYaejMGmE+Nvxu/DAw2kP9T6NNsGGC7VR7C"
    "wMACySAn9qbKe0GZB2zG25cAUchNDqS2526ZSzC3Yh8hYSQ2d3TxSpl87H73ocXICjL+TN"
    "7w9Rs3u9iBPyGNfm7vrKULkZNK33VE39Jusd1W2oaYXUtH0dvCsgnyN1g5b3dsTXDs7WIm"
    "rCuIoQcYFI9nni/SF9mFI45GFGSqXIIUEzEOXAIfscRw92RgEyz48WyC+VmJXv5qXbXftd"
    "+/edt+z11kJrHl3UMwPDX2IFASGM+NB9kOGAg8JEbFjWDkYphl1yUEQYDz+akgjeGCR+kQ"
    "I2RlFCODwqhKJ+JYtZg0kCWUupPJSGS9ofQ7kobhXPwmvIyDOh/f3nQH04urV8LMnVwGk3"
    "gVTgRYluU1IqCgEkN/DeNSBOzBMay1ShgfV44lFPuT2+5o0Pg0HfSGs+FkLInuQqJBY5re"
    "dGCOdHyE912JXxhQAwwAcjLEyxLsrYGXDzAO0AjynE+Sn7EBPy0E8YqtxSZ4WcLzX3Pa+2"
    "BOL1qXr7TVHLa0ZJO+gCmzKIQ4C7HPOTB3A4tWciJQg+mEka+jfw61Rz6SrQeBM8FoF85s"
    "Cdv58GYwm5s3n1L7Zt+cD0RLK126ofXirTYP8UMa/w3nHxriZ+PLZCyrfEsoW3myR+U3/2"
    "KInIDPiIXJvQWcxBs3sqrk1awqnWJVEgqZuN9rhhOZyieQDUJrLe9yVYPikrNbEw+6K/wR"
    "7iTTIc8LYDtPLYSS85bCffaao0uvh6gaIqvqwgP3sQbNFgkfIh8YDDbpnjnrmf2BIXEugH"
    "13DzzHSnEVLaRFNEvsm23atDa6BWCwkhDEWETmIdwRsUE48IzWj9uaZRofJb1qbX9ii7RZ"
    "ou3l3wpaIPI/SylwdbmPFuBehWJAtj2nnH+G98QL0/Mvj6DNNRkfrpVXiOWCNB1ZK9JnVa"
    "QSTGpifVpVjCYiahkaM3xGAXq0zeW3EjRRGqckPiXYHOEZAS8WndHM1oLz1JZjmeCEG+Ci"
    "KoozDvgjyXl8funLp057n9unTrv4+km0pd/3W46hkmiPA85StT/9Bd7S9Sizqh590lFnif"
    "JAB6A/gJkKqlnGSxtQek/4O3UN6LrSEtcDn2a3PPpa73T22i87JftlR4cqlY8EUQFoKuh4"
    "MGNVc6JbZ33WfEFnzcyxqfgIoCpAfcWhfQ0Qxl1/nEIU3wbnn6byviA5vdkuOllp11fB1f"
    "cjiSTv2c+IxCFPhib0XHtt5JwNw5Zm2ekQKJ/6fPiUW+CBz4c/oEfDdbDvqzoRUqueGKRY"
    "GhUghu7nCfAgWpz3yCDO0Tn/zCbjoi9l4hAN5C3mA/zquDZrNpBL2bfTxFpCUYw6pWUieB"
    "c35meda2806eoiRTygm3dZe8yLx4f/AbHCw0A="
)
