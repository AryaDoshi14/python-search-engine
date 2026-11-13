"""
tests/test_engine.py
Pytest suite covering core DSA components:
  1. Tokenizer (extraction, stop words, Porter stemming)
  2. Inverted Index (postings lists, document frequencies, lengths)
  3. TF-IDF Ranker (TF, IDF, snippet extraction, search scoring, title boost)
  4. Trie (insertion, prefix matching, ranking by frequency)
"""

import os
import sys
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.tokenizer import tokenize, extract_words, stem_word
from engine.indexer import InvertedIndex
from engine.ranker import compute_tf, compute_idf, compute_bm25_idf, generate_snippet, search
from engine.trie import Trie


# Takes in: None
# Returns: None - asserts tokenizer operations
def test_tokenizer_clean_words():
    """
    Tests extract_words splits text into unstemmed lowercase words without punctuation.
    """
    text = "Hello, World! Python's lists & dictionaries."
    words = extract_words(text)
    assert "hello" in words
    assert "world" in words
    assert "python" in words
    assert "lists" in words
    assert "dictionaries" in words


# Takes in: None
# Returns: None - asserts stop word removal and stemming
def test_tokenizer_stop_words_and_stemming():
    """
    Tests that tokenize removes English stop words and stems words correctly.
    """
    text = "Sorting a dictionary with Python"
    tokens = tokenize(text)
    # 'a' and 'with' are stop words and should be removed
    assert "a" not in tokens
    assert "with" not in tokens
    # 'sorting' stems to 'sort', 'dictionary' stems to 'dictionari'
    assert "sort" in tokens
    assert "dictionari" in tokens
    assert "python" in tokens


# Takes in: None
# Returns: None - asserts single word stemming
def test_stem_word():
    """
    Tests stem_word helper function.
    """
    assert stem_word("running") == "run"
    assert stem_word("dictionaries") == "dictionari"
    assert stem_word("sorted") == "sort"


# Takes in: None
# Returns: InvertedIndex - fixture with 2 sample documents indexed
@pytest.fixture
def sample_index():
    """
    Creates and populates a small in-memory InvertedIndex for testing.
    """
    idx = InvertedIndex()
    # Doc 0: about lists and sorting
    idx.add_document(
        doc_id=0,
        title="Python Lists Tutorial",
        filename="lists.html",
        raw_text="Lists are mutable sequences in Python. You can sort lists easily.",
        tokens=["list", "mutabl", "sequenc", "python", "sort", "list", "easili"],
        title_tokens=["python", "list", "tutori"]
    )
    # Doc 1: about dictionaries and sorting
    idx.add_document(
        doc_id=1,
        title="Sorting Python Dictionaries",
        filename="dictionaries.html",
        raw_text="Dictionaries store key value pairs. How to sort a dictionary by keys.",
        tokens=["dictionari", "store", "key", "valu", "pair", "sort", "dictionari", "key"],
        title_tokens=["sort", "python", "dictionari"]
    )
    return idx


# Takes in: sample_index (InvertedIndex fixture)
# Returns: None - asserts postings and term frequencies
def test_inverted_index_postings(sample_index):
    """
    Tests that terms correctly map to document IDs and counts.
    """
    # 'list' appears twice in doc 0, zero times in doc 1
    postings_list = sample_index.get_postings("list")
    assert postings_list == {0: 2}

    # 'sort' appears in both doc 0 and doc 1
    postings_sort = sample_index.get_postings("sort")
    assert 0 in postings_sort
    assert 1 in postings_sort
    assert postings_sort[0] == 1
    assert postings_sort[1] == 1

    # Document frequency
    assert sample_index.get_doc_freq("sort") == 2
    assert sample_index.get_doc_freq("dictionari") == 1


