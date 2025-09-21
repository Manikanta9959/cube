# app/search_utils.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict
import numpy as np

class TfidfIndex:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.docs = []
        self.ids = []
        self.tfidf_matrix = None

    def build(self, docs: List[str], ids: List[int]):
        self.docs = docs
        self.ids = ids
        if docs:
            self.tfidf_matrix = self.vectorizer.fit_transform(docs)
        else:
            self.tfidf_matrix = None

    def add(self, doc: str, id_: int):
        self.docs.append(doc)
        self.ids.append(id_)
        self.build(self.docs, self.ids)

    def query(self, q: str, k: int = 5) -> List[Dict]:
        if not self.tfidf_matrix:
            return []
        qv = self.vectorizer.transform([q])
        sims = cosine_similarity(qv, self.tfidf_matrix)[0]
        topk_idx = np.argsort(-sims)[:k]
        results = []
        for idx in topk_idx:
            if sims[idx] <= 0:
                continue
            results.append({"id": int(self.ids[idx]), "score": float(sims[idx]), "text": self.docs[idx]})
        return results
