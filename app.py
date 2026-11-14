"""
app.py
FastAPI Web Application for the Python Documentation Search Engine.
Provides routes:
  - GET /        : Serves the search homepage
  - GET /suggest : Returns autocomplete word suggestions from the Trie
  - GET /search  : Returns the top 10 ranked document results using TF-IDF
"""

import os
import pickle
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from engine.ranker import search

# Global storage for index and trie loaded at startup
app_state = {
    "index": None,
    "trie": None,
    "texts": None
}


# Takes in: None
# Returns: tuple of (InvertedIndex, Trie) loaded from data/index.pkl
def load_index_data():
    """
    Loads the inverted index and trie from data/index.pkl once at startup.
    """
    index_path = os.path.join(os.path.dirname(__file__), "data", "index.pkl")
    if not os.path.exists(index_path):
        print(f"Warning: Index file not found at '{index_path}'. Run scripts/build_index.py first.")
        return None, None

    with open(index_path, "rb") as f:
        data = pickle.load(f)
        print("Search index and Trie successfully loaded into memory.")
        return data.get("inverted_index"), data.get("trie")


# Takes in: None
# Returns: dict of { doc_id: clean_text } loaded from data/texts.pkl
def load_texts_data():
    """
    Loads the full clean text dictionary from data/texts.pkl for context window extraction.
    """
    texts_path = os.path.join(os.path.dirname(__file__), "data", "texts.pkl")
    if not os.path.exists(texts_path):
        return {}

    with open(texts_path, "rb") as f:
        print("Full page texts successfully loaded into memory.")
        return pickle.load(f)


def get_index():
    """Returns the inverted index, loading it if not already loaded."""
    if app_state["index"] is None:
        app_state["index"], app_state["trie"] = load_index_data()
    return app_state["index"]


def get_trie():
    """Returns the trie, loading it if not already loaded."""
    if app_state["trie"] is None:
        app_state["index"], app_state["trie"] = load_index_data()
    return app_state["trie"]


def get_texts():
    """Returns the full texts dictionary, loading it if not already loaded."""
    if app_state["texts"] is None:
        app_state["texts"] = load_texts_data()
    return app_state["texts"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager:
    Loads index, trie, and page texts once when the server starts up.
    """
    app_state["index"], app_state["trie"] = load_index_data()
    app_state["texts"] = load_texts_data()
    yield


# Initialize FastAPI app
app = FastAPI(
    title="Python Documentation Search Engine",
    description="A simple, educational search engine using Inverted Index, TF-IDF, and Trie.",
    lifespan=lifespan
)

# Mount static directory for CSS and JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount docs directory so users can open and read original HTML documentation files
docs_dir = os.path.join(os.path.dirname(__file__), "data", "docs")
if os.path.exists(docs_dir):
    app.mount("/docs", StaticFiles(directory=docs_dir), name="docs")

# Configure Jinja2 templates directory
templates = Jinja2Templates(directory="templates")


# Takes in: request (Request) - the incoming HTTP request
# Returns: HTMLResponse - renders index.html
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """
    Serves the main search engine homepage.
    """
    return templates.TemplateResponse(request, "index.html")


# Takes in: q (string) - user's current prefix in the search box
# Returns: JSONResponse - list of up to 5 matching words from the Trie
@app.get("/suggest")
def suggest(q: str = Query("", description="Prefix to autocomplete")):
    """
    Autocomplete endpoint: queries the Trie for words matching the prefix 'q'.
    """
    trie = get_trie()
    if not trie or not q.strip():
        return JSONResponse([])

    suggestions = trie.suggest(q.strip(), limit=5)
    return JSONResponse(suggestions)


# Takes in: q (string) - search query entered by the user
# Returns: JSONResponse - dict with query and top-10 ranked search results
@app.get("/search")
def search_endpoint(q: str = Query("", description="Search query string")):
    """
    Search endpoint: scores documents using BM25 and returns top 10 results with context windows.
    """
    index = get_index()
    if not index or not q.strip():
        return JSONResponse({"query": q, "total_results": 0, "results": []})

    results = search(q.strip(), index, top_k=10, full_texts=get_texts())
    return JSONResponse({
        "query": q,
        "total_results": len(results),
        "results": results
    })
