"""
Vulnerable FastAPI application for SQL injection testing.

WARNING: This app is intentionally vulnerable. Use only for testing!

Usage:
    python vulnerable_app.py
    # App runs on http://localhost:8666

Test endpoints:
    GET /users?id=1           - Vulnerable to SQL injection
    GET /search?name=admin    - Vulnerable to SQL injection
    GET /health               - Health check
"""

import sqlite3
import os
import uvicorn
from contextlib import contextmanager
from fastapi import FastAPI, Query
from typing import Optional

app = FastAPI(title="Vulnerable Test App", description="FOR TESTING ONLY")

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), "test_vulnerable.db")


def init_database():
    """Initialize SQLite database with test data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user'
        )
    """)

    # Create secrets table (for demonstrating data extraction)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY,
            secret_key TEXT NOT NULL,
            secret_value TEXT NOT NULL
        )
    """)

    # Insert test data
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM secrets")

    users = [
        (1, "admin", "admin123", "admin@test.com", "admin"),
        (2, "user1", "password1", "user1@test.com", "user"),
        (3, "user2", "password2", "user2@test.com", "user"),
        (4, "guest", "guest", "guest@test.com", "guest"),
    ]
    cursor.executemany(
        "INSERT INTO users (id, username, password, email, role) VALUES (?, ?, ?, ?, ?)",
        users
    )

    secrets = [
        (1, "API_KEY", "sk-secret-api-key-12345"),
        (2, "DB_PASSWORD", "super_secret_db_pass"),
        (3, "JWT_SECRET", "jwt-signing-secret-key"),
    ]
    cursor.executemany(
        "INSERT INTO secrets (id, secret_key, secret_value) VALUES (?, ?, ?)",
        secrets
    )

    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_database()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Vulnerable app is running"}


@app.get("/users")
async def get_user(id: str = Query(..., description="User ID")):
    """
    VULNERABLE ENDPOINT - SQL Injection via id parameter.

    Examples:
        /users?id=1                     - Normal query
        /users?id=1 OR 1=1              - Boolean injection
        /users?id=1 UNION SELECT 1,2,3,4,5  - Union injection
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # VULNERABLE: Direct string concatenation
        query = f"SELECT id, username, email, role FROM users WHERE id = {id}"
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            return {
                "query": query,  # Exposing query for debugging
                "results": [dict(row) for row in results]
            }
        except Exception as e:
            return {"error": str(e), "query": query}


@app.get("/search")
async def search_users(name: str = Query(..., description="Username to search")):
    """
    VULNERABLE ENDPOINT - SQL Injection via name parameter.

    Examples:
        /search?name=admin              - Normal query
        /search?name=admin' OR '1'='1   - String injection
        /search?name=' UNION SELECT * FROM secrets--  - Union injection
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # VULNERABLE: Direct string concatenation with quotes
        query = f"SELECT id, username, email, role FROM users WHERE username LIKE '%{name}%'"
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            return {
                "query": query,
                "results": [dict(row) for row in results]
            }
        except Exception as e:
            return {"error": str(e), "query": query}


@app.get("/login")
async def login(
    username: str = Query(..., description="Username"),
    password: str = Query(..., description="Password")
):
    """
    VULNERABLE ENDPOINT - SQL Injection in login.

    Examples:
        /login?username=admin&password=admin123           - Normal login
        /login?username=admin'--&password=anything        - Bypass auth
        /login?username=' OR '1'='1'--&password=anything  - Login as first user
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # VULNERABLE: Classic SQL injection in login
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        try:
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                return {
                    "success": True,
                    "message": f"Welcome {result['username']}!",
                    "role": result["role"]
                }
            return {"success": False, "message": "Invalid credentials"}
        except Exception as e:
            return {"error": str(e), "query": query}


def run_server(host: str = "127.0.0.1", port: int = 8666):
    """Run the vulnerable server."""
    print(f"Starting vulnerable test server on http://{host}:{port}")
    print("WARNING: This server is intentionally vulnerable!")
    print("\nVulnerable endpoints:")
    print(f"  - http://{host}:{port}/users?id=1")
    print(f"  - http://{host}:{port}/search?name=admin")
    print(f"  - http://{host}:{port}/login?username=admin&password=admin123")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_server()
