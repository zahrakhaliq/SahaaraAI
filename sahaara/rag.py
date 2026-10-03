"""Knowledge base + retrieval.

Semantic scenario matching uses FAISS + multilingual sentence-transformers when available
(set SAHAARA_EMBEDDINGS=off for a keyword fallback). Guidance chunks are retrieved per scenario
with source / version metadata so every answer can be attributed.
"""
import json
import re
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import config

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "scenarios.json"
GUIDANCE_SECTIONS = ["red_flags", "early_support", "escalation", "avoid", "referral_note"]
_TOKEN = re.compile(r"\w+", re.U)


class KnowledgeBase:
    def __init__(self):
        data = json.loads(KB_PATH.read_text(encoding="utf-8"))
        self.scenarios: Dict[str, dict] = {s["id"]: s for s in data["scenarios"]}
        # lines used to match a user's words to a scenario
        self.match_docs = []  # (scenario_id, text)
        for sid, s in self.scenarios.items():
            for line in s["plain_descriptions"] + s["symptom_patterns"]:
                self.match_docs.append((sid, line))
        self.index = None
        self.model = None
        if config.USE_EMBEDDINGS:
            try:
                import faiss
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(config.EMBED_MODEL)
                emb = self.model.encode([t for _, t in self.match_docs], normalize_embeddings=True)
                self.index = faiss.IndexFlatIP(emb.shape[1])
                self.index.add(np.asarray(emb, dtype="float32"))
            except Exception as e:  # missing deps / offline
                print(f"[rag] embeddings unavailable, using keyword fallback: {e}")
                self.index = None

    # ---------------------------------------------------------- scenario discovery
    def search_scenarios(self, query: str, k: int = 2) -> List[str]:
        if not query.strip():
            return []
        scores: Dict[str, float] = {}
        if self.index is not None:
            q = self.model.encode([query], normalize_embeddings=True)
            sims, idx = self.index.search(np.asarray(q, dtype="float32"), min(12, len(self.match_docs)))
            for sim, i in zip(sims[0], idx[0]):
                sid = self.match_docs[i][0]
                scores[sid] = max(scores.get(sid, 0.0), float(sim))
            ranked = [s for s, v in sorted(scores.items(), key=lambda x: -x[1]) if v >= 0.35]
        else:
            qt = set(_TOKEN.findall(query.lower()))
            for sid, text in self.match_docs:
                overlap = len(qt & set(_TOKEN.findall(text.lower())))
                if overlap:
                    scores[sid] = max(scores.get(sid, 0), overlap)
            ranked = [s for s, _ in sorted(scores.items(), key=lambda x: -x[1])]
        return ranked[:k]

    # ---------------------------------------------------------- evidence retrieval
    def evidence(self, scenario_ids: List[str]) -> List[Dict[str, str]]:
        chunks = []
        for sid in scenario_ids:
            s = self.scenarios.get(sid)
            if not s:
                continue
            for sec in GUIDANCE_SECTIONS:
                val = s.get(sec)
                text = " | ".join(val) if isinstance(val, list) else (val or "")
                if text:
                    chunks.append({
                        "scenario": s["title"], "section": sec, "text": text,
                        "source": s["source"], "source_date": s["source_date"],
                    })
        return chunks


_kb = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def scenario_ids() -> List[str]:
    return list(get_kb().scenarios.keys())
