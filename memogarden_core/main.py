"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="MemoGarden Core",
    description="Personal expenditure tracking API",
    version="0.1.0"
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
