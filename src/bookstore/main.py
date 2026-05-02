"""
BookStore API — the system under test.

Intentionally has interesting performance characteristics:
- /search uses linear scan over an in-memory list (slows with more books)
- /book/{id} is O(1) lookup (stable)
- A SLOW_MODE env flag toggles an artificial slowdown so we can demo
  performance regressions without changing code.
"""
import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="BookStore API")

SLOW_MODE = os.getenv("SLOW_MODE", "0") == "1"


class Book(BaseModel):
    id: int
    title: str
    author: str
    year: int


_books: list[Book] = [
    Book(id=i,
         title=f"Book Title {i}",
         author=f"Author {i % 50}",
         year=1900 + (i % 125))
    for i in range(1, 5001)
]
_by_id: dict[int, Book] = {b.id: b for b in _books}


@app.get("/health")
def health():
    return {"status": "ok", "slow_mode": SLOW_MODE, "book_count": len(_books)}


@app.get("/book/{book_id}", response_model=Book)
def get_book(book_id: int):
    """O(1) hash lookup. Stable performance."""
    if SLOW_MODE:
        time.sleep(0.005)
    if book_id not in _by_id:
        raise HTTPException(status_code=404, detail="not found")
    return _by_id[book_id]


@app.get("/search", response_model=list[Book])
def search(q: str, limit: int = 10):
    """Linear scan. Slows as dataset grows or query is broad."""
    q_lower = q.lower()
    results: list[Book] = []
    for b in _books:
        if q_lower in b.title.lower() or q_lower in b.author.lower():
            results.append(b)
            if len(results) >= limit:
                break
    if SLOW_MODE:
        time.sleep(0.02)
    return results
