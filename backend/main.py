# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import review
from db_module.session import SessionLocal, init_db
from LLM.search import TfidfIndex
from api_v1.api import api_v1_router

API_KEY = os.getenv("API_KEY", "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")  # use env in prod

app = FastAPI(title="Reviews Copilot")

# CORS for frontend dev:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory tf-idf index
tfidf_index = TfidfIndex()

@app.on_event("startup")
def on_startup():
    init_db()
    # build TF-IDF index from DB if any
    db = SessionLocal()
    try:
        rows = db.query(review.ReviewORM).all()
        docs = [r.text for r in rows]
        ids = [r.id for r in rows]
        tfidf_index.build(docs, ids)
    finally:
        db.close()


@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(prefix="/api/v1", router= api_v1_router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


