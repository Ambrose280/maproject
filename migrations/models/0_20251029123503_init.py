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
) /* Live dispatcher status for map display and online\/offline toggling. */;
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
    "title" VARCHAR(200),
    "image_path" VARCHAR(255),
    "cylinder_type" VARCHAR(50),
    "quantity" INT NOT NULL DEFAULT 1,
    "status" VARCHAR(20) NOT NULL DEFAULT 'Pending',
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "dispatcher_id" INT REFERENCES "user" ("id") ON DELETE SET NULL,
    "location_id" INT REFERENCES "location" ("id") ON DELETE SET NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
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
    "eJztm9lu2zgUhl9F0FUKeDKJJ26LufMW1FPHDrzMDFoUAi3RthCaVCS6qVH43UtSC7XHSr"
    "zIqa5ikedI5MdD8uch8lNdEQMi57JjOhag+hLaYwro2lH/Vn6qGKwg+5FpU1NUYFnSghdQ"
    "MEPCyQisHWk9c6gNdMrq5wA5kBUZ0NFt06Imwdyrb36HinRVXF9lTmxlBSxRg8BGAdhQCE"
    "Ymhn+S+Zz/VShZLNiPxSX/kEF09iX2tMd3rrH5uIYaK4OUvYa9+es3VmxiA/6Ajv9oPWhz"
    "EyIjAtA0+AtEuUY3lijrYXorDHlzZ5pO0HqFpbG1oUuCA2sTU166gBjagEL+emqvOUC8Rs"
    "hj7jN1WypN3CaGfAw4B2vEh4F7J0bBLwxB9Ip0gvkIsta4EbLgX/mjfn3z4ebjX+9vPjIT"
    "0ZKg5MPW7Z7su+soCAwm6lbUAwpcC4FRcnOHI8muRQiCAKfzk04xhjPmFYfoI8uj6BdIjD"
    "J4fY7p4bwzyBxKreGwz1u9cpxHJAp6E/5M2ERyZ9pgetfqji6u3/FiZmRSGMYrcSJAkyxv"
    "EQEZkejZxzDOucMOHL1YK4TxdeGYQ7EznLb6XeV+1G33xr3hQBDdeETdyii9UbfZj+Mj7N"
    "uF+HkOFUAXICND7CTB9hLY6QADhxhB1uZS8lNX4IeGIF7QJV8Er3J4/tsctT81Rxf1q3ex"
    "2ezV1EVVfAI7VHMgxEmIHcaBmiuYNZNDjjGYhud56f841Br5SrY2BMYQo403sjlsJ7277n"
    "jSvLuPrJud5qTLa+rR0PVKL97HxiF4ifJfb/JJ4Y/Kl+FARLlFHLqwxRel3eSLytsE1pRo"
    "mDxpwAjtuH6pbLwcVSlNtEJCIeH3vGYoyVDuQTZwrTV/SFUNkkvKak1saC7wZ7gRTHusXQ"
    "DraWrBE71TB+6y1hxdem39aPBL5Sds8BRo0GSQsC6yjkF3kW43x+1mp6sKnDOgPzwB29Ai"
    "XHkNqZNYSWCbrFrVV/ESgMFCQOB94S334PaJDryOJ04bQV0t75SBwlbPnS6y4Vba/ujaXv"
    "wtoAV8+7OUAtdXu2gBZpUpBkTdKeX8CfaJN6bn3x5BnWky1l0tLRDzBWnUs1KkJ1WkAkxk"
    "YNdOUTEa8qhkaMDwhAL0aIvLsxI0FBpFxWcoFWgb0HZSUoGe3+3nEUSBFExHOeTvKKVayE"
    "K5PaT6dnGkSO+AU7buJoFJJbpLtiTliW5qUlRIdQcOZym76zvJ7nqO7K4nZbe5YtNJY4fq"
    "ZRGQUa/zpNlo7EKz0cimyetiEnKDePttl0UBoAnHs2Ta2CVAG9nx2UiE5+MaYDZrNwUWyL"
    "DL8cTb9amXSclM3lDvGn3S40Vh9yJg6j3EhukeQUt6QVEdCN/qgdAyXjiwUc9qYKu7p5Pu"
    "vnveOfz7h2L0Yl6/KbsqyVQlmY6XZEqbtXsgF76mLN2M3RVebD2KABx3J8pg2u+rGfvG8a"
    "KvvPzyL9klwdPcsgu8KWk+H3t2ls9fXaokX9m2hFpOko+PWtHb9bDPfk60B6d4+At2CzjO"
    "E2HTbwmcQsm+hOPxkgSlT/iJjbposi/idMSMi78AVumWMgbrWzmVu+mWhMrf5Vo0K3NZ5F"
    "o07f96yjfamVekacL+lUQKiPqykmA7ENPgbIb/phfnYRbHRFCmeDjkoaIJbVNfqinHCq+m"
    "lnewANKmOlrsc0s88NHiO5tHqXmTbOkWcqlUsFye2dQoANEzP0+ABzmbsS9SiFN07z/j4S"
    "BD80qXGMgpZh38apg6rSnIdOi3cmLNoch7HdG2PryLu+b/ca7t/rAVF638Ba20XPMxc1bb"
    "X74FKVU="
)
