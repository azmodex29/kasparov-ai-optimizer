from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.store import router as store_router
from routes.analyze import router as analyze_router
from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI(title="KASPAROV API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dev/test routes
app.include_router(store_router)

# Main pipeline routes
app.include_router(analyze_router)


@app.get("/")
def root():
    return {"status": "ok", "message": "KASPAROV API running"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc)
        }
    )