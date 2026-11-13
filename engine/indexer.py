"""
engine/indexer.py
Constructs and manages an Inverted Index data structure.
An Inverted Index maps each word (token) to the documents where it appears,
along with the frequency (count) of that word in each document.
"""

from collections import defaultdict


class InvertedIndex:
    """
    Inverted Index data structure for full-text search.

    Structure:
      index: {
          "sort": { 0: 5, 2: 3 },
          "dictionari": { 1: 4, 2: 1 }
      }
      doc_lengths: { 0: 42, 1: 56, 2: 60 }
      doc_metadata: {
          0: { "title": "...", "filename": "...", "raw_text": "...", "title_tokens": [...] }
      }
    """

    def __init__(self):
        # Maps term -> { doc_id: frequency_count }
        self.index = defaultdict(dict)
        # Maps doc_id -> total number of tokens in the document
        self.doc_lengths = {}
        # Maps doc_id -> dictionary of document info (title, filename, raw text, etc.)
        self.doc_metadata = {}
        # Total number of indexed documents
        self.total_docs = 0
        # Average token length across all indexed documents (used for BM25)
        self.avg_doc_length = 0.0

    # Takes in: doc_id (int) - unique identifier for the document
    #           title (string) - page title
    #           filename (string) - file name (e.g., 'tutorial/datastructures.html')
    #           raw_text (string) - clean body text for snippet generation
    #           tokens (list of strings) - stemmed tokens from the document text
    #           title_tokens (list of strings) - stemmed tokens from the document title
    #           preview (string, optional) - word-bounded preview for modal popup
    # Returns: None
    def add_document(self, doc_id: int, title: str, filename: str, raw_text: str, tokens: list, title_tokens: list, preview: str = None):
        """
        Indexes a single document by counting word frequencies and storing metadata.
        """
        if preview is None:
            preview = raw_text[:1500] if raw_text else ""
            if len(raw_text) > 1500:
                preview = preview.rsplit(" ", 1)[0] + "..."

        self.doc_lengths[doc_id] = len(tokens)
        self.doc_metadata[doc_id] = {
            "title": title,
            "filename": filename,
            "raw_text": raw_text,
            "preview": preview,
            "title_tokens": set(title_tokens)
        }

        # Count frequencies of each token in this document
        for token in tokens:
            if doc_id not in self.index[token]:
                self.index[token][doc_id] = 1
            else:
                self.index[token][doc_id] += 1

        self.total_docs = len(self.doc_lengths)

    # Takes in: term (string) - a stemmed token
    # Returns: dict - { doc_id: frequency } mapping of documents containing the term, or {}
    def get_postings(self, term: str) -> dict:
        """
        Returns the postings list for a given term.
        """
        return self.index.get(term, {})

    # Takes in: term (string) - a stemmed token
    # Returns: int - count of documents that contain the term
    def get_doc_freq(self, term: str) -> int:
        """
        Returns how many documents contain this term (Document Frequency - DF).
        """
        return len(self.index.get(term, {}))

    # Takes in: doc_id (int) - unique document ID
    # Returns: int - total number of tokens in this document
    def get_doc_length(self, doc_id: int) -> int:
        """
        Returns the token length of a document.
        """
        return self.doc_lengths.get(doc_id, 0)

    # Takes in: doc_id (int) - unique document ID
    # Returns: dict - metadata dictionary containing title, filename, raw_text, and title_tokens
    def get_metadata(self, doc_id: int) -> dict:
        """
        Returns the stored metadata for a document.
        """
        return self.doc_metadata.get(doc_id, {})

    # Takes in: None
    # Returns: float - average token length across all indexed documents
    def get_avg_doc_length(self) -> float:
        """
        Returns the average document length across the collection.
        """
        if getattr(self, "avg_doc_length", 0.0) > 0:
            return self.avg_doc_length
        if self.total_docs > 0:
            return sum(self.doc_lengths.values()) / self.total_docs
        return 0.0

