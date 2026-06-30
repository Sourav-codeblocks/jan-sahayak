"""
core/retrieval.py — RAG Layer 1 (Static Knowledge Base)

Loads the farmer schemes CSV and exposes a single retrieve() function.
This is "Layer 1" of the fallback chain: fastest, free, always
available, zero hallucination risk because it returns exact source
documents, not generated text.

EMBEDDING STRATEGY:
Uses scikit-learn's TF-IDF vectorizer — deterministic, instant,
100% offline, no external model downloads required. This matters
for reliability on restricted networks and air-gapped lab machines.

To help TF-IDF match Hindi/Hinglish colloquial farmer queries against
English-language scheme documents, each document also includes a
"hindi_keywords" field from the CSV with common Hindi/Hinglish phrasings
a farmer might actually type or speak.
"""

import os
import pandas as pd
import config

USE_TFIDF = True


def _build_tfidf_embedder(corpus: list):
    """Fits a TF-IDF vectorizer on the knowledge base corpus."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    vectorizer = TfidfVectorizer(stop_words="english", max_features=2048)
    vectorizer.fit(corpus)
    return vectorizer


class SchemeRetriever:
    def __init__(self):
        os.makedirs(config.CHROMA_PERSIST_DIR, exist_ok=True)

        self.df = pd.read_csv(config.SCHEME_KB_CSV)
        self.documents, self.metadatas, self.ids = self._prepare_documents()

        self.vectorizer = _build_tfidf_embedder(self.documents)
        self.doc_vectors = self.vectorizer.transform(self.documents)

    def _prepare_documents(self):
        documents, metadatas, ids = [], [], []
        for _, row in self.df.iterrows():
            # Any field that's empty/NaN in the CSV becomes an explicit
            # withholding marker, never silently blank. This is a tripwire
            # the LLM prompt instructs it to respect: if it sees this marker
            # it must NOT guess or invent a value for that field.
            def safe(field_name):
                val = row.get(field_name, "")
                if pd.isna(val) or str(val).strip() == "":
                    return "INFORMATION_WITHHELD"
                return val

            doc_text = (
                f"Scheme: {safe('scheme_name')}. "
                f"Department: {safe('department')}. "
                f"Eligibility: {safe('eligibility_criteria')}. "
                f"Land holding limit: {safe('land_holding_limit')}. "
                f"Income limit: {safe('income_limit')}. "
                f"Benefit: {safe('benefit_description')}. "
                f"Required documents: {safe('required_documents')}. "
                f"How to apply: {safe('application_process')}. "
                f"Related terms: {row.get('hindi_keywords', '')} "
                f"{row.get('tamil_keywords', '')} "
                f"{row.get('telugu_keywords', '')}."
            )
            documents.append(doc_text)
            metadatas.append({
                "scheme_id": row["scheme_id"],
                "scheme_name": row["scheme_name"],
                "department": row["department"],
                "official_link": row["official_link"],
                "required_documents": row["required_documents"],
                "application_process": row["application_process"],
            })
            ids.append(row["scheme_id"])
        return documents, metadatas, ids

    def retrieve(self, query: str, top_k: int = None) -> list:
        """
        Returns top_k most relevant scheme documents for a query.
        Each result includes text, metadata, and a relevance score
        (0 to 1, higher = more relevant, TF-IDF cosine similarity).
        """
        top_k = top_k or config.RAG_TOP_K

        from sklearn.metrics.pairwise import cosine_similarity
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.doc_vectors)[0]
        ranked_idx = scores.argsort()[::-1][:top_k]

        retrieved = []
        for idx in ranked_idx:
            retrieved.append({
                "text": self.documents[idx],
                "metadata": self.metadatas[idx],
                "score": float(scores[idx]),
            })
        return retrieved


# Singleton instance — loaded once, reused across requests
_retriever_instance = None

def get_retriever() -> SchemeRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = SchemeRetriever()
    return _retriever_instance
