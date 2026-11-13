"""
engine/ranker.py
Scores documents for search queries using hand-crafted Okapi BM25 and TF-IDF ranking.
BM25 prevents very short, irrelevant pages from dominating results by balancing term
frequency saturation and document length normalization against the collection average.
Uses heapq.nlargest to efficiently select the top-10 results.
"""

import re
import math
import heapq
import os
import sys
import pickle

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.tokenizer import tokenize, extract_words

# ==============================================================================
# BM25 & RANKING HYPERPARAMETERS
# ==============================================================================

# k1 controls term frequency saturation:
# It limits how much extra score a repeated keyword can add. Higher values give
# more weight to repeated words; lower values saturate faster. (Typical: 1.2 - 2.0)
K1 = 1.5

# b controls document length normalization:
# b = 1.0 penalizes long documents heavily; b = 0.0 applies no length penalty at all.
# b = 0.75 provides the standard balance, preventing tiny docs from unfairly dominating.
B = 0.75

# Extra weight (+30%) added to a word's score if it appears in the page's title
TITLE_BOOST = 0.30

# Default ranking algorithm: "bm25" (can be switched to "tfidf" for comparison)
DEFAULT_ALGORITHM = "bm25"


# ==============================================================================
# MATHEMATICAL SCORING FUNCTIONS
# ==============================================================================

# Takes in: total_docs (int) - N: total number of documents in the collection
#           doc_freq (int) - n: number of documents containing the term
# Returns: float - BM25 inverse document frequency
def compute_bm25_idf(total_docs: int, doc_freq: int) -> float:
    """
    Computes BM25 Inverse Document Frequency:
    idf = ln(1 + (N - n + 0.5) / (n + 0.5))
    """
    if total_docs == 0 or doc_freq == 0:
        return 0.0
    return math.log(1.0 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))


# Takes in: count (int) - raw number of occurrences of term in document
#           doc_length (int) - total number of tokens in the document
# Returns: float - normalized term frequency for TF-IDF
def compute_tf(count: int, doc_length: int) -> float:
    """
    Computes normalized Term Frequency (TF) for TF-IDF:
    tf = count / doc_length
    """
    if doc_length == 0:
        return 0.0
    return count / doc_length


# Takes in: total_docs (int) - total number of documents in collection (N)
#           doc_freq (int) - number of documents containing the term (DF)
# Returns: float - smooth inverse document frequency for TF-IDF
def compute_idf(total_docs: int, doc_freq: int) -> float:
    """
    Computes smooth Inverse Document Frequency (IDF) for TF-IDF:
    idf = ln((N + 1) / (DF + 1)) + 1.0
    """
    if doc_freq == 0:
        return 0.0
    return math.log((total_docs + 1) / (doc_freq + 1)) + 1.0


# Takes in: query_tokens (list of strings) - stemmed tokens from search query
#           index (InvertedIndex) - inverted index data structure
# Returns: dict of { doc_id: score } - BM25 scores per matching document
def bm25_score(query_tokens: list, index) -> dict:
    """
    Calculates document relevance scores using Okapi BM25:
    score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_length / avg_doc_length))
    Adds +30% boost if the query word appears in the page's title.
    """
    doc_scores = {}
    total_docs = index.total_docs
    avg_doc_length = index.get_avg_doc_length()

    if total_docs == 0 or avg_doc_length == 0:
        return {}

    for token in query_tokens:
        postings = index.get_postings(token)
        n = len(postings)

        if n == 0:
            continue

        idf = compute_bm25_idf(total_docs, n)

        for doc_id, tf in postings.items():
            doc_len = index.get_doc_length(doc_id)

            # BM25 term saturation & length normalization formula
            numerator = tf * (K1 + 1.0)
            denominator = tf + K1 * (1.0 - B + B * (doc_len / avg_doc_length))
            term_score = idf * (numerator / denominator)

            # Title boost: add +30% of that word's score if present in the document title
            metadata = index.get_metadata(doc_id)
            title_tokens = metadata.get("title_tokens", set())
            if token in title_tokens:
                term_score += term_score * TITLE_BOOST

            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + term_score

    return doc_scores


