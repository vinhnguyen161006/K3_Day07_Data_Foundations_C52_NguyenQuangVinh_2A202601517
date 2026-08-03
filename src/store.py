from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot, compute_similarity
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import chromadb  # noqa: F401
            self._use_chroma = True
            self._client = chromadb.Client()
            self._collection = self._client.create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        embedding = self._embedding_fn(doc.content)
        return {
            'id': doc.id,
            'content': doc.content,
            'embedding': embedding,
            'metadata': doc.metadata
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not records:
            return []

        query_embedding = self._embedding_fn(query)
        scored = []

        for record in records:
            score = compute_similarity(query_embedding, record['embedding'])
            scored.append({
                'id': record['id'],
                'content': record['content'],
                'metadata': record['metadata'],
                'score': score
            })

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if self._use_chroma:
            ids = []
            documents = []
            embeddings = []
            metadatas = []

            for doc in docs:
                embedding = self._embedding_fn(doc.content)
                ids.append(doc.id)
                documents.append(doc.content)
                embeddings.append(embedding)
                metadatas.append(doc.metadata)

            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
        else:
            for doc in docs:
                record = self._make_record(doc)
                self._store.append(record)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        if self._use_chroma:
            query_embedding = self._embedding_fn(query)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            output = []
            if results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i] if results['distances'] else 0
                    score = 1 - distance
                    output.append({
                        'content': doc,
                        'score': score,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    })
            return output
        else:
            return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        if self._use_chroma:
            return self._collection.count()
        else:
            return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if metadata_filter is None:
            return self.search(query, top_k)

        if self._use_chroma:
            query_embedding = self._embedding_fn(query)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=metadata_filter
            )

            output = []
            if results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i] if results['distances'] else 0
                    score = 1 - distance
                    output.append({
                        'content': doc,
                        'score': score,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    })
            return output
        else:
            filtered = []
            for record in self._store:
                match = True
                for key, value in metadata_filter.items():
                    if record['metadata'].get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(record)

            return self._search_records(query, filtered, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        if self._use_chroma:
            try:
                self._collection.delete(ids=[doc_id])
                return True
            except Exception:
                return False
        else:
            initial_size = len(self._store)
            self._store = [r for r in self._store if r['id'] != doc_id]
            return len(self._store) < initial_size
