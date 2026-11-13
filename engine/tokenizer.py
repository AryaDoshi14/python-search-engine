"""
engine/tokenizer.py
Cleans and transforms raw text into search tokens:
1. Converts text to lowercase
2. Extracts word tokens using regular expressions
3. Removes English stop words (like 'the', 'is', 'at')
4. Applies Porter Stemming (reduces words like 'sorting', 'sorted' -> 'sort')
"""

import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Ensure stopwords are available; download if missing
try:
    STOP_WORDS = set(stopwords.words("english"))
except LookupError:
    nltk.download("stopwords", quiet=True)
    STOP_WORDS = set(stopwords.words("english"))

# Initialize Porter Stemmer once
STEMMER = PorterStemmer()


# Takes in: text (string) - any raw text string
# Returns: list of strings - lowercase words with punctuation removed (unstemmed)
def extract_words(text: str):
    """
    Splits text into lowercase alphanumeric words.
    Useful for autocomplete suggestions where we want readable, unstemmed words.
    """
    if not text:
        return []
    # Match sequences of word characters (alphanumeric and underscores)
    return re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())


# Takes in: text (string) - raw text to tokenize
# Returns: list of strings - stemmed tokens with stop words removed
def tokenize(text: str):
    """
    Processes raw text for search indexing and querying:
    lowercase -> split words -> remove stopwords -> apply Porter stemming.
    """
    words = extract_words(text)
    tokens = []

    for word in words:
        # Ignore common stop words (e.g., 'the', 'in', 'and')
        # We keep single characters only if they are meaningful (skip 1-letter noise except 'a' is a stopword anyway)
        if word not in STOP_WORDS and len(word) > 1:
            stemmed_word = STEMMER.stem(word)
            tokens.append(stemmed_word)

    return tokens


# Takes in: word (string) - a single word
# Returns: string - stemmed version of the word
def stem_word(word: str):
    """
    Stems a single word using PorterStemmer.
    """
    return STEMMER.stem(word.lower())