# Takes in: query_tokens (list of strings) - stemmed tokens from search query
#           index (InvertedIndex) - inverted index data structure
# Returns: dict of { doc_id: score } - TF-IDF scores per matching document
def tfidf_score(query_tokens: list, index) -> dict:
    """
    Legacy TF-IDF scoring function (retained for comparison):
    score += (count / doc_len) * idf
    Multiplies term score by 2x if the term appears in the page title.
    """
    doc_scores = {}
    total_docs = index.total_docs

    if total_docs == 0:
        return {}

    for token in query_tokens:
        postings = index.get_postings(token)
        df = len(postings)

        if df == 0:
            continue

        idf = compute_idf(total_docs, df)

        for doc_id, count in postings.items():
            doc_len = index.get_doc_length(doc_id)
            tf = compute_tf(count, doc_len)
            term_score = tf * idf

            metadata = index.get_metadata(doc_id)
            title_tokens = metadata.get("title_tokens", set())
            if token in title_tokens:
                term_score *= 2.0

            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + term_score

    return doc_scores


# ==============================================================================
# SNIPPET & SEARCH RETRIEVAL
# ==============================================================================

# ==============================================================================
# SNIPPET & CONTEXT WINDOW EXTRACTION
# ==============================================================================

# Takes in: text (string) - full page text
#           query_words (list of strings) - unstemmed query words
#           query_stems (list of strings) - stemmed query tokens
# Returns: int - character index of the earliest match, or -1 if no match found
def find_match_position(text: str, query_words: list, query_stems: list) -> int:
    """
    Finds the earliest character position in the document text where any query word appears.
    Checks:
      1. Exact case-insensitive word match
      2. Stem match: words starting with the same stem
    """
    if not text:
        return -1

    lower_words_set = {w.lower() for w in query_words if len(w) >= 2}
    stems_set = {s.lower() for s in query_stems if len(s) >= 2}

    earliest_pos = -1

    for match in re.finditer(r"\b[a-zA-Z0-9_]+\b", text):
        word = match.group().lower()
        pos = match.start()

        # 1. Direct word match
        if word in lower_words_set:
            return pos

        # 2. Stem-based match (word starts with stem, e.g. 'sorting' starts with 'sort')
        for s in stems_set:
            if word.startswith(s) or (len(s) >= 3 and s in word):
                if earliest_pos == -1 or pos < earliest_pos:
                    earliest_pos = pos
                    break

    return earliest_pos


# Takes in: text (string) - document text
#           match_pos (int) - character index where match was found (-1 if none)
#           window_len (int) - target length of the window in characters
#           offset_before (int) - characters before match_pos to start the window
# Returns: string - extracted window cut at word boundaries with '...' where truncated
def extract_context_window(text: str, match_pos: int, window_len: int, offset_before: int) -> str:
    """
    Extracts a window of text centered around match_pos, snapped to word boundaries,
    with '...' prepended or appended when text is removed.
    """
    if not text:
        return ""

    # If no match was found, fallback to beginning of text cut at a word boundary
    if match_pos == -1:
        if len(text) <= window_len:
            return text
        cut = text[:window_len]
        return cut.rsplit(" ", 1)[0] + "..."

    raw_start = max(0, match_pos - offset_before)
    raw_end = min(len(text), raw_start + window_len)

    # Snap raw_start forward to next space (word boundary), unless starting at index 0
    if raw_start > 0:
        next_space = text.find(" ", raw_start)
        if next_space != -1 and next_space < match_pos:
            start = next_space + 1
        else:
            start = raw_start
    else:
        start = 0

    # Snap raw_end backward to previous space (word boundary), unless reaching end of text
    if raw_end < len(text):
        prev_space = text.rfind(" ", start, raw_end)
        if prev_space > start:
            end = prev_space
        else:
            end = raw_end
    else:
        end = len(text)

    window = text[start:end].strip()

    if start > 0:
        window = "..." + window
    if end < len(text):
        window = window + "..."

    return window


# Takes in: raw_text (string) - full text of the document
#           query_words (list of strings) - list of unstemmed query words
#           max_len (int) - approximate length of snippet (default: 150)
# Returns: string - snippet around the first matched query word
def generate_snippet(raw_text: str, query_words: list, max_len: int = 150) -> str:
    """
    Legacy helper maintaining backwards-compatibility for existing tests.
    """
    query_stems = [tokenize(w)[0] for w in query_words if tokenize(w)]
    pos = find_match_position(raw_text, query_words, query_stems)
    return extract_context_window(raw_text, pos, window_len=max_len, offset_before=30)


