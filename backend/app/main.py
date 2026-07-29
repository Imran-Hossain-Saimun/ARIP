import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.admin.router import router as admin_router
from app.ai.router import router as ai_router
from app.analytics.router import router as analytics_router
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.automation.router import router as automation_router
from app.dashboard.router import router as dashboard_router
from app.decisions.router import router as decisions_router
from app.email.router import router as email_router
from app.knowledge.router import gaps_router, router as knowledge_router
from app.portal.router import router as portal_router
from app.realtime.router import router as realtime_router
from app.reference.router import router as reference_router
from app.requests.router import router as requests_router
from app.settings.router import router as settings_router

app = FastAPI(title="ARIP API", version="0.1.0", openapi_url="/v1/openapi.json", docs_url="/v1/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """§09 API convention: every error is `{code, message, field_errors, trace_id}`."""
    trace_id = f"trc_{uuid.uuid4().hex[:12]}"
    detail = exc.detail
    if isinstance(detail, dict):
        body = {"code": detail.get("code", "error"), "message": detail.get("message", "Request failed."), "field_errors": detail.get("field_errors", []), "trace_id": trace_id}
    else:
        body = {"code": "error", "message": str(detail), "field_errors": [], "trace_id": trace_id}
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """§09: 400 validation_failed -> inline field errors (FastAPI's own default is a
    bare 422 with a different shape; reshape it to match every other error path)."""
    trace_id = f"trc_{uuid.uuid4().hex[:12]}"
    field_errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(
        status_code=400,
        content={"code": "validation_failed", "message": "Request validation failed.", "field_errors": field_errors, "trace_id": trace_id},
    )


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(dashboard_router)
app.include_router(requests_router)
app.include_router(decisions_router)
app.include_router(knowledge_router)
app.include_router(gaps_router)
app.include_router(reference_router)
app.include_router(email_router)
app.include_router(automation_router)
app.include_router(analytics_router)
app.include_router(audit_router)
app.include_router(settings_router)
app.include_router(ai_router)
app.include_router(portal_router)
app.include_router(realtime_router)
