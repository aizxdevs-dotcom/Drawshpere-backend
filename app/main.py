from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.routes import comment_routes, reaction_routes, notification_routes

from app.routes import user_routes, post_routes
from app.db import get_db
from app.auth import get_current_user

# =========================================================
# ✅ APP SETUP
# =========================================================
app = FastAPI(
    title="FastAPI + Neo4j AuraDB Example",
    version="1.0.0",
    description="Social media API powered by FastAPI and Neo4j AuraDB, using HTTP Bearer JWT authentication.",
    swagger_ui_parameters={"persistAuthorization": True},  # keep token after refresh
)

# =========================================================
# ✅ ENABLE CORS (optional but useful)
# =========================================================
app.add_middleware(
    CORSMiddleware,
    # change to your frontend URL(s) if needed
    allow_origins=[
        "https://drawsphere-lq96f4uit-aizxdevs-projects.vercel.app/",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# ✅ ROUTE REGISTRATION
# =========================================================
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(post_routes.router, prefix="/posts", tags=["Posts"])
app.include_router(comment_routes.router, prefix="/comments", tags=["Comments"])
app.include_router(reaction_routes.router, prefix="/reactions", tags=["Reactions"])
app.include_router(notification_routes.router, prefix="/notifications", tags=["Notifications"])

# =========================================================
# ✅ PROTECTED ROOT ENDPOINT
# =========================================================
@app.get("/")
def root(current_user: dict = Depends(get_current_user)):
    """
    Protected welcome route. Requires valid Bearer token.
    """
    return {
        "message": f"Welcome {current_user['username']} to FastAPI + Neo4j AuraDB API!",
        "user_id": current_user["user_id"],
    }


# =========================================================
# ✅ CUSTOM OPENAPI (for HTTP Bearer Auth)
# =========================================================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add Bearer auth scheme
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    # Apply Bearer auth to all endpoints by default
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"HTTPBearer": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Attach custom OpenAPI schema
app.openapi = custom_openapi
