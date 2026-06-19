import warnings
warnings.filterwarnings('ignore')

from langchain.embeddings.base import Embeddings
from typing import Any, List, Optional


class LocalEmbeddings(Embeddings):
    """
    文本向量化：
    - 优先使用 sentence-transformers（需要 torch，约400MB）
    - 降级使用 sklearn TfidfVectorizer（轻量，无需GPU）
    """

    def __init__(self, model_name: str = "shibing624/text2vec-base-chinese",
                 device: str = "cpu", **kwargs: Any):
        self._model: Optional[object] = None
        self._tfidf: Optional[object] = None
        self._tfidf_fitted = False
        self._docs_for_fit: List[str] = []

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name, device=device)
            return
        except (ImportError, Exception):
            pass

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._tfidf = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(2, 4), max_features=512
            )
        except ImportError:
            raise ImportError(
                "请安装 embedding 依赖:\n"
                "  pip install sentence-transformers\n"
                "  或\n"
                "  pip install scikit-learn"
            )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self._model:
            embeddings = self._model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()

        if self._tfidf:
            if not self._tfidf_fitted:
                self._tfidf.fit(texts)
                self._tfidf_fitted = True
            sparse = self._tfidf.transform(texts)
            return [vec.toarray().flatten().tolist() for vec in sparse]

        return [[0.0] * 512] * len(texts)

    def embed_query(self, text: str) -> List[float]:
        if self._model:
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding.tolist()

        if self._tfidf:
            if not self._tfidf_fitted:
                self._tfidf.fit([text])
                self._tfidf_fitted = True
            sparse = self._tfidf.transform([text])
            return sparse.toarray().flatten().tolist()

        return [0.0] * 512