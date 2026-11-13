"""
scripts/build_index.py
Processes all HTML files in data/docs/, extracts text, tokenizes,
builds the Inverted Index, and serializes the index to data/index.pkl.
"""

import os
import sys
import pickle

# Ensure the project root directory is on the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.parser import parse_html
from engine.tokenizer import tokenize, extract_words


# Takes in: docs_dir (string) - directory containing HTML files
#           output_path (string) - filepath where the pickle file should be saved
# Returns: tuple of (InvertedIndex, Trie or None)
def build_and_save_index(docs_dir: str = "data/docs", output_path: str = "data/index.pkl"):
    """
    Parses all documents in docs_dir, builds the Inverted Index,
    and saves the indexed data using pickle.
    """
    from engine.indexer import InvertedIndex

    # Optional: Try importing Trie if already implemented (for Stage D)
    try:
        from engine.trie import Trie
        trie = Trie()
    except (ImportError, ModuleNotFoundError):
        trie = None

    index = InvertedIndex()

    if not os.path.exists(docs_dir):
        print(f"Error: Directory '{docs_dir}' does not exist.")
        return None, None

    # Recursively find all HTML files in docs_dir and any subdirectories (e.g. tutorial, library, howto, etc.)
    doc_entries = []
    for root, _, files in os.walk(docs_dir):
        for file in files:
            if file.lower().endswith((".html", ".htm")):
                full_path = os.path.join(root, file)
                # Normalize relative path to forward slashes (e.g. "tutorial/datastructures.html")
                rel_path = os.path.relpath(full_path, docs_dir).replace("\\", "/")
                doc_entries.append((full_path, rel_path))

    if not doc_entries:
        print(f"No HTML files found in '{docs_dir}' or its subdirectories.")
        return None, None

    # Sort deterministically by relative path
    doc_entries.sort(key=lambda item: item[1])
    print(f"Found {len(doc_entries)} HTML files across folders to index...")

    # Collect all document full clean texts in a separate dictionary
    full_texts = {}

    for doc_id, (file_path, rel_path) in enumerate(doc_entries):
        title, clean_text, preview = parse_html(file_path)

        # Store full clean text by doc_id
        full_texts[doc_id] = clean_text

        # Tokenize body and title (for TF-IDF matching and title boosting)
        tokens = tokenize(clean_text)
        title_tokens = tokenize(title)

        # Index the document
        index.add_document(
            doc_id=doc_id,
            title=title,
            filename=rel_path,
            raw_text=clean_text,
            tokens=tokens,
            title_tokens=title_tokens,
            preview=preview
        )

        # If Trie is available, insert unstemmed words and title terms for autocomplete
        if trie is not None:
            # Add words from page title
            for word in extract_words(title):
                if len(word) >= 2:
                    trie.insert(word)
            # Add words from body text
            for word in extract_words(clean_text):
                if len(word) >= 2:
                    trie.insert(word)

        print(f"  [{doc_id}] Indexed '{rel_path}' (Title: '{title}', Tokens: {len(tokens)})")

    # Ensure parent directory for output_path exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Compute average document length across all indexed documents (for BM25 scoring)
    avg_doc_length = (
        sum(index.doc_lengths.values()) / index.total_docs
        if index.total_docs > 0 else 0.0
    )
    index.avg_doc_length = avg_doc_length
    print(f"\nIndexed {index.total_docs} documents. Average document length: {avg_doc_length:.2f} tokens.")

    # Save full clean texts to a separate file data/texts.pkl so index.pkl stays compact
    texts_path = os.path.join(os.path.dirname(output_path), "texts.pkl")
    with open(texts_path, "wb") as f:
        pickle.dump(full_texts, f)
    print(f"Full clean page texts saved to '{texts_path}'.")

    # Package index data to save
    payload = {
        "inverted_index": index,
        "trie": trie,
        "avg_doc_length": avg_doc_length,
        "doc_lengths": index.doc_lengths
    }

    # Save to disk using pickle
    with open(output_path, "wb") as f:
        pickle.dump(payload, f)

    print(f"Index successfully built and saved to '{output_path}'.")
    return index, trie, full_texts


if __name__ == "__main__":
    build_and_save_index()
