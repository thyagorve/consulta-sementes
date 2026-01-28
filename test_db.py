import environ
import os
from pathlib import Path
import psycopg2

BASE_DIR = Path(__file__).resolve().parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

print("ENV VARS:")
for k in [
    "DATABASE_NAME",
    "DATABASE_USER",
    "DATABASE_PASSWORD",
    "DATABASE_HOST",
    "DATABASE_PORT",
]:
    print(k, "=>", repr(env(k, default=None)))

print("\nTentando conectar...\n")

conn = psycopg2.connect(
    dbname=env("DATABASE_NAME"),
    user=env("DATABASE_USER"),
    password=env("DATABASE_PASSWORD"),
    host=env("DATABASE_HOST"),
    port=env("DATABASE_PORT"),
)

print("Conectado com sucesso!")
conn.close()