# Takes in: query (string) - search query entered by the user
#           index (InvertedIndex) - inverted index containing terms and postings
#           top_k (int) - number of top results to return (default: 10)
#           algorithm (string) - ranking algorithm to use ("bm25" or "tfidf")
#           full_texts (dict, optional) - mapping of doc_id -> full clean text
# Returns: list of dicts - [{ "title": ..., "filename": ..., "snippet": ..., "preview": ..., "score": ... }]
def search(query: str, index, top_k: int = 10, algorithm: str = DEFAULT_ALGORITHM, full_texts: dict = None) -> list:
    """
    Executes a search query:
    1. Tokenizes the query into stemmed search tokens.
    2. Scores documents using the selected algorithm (BM25 or TF-IDF).
    3. Selects top_k highest scoring documents using heapq.nlargest.
    4. Finds first occurrence position of any query word/stem in the full text.
    5. Extracts both a ~150-char card snippet and a ~1500-char popup window cut at word boundaries.
    """
    query_tokens = tokenize(query)
    raw_query_words = extract_words(query)

    if not query_tokens or index.total_docs == 0:
        return []

    # Choose ranking algorithm
    if algorithm.lower() == "tfidf":
        doc_scores = tfidf_score(query_tokens, index)
    else:
        doc_scores = bm25_score(query_tokens, index)

    if not doc_scores:
        return []

    # Convert dictionary items into a list of tuples for heap ranking: (score, doc_id)
    candidate_list = [(score, doc_id) for doc_id, score in doc_scores.items()]

    # Use heapq.nlargest to find top_k highest scores
    top_candidates = heapq.nlargest(top_k, candidate_list, key=lambda item: item[0])

    # Format the results
    results = []
    for score, doc_id in top_candidates:
        metadata = index.get_metadata(doc_id)

        # Retrieve full clean text if available; fallback to metadata
        full_text = ""
        if full_texts and doc_id in full_texts:
            full_text = full_texts[doc_id]
        elif metadata.get("raw_text"):
            full_text = metadata.get("raw_text")
        elif metadata.get("preview"):
            full_text = metadata.get("preview")

        # Find first matching word or stem position in the document text
        match_pos = find_match_position(full_text, raw_query_words, query_tokens)

        # Build card snippet (~150 chars, offset ~30 chars before match)
        snippet = extract_context_window(full_text, match_pos, window_len=150, offset_before=30)

        # Build popup text (~1500 chars, offset ~200 chars before match)
        if match_pos != -1:
            popup_text = extract_context_window(full_text, match_pos, window_len=1500, offset_before=200)
        else:
            popup_text = metadata.get("preview") or extract_context_window(full_text, -1, window_len=1500, offset_before=0)

        results.append({
            "title": metadata.get("title", "Untitled Document"),
            "filename": metadata.get("filename", ""),
            "snippet": snippet,
            "preview": popup_text,
            "score": round(score, 4)
        })

    return results


# Terminal Test Runner
if __name__ == "__main__":
    index_path = "data/index.pkl"
    if not os.path.exists(index_path):
        print(f"Index file '{index_path}' not found. Please run scripts/build_index.py first.")
        sys.exit(1)

    with open(index_path, "rb") as f:
        data = pickle.load(f)
        index = data["inverted_index"]

    print("=" * 65)
    print("PYTHON DOCUMENTATION SEARCH ENGINE - BM25 vs TF-IDF COMPARISON")
    print("=" * 65)

    test_queries = [
        "lists",
        "sort a dictionary",
        "asyncio stream",
        "compound statements"
    ]

    for q in test_queries:
        print(f"\nQUERY: '{q}'")
        print("-" * 65)
        bm25_hits = search(q, index, top_k=3, algorithm="bm25")
        tfidf_hits = search(q, index, top_k=3, algorithm="tfidf")

        print("  [BM25 Ranking]:")
        for rank, hit in enumerate(bm25_hits, 1):
            print(f"    {rank}. [{hit['score']}] {hit['title']} ({hit['filename']})")

        print("  [TF-IDF Ranking]:")
        for rank, hit in enumerate(tfidf_hits, 1):
            print(f"    {rank}. [{hit['score']}] {hit['title']} ({hit['filename']})")
