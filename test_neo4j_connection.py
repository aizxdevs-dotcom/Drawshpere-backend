import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# ✅ Load environment variables from .env file
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")  # default name

def test_connection():
    print("🔌 Connecting to Neo4j AuraDB...")

    try:
        # Initialize driver
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        # Open a session and run a test query
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("RETURN '✅ Connected successfully!' AS message")
            print(result.single()["message"])

        print("🎉 Connection test completed successfully.")
    except Exception as e:
        print("❌ Connection failed:")
        print(e)
    finally:
        try:
            driver.close()
        except:
            pass

if __name__ == "__main__":
    test_connection()
