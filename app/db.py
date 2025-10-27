from passlib.context import CryptContext
from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Create the database driver
try:
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
        keep_alive=True
    )

    # Test connection once on startup
    with driver.session() as session:
        session.run("RETURN 1 AS test")
    print("✅ Successfully connected to Neo4j AuraDB!")

except Exception as e:
    # If we can't connect at import time (for example during local development
    # without network access to AuraDB), don't raise here - allow the app to
    # start and fail later when a DB operation is attempted. Keep driver as
    # None so callers can detect the absence of a connection.
    print("❌ Failed to connect to Neo4j AuraDB:", e)
    driver = None

# Password hashing setup
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_db():
    return driver

def hash_password(password: str) -> str:
    if len(password) > 500:
        password = password[:500]
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password) > 500:
        plain_password = plain_password[:500]
    return pwd_context.verify(plain_password, hashed_password)
