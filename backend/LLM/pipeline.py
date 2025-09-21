# app/ai.py
from typing import Dict, Any
import re
import os

# Hugging Face pipelines
from transformers import pipeline

# OpenAI client (only if API key present)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ========== Setup ==========
_sentiment_pipeline = None
_summarizer = None
_openai_client = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", default="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")

if OPENAI_API_KEY and OpenAI:
    _openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ========== Utilities ==========

PHONE_RE = re.compile(r"(\+?\d[\d\-\s]{6,}\d)")
EMAIL_RE = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")

def redact(text: str) -> str:
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return text

# Lightweight topic classifier
TOPIC_KEYWORDS = {
    "service": ["service", "staff", "wait", "checkout", "friendly"],
    "cleanliness": ["clean", "dirty", "hygiene", "messy"],
    "price": ["price", "expensive", "cheap", "cost"],
    "delivery": ["delivery", "late", "fast", "missing", "order"],
    "app": ["app", "crash", "bug", "login"]
}

def detect_topic(text: str) -> str:
    text_lower = text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(word in text_lower for word in keywords):
            return topic
    return "general"

# Hugging Face pipelines
def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        _sentiment_pipeline = pipeline("sentiment-analysis", truncation=True)
    return _sentiment_pipeline

def get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = pipeline("summarization", truncation=True)
    return _summarizer

# ========== Analysis ==========

def analyze_text(text: str) -> Dict[str, Any]:
    safe_text = redact(text)

    try:
        print("openaiclienttttttttttttttttttttt")
        # Use OpenAI for sentiment + summary
        messages = [
            {"role": "system", "content": "You are a classifier for customer reviews."},
            {"role": "user", "content": f"Review: {safe_text}\n\n1. Sentiment (Positive/Negative/Neutral)\n2. Short summary (max 30 words)."}
        ]
        resp = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0
        )
        content = resp.choices[0].message.content
        # crude parse
        lines = content.splitlines()
        sentiment = {"label": "UNKNOWN", "score": 1.0}
        summary = ""
        for line in lines:
            if "positive" in line.lower():
                sentiment = {"label": "POSITIVE", "score": 1.0}
            elif "negative" in line.lower():
                sentiment = {"label": "NEGATIVE", "score": 1.0}
            elif "neutral" in line.lower():
                sentiment = {"label": "NEUTRAL", "score": 1.0}
            if "summary" in line.lower() or len(line.split()) > 3:
                summary = line.strip()
        topic = detect_topic(safe_text)
        return {"safe_text": safe_text, "sentiment": sentiment, "summary": summary, "topic": topic}

    except Exception as err:
        print(err)
        print("hugging faceeeeeeeee")
        # Hugging Face fallback
        sentiment = get_sentiment_pipeline()(safe_text[:1000])[0]
        summary = get_summarizer()(safe_text[:2000], max_length=40, min_length=10)
        topic = detect_topic(safe_text)
        return {
            "safe_text": safe_text,
            "sentiment": sentiment,
            "summary": summary[0]["summary_text"] if isinstance(summary, list) else str(summary),
            "topic": topic
        }

# ========== Suggest Reply ==========

def suggest_reply(review_text: str, sentiment_label: str, topic: str) -> Dict[str, Any]:
    safe_text = redact(review_text)

    try:
        messages = [
            {"role": "system", "content": "You are a helpful customer support assistant. Write concise, empathetic replies."},
            {"role": "user", "content": f"Review: {safe_text}\nSentiment: {sentiment_label}\nTopic: {topic}\nDraft a reply:"}
        ]
        resp = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        reply = resp.choices[0].message.content.strip()
        reasoning = {"redacted": safe_text, "sentiment": sentiment_label, "topic": topic, "model": "gpt-4o-mini"}
        return {"reply": reply, "reasoning_log": reasoning}
    except Exception as err:
        print(err)
        summary = analyze_text(review_text)["summary"]
        if "neg" in sentiment_label.lower():
            reply = f"Hi — we're sorry you had this experience. {summary} We value your feedback and would like to make it right."
        else:
            reply = f"Hi — thanks for the feedback! {summary} We're glad you had a good experience."
        reasoning = {"redacted": safe_text, "summary": summary, "sentiment": sentiment_label, "topic": topic, "model": "huggingface"}
        return {"reply": reply, "reasoning_log": reasoning}
