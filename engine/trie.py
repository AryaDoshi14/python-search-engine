"""
engine/trie.py
A Trie (Prefix Tree) data structure for fast prefix-based autocomplete suggestions.
Each node stores child character links, whether it marks the end of a word,
and the word's appearance frequency.
"""


class TrieNode:
    """
    A single node in the Trie.
    """
    def __init__(self):
        # Maps a character to its child TrieNode: { 'a': TrieNode, ... }
        self.children = {}
        # True if this node represents the end of a complete word
        self.is_end_of_word = False
        # Holds the full unstemmed word string at end nodes for easy retrieval
        self.word = None
        # Frequency count: how many times this word appeared across documents
        self.frequency = 0


class Trie:
    """
    Trie (Prefix Tree) supporting insertion and prefix-based autocomplete suggestions.
    """
    def __init__(self):
        self.root = TrieNode()

    # Takes in: word (string) - unstemmed word to insert
    # Returns: None
    def insert(self, word: str):
        """
        Inserts a word into the trie character by character,
        and increments its occurrence frequency.
        """
        if not word:
            return

        word = word.lower().strip()
        current_node = self.root

        for char in word:
            if char not in current_node.children:
                current_node.children[char] = TrieNode()
            current_node = current_node.children[char]

        current_node.is_end_of_word = True
        current_node.word = word
        current_node.frequency += 1

    # Takes in: prefix (string) - starting characters typed by the user
    #           limit (int) - maximum number of suggestions to return (default: 5)
    # Returns: list of strings - up to 'limit' autocomplete suggestions
    def suggest(self, prefix: str, limit: int = 5) -> list:
        """
        Finds all words in the trie that start with 'prefix',
        ranked by frequency (most frequent first), returning up to 'limit' words.
        """
        if not prefix:
            return []

        prefix = prefix.lower().strip()
        current_node = self.root

        # 1. Walk down the trie following the characters in 'prefix'
        for char in prefix:
            if char not in current_node.children:
                return []  # Prefix not found in the trie
            current_node = current_node.children[char]

        # 2. Collect all complete words under this prefix node using DFS
        matched_words = []

        def dfs(node):
            if node.is_end_of_word:
                matched_words.append((node.frequency, node.word))
            for child in node.children.values():
                dfs(child)

        dfs(current_node)

        # 3. Sort by highest frequency first, then alphabetically
        matched_words.sort(key=lambda item: (-item[0], item[1]))

        # 4. Return top 'limit' words
        return [word for _, word in matched_words[:limit]]