# Takes in: sample_index (InvertedIndex fixture)
# Returns: None - asserts document lengths and metadata
def test_inverted_index_metadata(sample_index):
    """
    Tests document token length and metadata storage.
    """
    assert sample_index.total_docs == 2
    assert sample_index.get_doc_length(0) == 7
    assert sample_index.get_doc_length(1) == 8

    meta_0 = sample_index.get_metadata(0)
    assert meta_0["title"] == "Python Lists Tutorial"
    assert meta_0["filename"] == "lists.html"
    assert "tutori" in meta_0["title_tokens"]


# Takes in: None
# Returns: None - asserts TF and IDF math
def test_tf_idf_math():
    """
    Tests hand-crafted TF and IDF formula outputs.
    """
    # TF: count / length
    assert compute_tf(2, 10) == 0.2
    assert compute_tf(0, 5) == 0.0

    # IDF: smooth formula
    idf_single = compute_idf(total_docs=10, doc_freq=1)
    idf_many = compute_idf(total_docs=10, doc_freq=8)
    # Rare words should have higher IDF than common words
    assert idf_single > idf_many


# Takes in: None
# Returns: None - asserts BM25 IDF math
def test_bm25_idf_math():
    """
    Tests hand-crafted BM25 IDF formula outputs.
    """
    # Rare words (low doc_freq) must have higher BM25 IDF than common words
    idf_rare = compute_bm25_idf(total_docs=100, doc_freq=2)
    idf_common = compute_bm25_idf(total_docs=100, doc_freq=50)
    assert idf_rare > idf_common
    assert idf_rare > 0.0


# Takes in: None
# Returns: None - asserts snippet generation
def test_snippet_generation():
    """
    Tests snippet generation centered around query keywords.
    """
    raw = "Introduction. Python dictionaries store mapping data. How to sort a dictionary by values."
    snippet = generate_snippet(raw, ["sort", "dictionary"], max_len=50)
    assert len(snippet) <= 70
    assert "sort" in snippet.lower() or "dictionar" in snippet.lower()


# Takes in: sample_index (InvertedIndex fixture)
# Returns: None - asserts search ranking and title boosting
def test_ranker_search(sample_index):
    """
    Tests search ranking and title boost for both BM25 and TF-IDF.
    For query 'sorting dictionaries', Doc 1 has both words and both in title,
    so it must rank #1 in both BM25 and legacy TF-IDF.
    """
    # Test default BM25
    bm25_results = search("sorting dictionaries", sample_index, top_k=2, algorithm="bm25")
    assert len(bm25_results) == 2
    assert bm25_results[0]["filename"] == "dictionaries.html"
    assert bm25_results[0]["score"] > bm25_results[1]["score"]

    # Test legacy TF-IDF
    tfidf_results = search("sorting dictionaries", sample_index, top_k=2, algorithm="tfidf")
    assert len(tfidf_results) == 2
    assert tfidf_results[0]["filename"] == "dictionaries.html"
    assert tfidf_results[0]["score"] > tfidf_results[1]["score"]


# Takes in: None
# Returns: None - asserts Trie insertion and prefix suggestions
def test_trie_insert_and_suggest():
    """
    Tests Trie prefix matching, limit cap, and frequency ordering.
    """
    trie = Trie()
    trie.insert("sort")
    trie.insert("sorted")
    trie.insert("sorting")
    trie.insert("sort")  # Insert 'sort' twice so its frequency is 2
    trie.insert("software")
    trie.insert("solitary")
    trie.insert("different")

    # Prefix 'so' should match words starting with 'so'
    suggestions = trie.suggest("so", limit=3)
    assert len(suggestions) == 3
    # 'sort' had frequency 2, so it should appear first
    assert suggestions[0] == "sort"
    assert all(w.startswith("so") for w in suggestions)

    # Prefix with no matches
    empty_suggestions = trie.suggest("xyz")
    assert empty_suggestions == []


# Takes in: None
# Returns: None - asserts case insensitivity in Trie
def test_trie_case_insensitivity():
    """
    Tests that the Trie handles uppercase and lowercase uniformly.
    """
    trie = Trie()
    trie.insert("Python")
    trie.insert("Pyramid")

    results = trie.suggest("py")
    assert "python" in results
    assert "pyramid" in results
