from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "username" VARCHAR(100) NOT NULL UNIQUE,
    "password_hash" VARCHAR(255) NOT NULL,
    "delivery" BOOL NOT NULL DEFAULT False
);
CREATE TABLE IF NOT EXISTS "location" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "lat" DOUBLE PRECISION NOT NULL,
    "long" DOUBLE PRECISION NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "order" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "cylinder_type" VARCHAR(50) NOT NULL,
    "quantity" INT NOT NULL DEFAULT 1,
    "status" VARCHAR(20) NOT NULL DEFAULT 'Pending',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "location_id" INT NOT NULL REFERENCES "location" ("id") ON DELETE CASCADE,
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
    "eJztmV1v2jAUhv8KylUrdVOblbbaXaBUZaWkonSbWlWRSQxYNTZ1nFFU9b/PdhLyzcgGHW"
    "y5ghyfE/s8ObFfO6/ahDoQux871AYcUaJ9rr1qBEyg+JNpO6hpYDqNWqSBgwFWzjjuNXA5"
    "AzYX9iHALhQmB7o2Q9OgD+JhLI3UFo6IjCKTR9CzBy1OR5CPIRMND4/CjIgDX6AbXk6frC"
    "GC2EkMFzmyb2W3+HyqbG3CL5Sj7G1g2RR7ExI5T+d8TMnCGxEurSNIIAMcyttz5snhy9EF"
    "mYYZ+SONXPwhxmIcOAQe5rF0V2RgUyL5idG4KsGR7OWDfnR8enz26eT4TLiokSwsp29+el"
    "HufqAi0O1rb6odcOB7KIwRN/WbIdccA5aPLvRPwRNDTsMLUS2jFxoifFHJrInfBLxYGJIR"
    "H4vLo8PDJbS+Gr3mpdHbE177Mhsqytiv727QpPttEmmEEAOeJXiBKSiovsA/RXAoA7aT4R"
    "Jk5+Zdo9Oq3fRazfZt2+zKBCZz9xlHjdIkDIirNHsto5PmR0XfpQAGARXBgKDNoEzXyivE"
    "c9HC0QTmo0xGpoA6QejH8M92wtVEDo5J8DyYfZfA7revW7d94/pGUXZDyka/JVv0JPvAun"
    "eSmgwWN6l9a/cva/Kydm921WOaUpePmOox8uvfa3JMwOPUInRmASe2UITWEEziwXouZFap"
    "pS0W8ev1bUue3xqWOKkLhk+5K5wkkjO9UAbRiFzBueLYFiMCxM5b2gIhdBfcZvv4vYU1EF"
    "qj4mJgttBK8dIQ6YmkoD+hNI3bpnHe0hTEAbCfZoA5VgFNyhzI3CzPRhB3cdWDeKEF81Ga"
    "8h67xVKxoTqNMUnQyjZN9EnaAggYqVHLvmVPCR454nsBqlh504VLJbu3bE5aJrvtOZZjZz"
    "6GEvo7E7ibQry+ig6vF8vwekaFP3uAcMTnJeoxHvJ+i+XR367KiJlY87iXM5kXl18U8X51"
    "p91A4iBf8q+l+PRVik8vLj49U3yVAP9HBXh4sFVOhKei/ichXu1efgNatXtZw+4l77VdA7"
    "n4Afju0kvNSGX3f5vc/ajSzNn8hCVbvPcJ341q67NtE9rBkq2PfGplvzrEY9YjPDdOcfPf"
    "HabAdWdi/2+NgTsuQzMTuJt7SL1eX0XH1+vFQl62JaGKSQb9gCxnG9mgFENA8pHGw1I0By"
    "JuUzjLTnerf5ZomGYnodEb7X4K4911oyWKdj/5eaJA0axythguUn94vLibK3aiCqtT1vXr"
    "DAMyZI/zlEbQslRrgMinUhs7pDbEpOzmbgSKl8dYSLUwLkDKV6MExMB9NwFuRK6JHjkkOQ"
    "eEX27NbsHhYBSSAnlHRIIPDrL5QQ0jlz9uJ9YlFGXWCYERwtu7Nr6nuTY7ZiN9uidv0Cgn"
    "Nda/vLz9BBD9nbI="
)
