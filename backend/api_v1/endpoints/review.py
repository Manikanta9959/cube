# app/main.py
import os
from fastapi import  HTTPException, Header, Depends, Query, APIRouter
from typing import List, Optional
from sqlalchemy.orm import Session
from models import review
from db_module.session import get_db
from LLM.pipeline import analyze_text, suggest_reply
from LLM.search import TfidfIndex

API_KEY = os.getenv("API_KEY", "sk-proj-qcd4w71XoWKPoRmXJrOf71Czm7I9cG0")


router = APIRouter()

def require_api_key(x_api_key: Optional[str] = Header(None)):
    print(x_api_key)
    print(API_KEY)
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

# in-memory tf-idf index
tfidf_index = TfidfIndex()



@router.post("/ingest", dependencies=[Depends(require_api_key)])
def ingest(reviews: List[review.ReviewCreate], db: Session = Depends(get_db)):
    added = []
    for r in reviews:
        exists = db.query(review.ReviewORM).filter(review.ReviewORM.id == r.id).first()
        if exists:
            continue
        orm = review.ReviewORM(id=r.id, location=r.location, rating=r.rating, text=r.text, date=r.date)
        db.add(orm)
        added.append(r.id)
    db.commit()
    # rebuild tfidf
    rows = db.query(review.ReviewORM).all()
    tfidf_index.build([r.text for r in rows], [r.id for r in rows])
    return {"ingested": added}

@router.get("/reviews", dependencies=[Depends(require_api_key)])
def list_reviews(location: Optional[str] = None, sentiment: Optional[str] = None,
                 q: Optional[str] = None, page: int = 1, page_size: int = 20,
                 db: Session = Depends(get_db)):
    query = db.query(review.ReviewORM)
    if location:
        query = query.filter(review.ReviewORM.location == location)
    # naive sentiment filter: we analyze on the fly (could be cached)
    all_rows = query.order_by(review.ReviewORM.id).offset((page - 1) * page_size).limit(page_size).all()
    results = []
    for r in all_rows:
        s = analyze_text(r.text)["sentiment"]["label"]
        if sentiment and sentiment.lower() not in s.lower():
            continue
        if q and q.lower() not in r.text.lower():
            continue
        results.append({"id": r.id, "location": r.location, "rating": r.rating, "text": r.text, "date": r.date, "sentiment": s})
    return {"page": page, "page_size": page_size, "items": results}

@router.get("/reviews/{id}", dependencies=[Depends(require_api_key)])
def get_review(id: int, db: Session = Depends(get_db)):
    r = db.query(review.ReviewORM).filter(review.ReviewORM.id == id).first()
    if not r:
        raise HTTPException(404, "Review not found")
    analysis = analyze_text(r.text)
    return {"id": r.id, "location": r.location, "rating": r.rating, "text": r.text, "date": r.date,
            "analysis": analysis}

@router.post("/reviews/{id}/suggest-reply", dependencies=[Depends(require_api_key)])
def suggest_review_reply(id: int, db: Session = Depends(get_db)):
    r = db.query(review.ReviewORM).filter(review.ReviewORM.id == id).first()
    if not r:
        raise HTTPException(404, "Review not found")
    analysis = analyze_text(r.text)
    topic = analysis.get("topic", "general") 
    out = suggest_reply(r.text, analysis["sentiment"]["label"], topic=topic)
    # basic toxicity check - naive
    if "idiot" in r.text.lower() or "kill" in r.text.lower():
        out["reply"] = "[AUTO-REDACTED] Message contains unsafe words; escalate to human."
    return {"reply": out["reply"], "tags": {"sentiment": analysis["sentiment"]["label"]}, "reasoning_log": out["reasoning_log"]}

@router.get("/analytics", dependencies=[Depends(require_api_key)])
def analytics(db: Session = Depends(get_db)):
    rows = db.query(review.ReviewORM).all()
    counts = {"total": len(rows), "by_location": {}, "by_sentiment": {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}}
    for r in rows:
        counts["by_location"].setdefault(r.location, 0)
        counts["by_location"][r.location] += 1
        s = analyze_text(r.text)["sentiment"]["label"].upper()
        if "POS" in s:
            counts["by_sentiment"]["POSITIVE"] += 1
        elif "NEG" in s:
            counts["by_sentiment"]["NEGATIVE"] += 1
        else:
            counts["by_sentiment"]["NEUTRAL"] += 1
    return counts

@router.get("/search", dependencies=[Depends(require_api_key)])
def search(q: str = Query(...), k: int = 5):
    return {"results": tfidf_index.query(q, k)}
