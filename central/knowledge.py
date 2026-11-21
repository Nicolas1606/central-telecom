"""Índice imutável de políticas. LSA é ajustada apenas ao corpus, nunca aos casos de avaliação."""
from pathlib import Path
import hashlib
import re
import unicodedata
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[1]

def norm(text):
    simple = unicodedata.normalize("NFKD", text.casefold())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in simple if not unicodedata.combining(c))))

class Index:
    def __init__(self):
        self.docs = {}
        for file in sorted((ROOT / "knowledge").glob("*.md")):
            for section in file.read_text(encoding="utf-8").split("## ")[1:]:
                heading, body = section.strip().split("\n", 1)
                key, title = heading.split(" | ")
                text, aliases = body.split("\nTermos: ")
                if key in self.docs or not text.strip():
                    raise ValueError(f"Seção inválida: {key}")
                self.docs[key] = dict(id=key, domain=file.stem, title=title, text=text, aliases=aliases,
                                      source=f"knowledge/{file.name}", sha256=hashlib.sha256(text.encode()).hexdigest())
        self.ids = list(self.docs)
        texts = [norm(" ".join(d[k] for k in ("title","text","aliases"))) for d in self.docs.values()]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self.sparse = self.vectorizer.fit_transform(texts)
        self.encoder = TruncatedSVD(n_components=min(4, len(texts)-1), random_state=42)
        self.dense = normalize(self.encoder.fit_transform(self.sparse))

    def search(self, query, domain=None, mode="hybrid", limit=3):
        q = self.vectorizer.transform([norm(query)])
        lexical = (self.sparse @ q.T).toarray().ravel()
        semantic = (self.dense @ normalize(self.encoder.transform(q)).T).ravel()
        scores = {"lexical": lexical, "semantic": semantic, "hybrid": 0.7*lexical + 0.3*semantic}[mode]
        return [dict(self.docs[self.ids[i]], score=round(float(scores[i]), 5))
                for i in np.argsort(-scores, kind="stable") if scores[i] > 1e-8 and
                (domain is None or self.docs[self.ids[i]]["domain"] == domain)][:limit]
