# Python Documentation Search Engine

A lightweight, educational search engine built in Python from scratch using fundamental **Data Structures and Algorithms (DSA)**.

This project indexes Python documentation HTML files, provides real-time autocomplete suggestions as you type, and retrieves the most relevant pages ranked by a custom **TF-IDF** scoring algorithm.

---

## 🎯 Project Overview

Many modern applications use heavyweight search libraries like Elasticsearch, Whoosh, or scikit-learn. This project intentionally avoids ready-made search libraries to demonstrate how full-text search works under the hood using foundational computer science concepts:

- **Inverted Index** for fast document lookup ($O(1)$ dictionary lookups instead of scanning every document).
- **TF-IDF (Term Frequency – Inverse Document Frequency)** for mathematical relevance ranking with title boosting.
- **Trie (Prefix Tree)** for sub-millisecond prefix-based autocomplete suggestions.
- **FastAPI & Vanilla Web Frontend** for a clean, responsive search user interface.

---

## 🧠 How It Works

### 1. Inverted Index (`engine/indexer.py`)
In a normal document store, documents map to words:
$$\text{Document } \rightarrow [\text{word}_1, \text{word}_2, \dots]$$

An **Inverted Index** reverses this relationship:
$$\text{Word} \rightarrow \{\text{Doc ID}: \text{Count}\}$$

When a user searches for `"sort"`, the search engine doesn't read every document on disk. Instead, it looks up `"sort"` in the inverted index in $O(1)$ time and immediately gets the list of documents where it appears.

### 2. TF-IDF Ranking (`engine/ranker.py`)
Not all matching words are equally important. TF-IDF scores document relevance using two metrics:

1. **Term Frequency (TF)**: How frequently a word appears in a document, normalized by document length:
   $$\text{TF}(t, d) = \frac{\text{count}(t, d)}{\text{total terms in } d}$$
   Normalizing by length prevents very long documents from unfairly dominating search results.

2. **Inverse Document Frequency (IDF)**: How unique or informative a word is across the entire collection of $N$ documents:
   $$\text{IDF}(t) = \ln\left(\frac{N + 1}{\text{DF}(t) + 1}\right) + 1.0$$
   Words that appear in almost every document (common terms) receive a low IDF, while rare words receive a higher weight.

3. **Title Boost**:
   Words appearing in the `<title>` tag receive a $2\times$ multiplier boost.

4. **Heap Selection (`heapq.nlargest`)**:
   Instead of sorting all documents ($O(M \log M)$), we maintain a min-heap of size $K=10$ to retrieve the top-10 results in $O(M \log K)$ time.

### 3. Prefix Trie for Autocomplete (`engine/trie.py`)
A **Trie (Prefix Tree)** is an $n$-ary tree where each node represents a character.
- Inserting a word of length $L$ takes $O(L)$ time.
- Looking up a prefix of length $P$ takes $O(P)$ time.
- Once the prefix node is reached, a quick Depth-First Search (DFS) collects all matching candidate words, ranked by historical appearance frequency.

---

## 📂 Project Structure

```text
SearchEnginePython/
├── app.py                 # FastAPI routes: /, /search, /suggest
├── requirements.txt       # Project dependencies
├── README.md              # Project documentation and guide
├── .gitignore             # Ignored git files (caches, virtualenvs)
├── engine/
│   ├── __init__.py
│   ├── parser.py          # BeautifulSoup HTML parser (strips script/style)
│   ├── tokenizer.py       # Regex tokenization, stop words, Porter stemmer
│   ├── indexer.py         # InvertedIndex data structure
│   ├── ranker.py          # TF-IDF math, title boost, snippet extraction, heapq
│   └── trie.py            # Trie prefix tree for live autocomplete
├── scripts/
│   └── build_index.py     # Parses data/docs/, builds index + trie, saves data/index.pkl
├── data/
│   ├── index.pkl          # Serialized search index + trie
│   └── docs/              # Python documentation HTML files
│       ├── dictionaries.html
│       ├── functions.html
│       ├── lists.html
│       ├── sorting.html
│       └── tuples.html
├── templates/
│   └── index.html         # Clean frontend search interface
├── static/
│   ├── style.css          # Modern card layout and badge styles
│   └── script.js          # Live autocomplete fetch, keyboard nav, AJAX search
└── tests/
    └── test_engine.py     # Comprehensive pytest test suite for all DSA modules
```

---

## 🚀 Setup and Installation

### 1. Prerequisites
- Python 3.9+ installed on your system.

### 2. Install Dependencies
Open your terminal in the project root directory and run:
```bash
pip install -r requirements.txt
```

---

## 🛠️ How to Run

### Step 1: Build the Search Index & Trie
Process all documentation files inside `data/docs/` and build `data/index.pkl`:
```bash
python scripts/build_index.py
```

*Output:*
```text
Found 5 HTML files to index...
  [0] Indexed 'dictionaries.html' (Title: 'Python Dictionaries - Mapping Types', Tokens: 53)
  [1] Indexed 'functions.html' (Title: 'Defining Functions in Python', Tokens: 41)
  [2] Indexed 'lists.html' (Title: 'Python Lists - Data Structures', Tokens: 58)
  [3] Indexed 'sorting.html' (Title: 'Sorting Techniques - Python HOWTO', Tokens: 52)
  [4] Indexed 'tuples.html' (Title: 'Tuples and Sequences - Python Tutorial', Tokens: 50)

Index successfully built and saved to 'data/index.pkl'.
```

### Step 2: (Optional) Test the Ranker in the Terminal
You can run query ranking directly from your CLI:
```bash
python engine/ranker.py
```

### Step 3: Start the Web Server
Launch the FastAPI application using Uvicorn:
```bash
uvicorn app:app --reload --port 8000
```

Now open your web browser and navigate to:
👉 **http://localhost:8000**

- **Live Autocomplete**: Start typing `so` or `di` to see suggestions pop up under the search bar.
- **Search**: Press Enter on queries like `sort a dictionary`, `python lists`, or `immutable sequences`.
- **Snippet & Score**: View the snippet showing context around your keywords along with calculated TF-IDF relevance scores.
- **Empty States**: Queries with no matches cleanly display a friendly "No results found" container.

---

## 🧪 Running Automated Tests

Run the Pytest suite to verify the tokenizer, indexer, ranker, and trie:
```bash
pytest -v
```

All 10 tests will execute and pass:
```text
tests/test_engine.py::test_tokenizer_clean_words PASSED
tests/test_engine.py::test_tokenizer_stop_words_and_stemming PASSED
tests/test_engine.py::test_stem_word PASSED
tests/test_engine.py::test_inverted_index_postings PASSED
tests/test_engine.py::test_inverted_index_metadata PASSED
tests/test_engine.py::test_tf_idf_math PASSED
tests/test_engine.py::test_snippet_generation PASSED
tests/test_engine.py::test_ranker_search PASSED
tests/test_engine.py::test_trie_insert_and_suggest PASSED
tests/test_engine.py::test_trie_case_insensitivity PASSED
```

---

## 📈 Adding Real Python Documentation

You can index real documentation across nested subdirectories:
1. Download official Python HTML documentation pages (from [docs.python.org](https://docs.python.org/3/)).
2. Place documentation folders like `tutorial/`, `library/`, `reference/`, `howto/`, `faq/`, `using/` inside `data/docs/`:
   ```text
   data/docs/
   ├── tutorial/
   │   ├── datastructures.html
   │   └── controlflow.html
   ├── library/
   │   ├── functions.html
   │   └── stdtypes.html
   ├── howto/
   │   └── sorting.html
   ├── reference/
   ├── faq/
   └── using/
   ```
3. Run the indexing script once:
   ```bash
   python scripts/build_index.py
   ```
   The indexer will recursively scan all subfolders, preserve paths like `tutorial/datastructures.html` on the result badges, and make them clickable in the web browser.
4. Refresh your browser — all pages are now searchable!

---

## 💡 Possible Improvements

For future enhancements or final year project expansions, consider adding:
1. **Preserving Code Block Formatting**: Currently, code examples inside `<pre>` and `<code>` blocks are flattened into single-spaced prose (`>>> sorted ( [ 5 , 2 , 3 , 1 , 4 ] )`) for consistent indexing. A richer parser could preserve newlines and indentation inside `<pre>` blocks specifically for preview rendering.
2. **Okapi BM25 Ranking**: An evolution of TF-IDF incorporating document length saturation and tunable hyperparameters ($k_1$, $b$).
3. **Phrase Search & Positional Index**: Store word positions (`{doc_id: [pos1, pos2]}`) to support exact phrase queries (e.g., `"list comprehension"`).
4. **Fuzzy Search / Spelling Correction**: Implement Levenshtein Distance or SymSpell on the Trie to suggest corrections for misspelled queries (e.g., `dictionry` $\rightarrow$ `dictionary`).
5. **Boolean Operators**: Support explicit boolean syntax like `AND`, `OR`, `NOT` across postings lists.
6. **Snippet Keyword Highlighting**: Wrap matched words in `<mark>` tags in the HTML snippet for visual emphasis.

---

## 🔬 Parser Tuning & Ranking Impact (Case Study)

In official Python documentation (Sphinx theme), pages include top-level navigation headers, version switchers, and permalink anchors (`<a class="headerlink">¶</a>`). 

- **Before Tuning**: The parser read all `<body>` text. Common words like *"Navigation"*, *"modules"*, *"previous"*, and *"Theme"* contaminated the index. Searching for `"lists"` gave skewed results where unrelated modules with large navigation trees ranked artificially high.
- **After Tuning**: 
  1. The parser isolates the main container (`<div role="main">` or `<div class="body">`).
  2. Strips `<nav>`, `class="related"`, `class="sphinxsidebar"`, and `a.headerlink` (`¶`).
  3. Collapses whitespace and cuts previews cleanly on a word boundary (`rsplit(' ', 1)`).
- **Result**: For the query `"lists"`, **`5. Data Structures` (`tutorial/datastructures.html`) immediately jumped to rank #1**, and for `"sort a dictionary"`, **`Sorting Techniques` (`howto/sorting.html`) took rank #1** with a clear, readable preview starting right at the page's actual content.

