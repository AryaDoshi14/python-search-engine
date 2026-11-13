/**
 * static/script.js
 * Handles live autocomplete suggestions and search execution.
 * Communicates with backend endpoints:
 *   - GET /suggest?q=...
 *   - GET /search?q=...
 */

document.addEventListener("DOMContentLoaded", () => {
    const searchForm = document.getElementById("search-form");
    const queryInput = document.getElementById("query-input");
    const suggestionsList = document.getElementById("suggestions-list");
    const resultsContainer = document.getElementById("results-container");
    const statusBar = document.getElementById("status-bar");

    // Modal popup elements
    const modalOverlay = document.getElementById("modal-overlay");
    const modalTitle = document.getElementById("modal-title");
    const modalFile = document.getElementById("modal-file");
    const modalPreview = document.getElementById("modal-preview");
    const modalCloseBtn = document.getElementById("modal-close-btn");

    let debounceTimer = null;
    let activeSuggestionIndex = -1;

    // ==========================================
    // 1. AUTOCOMPLETE / SUGGESTIONS
    // ==========================================

    // Listens for keystrokes in the search input
    queryInput.addEventListener("input", (e) => {
        const query = e.target.value.trim();

        // Clear any pending debounce timer
        clearTimeout(debounceTimer);

        if (!query) {
            hideSuggestions();
            return;
        }

        // Debounce: wait 150ms after user stops typing before fetching suggestions
        debounceTimer = setTimeout(() => {
            fetchSuggestions(query);
        }, 150);
    });

    // Takes in: prefix (string) - the starting letters typed by user
    // Returns: None - updates suggestions dropdown in the DOM
    async function fetchSuggestions(prefix) {
        try {
            const response = await fetch(`/suggest?q=${encodeURIComponent(prefix)}`);
            if (!response.ok) return;

            const suggestions = await response.json();
            renderSuggestions(suggestions);
        } catch (error) {
            console.error("Error fetching suggestions:", error);
        }
    }

    // Takes in: suggestions (array of strings)
    // Returns: None - creates <li> elements inside suggestionsList
    function renderSuggestions(suggestions) {
        suggestionsList.innerHTML = "";
        activeSuggestionIndex = -1;

        if (!suggestions || suggestions.length === 0) {
            hideSuggestions();
            return;
        }

        suggestions.forEach((word) => {
            const li = document.createElement("li");
            li.className = "suggestion-item";
            li.innerHTML = `<span class="suggestion-icon">&#128269;</span> <span>${word}</span>`;

            // When a suggestion is clicked: populate input, hide suggestions, and perform search
            li.addEventListener("click", () => {
                queryInput.value = word;
                hideSuggestions();
                performSearch(word);
            });

            suggestionsList.appendChild(li);
        });

        suggestionsList.classList.remove("hidden");
    }

    function hideSuggestions() {
        suggestionsList.classList.add("hidden");
        suggestionsList.innerHTML = "";
        activeSuggestionIndex = -1;
    }

    // Close suggestions if clicked outside the search section
    document.addEventListener("click", (e) => {
        if (!e.target.closest(".search-box-wrapper")) {
            hideSuggestions();
        }
    });

    // ==========================================
    // 2. KEYBOARD NAVIGATION IN SUGGESTIONS
    // ==========================================

    queryInput.addEventListener("keydown", (e) => {
        const items = suggestionsList.querySelectorAll(".suggestion-item");

        if (e.key === "ArrowDown") {
            // Move selection down
            if (items.length > 0) {
                e.preventDefault();
                activeSuggestionIndex = (activeSuggestionIndex + 1) % items.length;
                updateActiveSuggestion(items);
            }
        } else if (e.key === "ArrowUp") {
            // Move selection up
            if (items.length > 0) {
                e.preventDefault();
                activeSuggestionIndex = (activeSuggestionIndex - 1 + items.length) % items.length;
                updateActiveSuggestion(items);
            }
        } else if (e.key === "Enter") {
            // If a suggestion is highlighted, use it; otherwise search current input
            if (activeSuggestionIndex >= 0 && items[activeSuggestionIndex]) {
                e.preventDefault();
                const selectedWord = items[activeSuggestionIndex].querySelector("span:last-child").textContent;
                queryInput.value = selectedWord;
                hideSuggestions();
                performSearch(selectedWord);
            } else {
                hideSuggestions();
                performSearch(queryInput.value.trim());
            }
        } else if (e.key === "Escape") {
            hideSuggestions();
        }
    });

    function updateActiveSuggestion(items) {
        items.forEach((item, index) => {
            if (index === activeSuggestionIndex) {
                item.classList.add("active");
                // Put text into input as preview
                queryInput.value = item.querySelector("span:last-child").textContent;
            } else {
                item.classList.remove("active");
            }
        });
    }

    // ==========================================
    // 3. SEARCH EXECUTION
    // ==========================================

    // Handles form submission
    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        hideSuggestions();
        performSearch(queryInput.value.trim());
    });

    // Takes in: query (string) - search query text
    // Returns: None - fetches results from backend and renders result cards
    async function performSearch(query) {
        if (!query) return;

        statusBar.textContent = `Searching for "${query}"...`;
        resultsContainer.innerHTML = "";

        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                statusBar.textContent = "Error connecting to search server.";
                return;
            }

            const data = await response.json();
            renderResults(data);
        } catch (error) {
            console.error("Search error:", error);
            statusBar.textContent = "Error occurred while searching.";
        }
    }

    // Takes in: data (object) - { query: string, total_results: int, results: array }
    // Returns: None - displays result cards or friendly empty state
    function renderResults(data) {
        const { query, results } = data;

        if (!results || results.length === 0) {
            statusBar.textContent = `0 results found for "${query}"`;
            resultsContainer.innerHTML = `
                <div class="no-results">
                    <div class="no-results-icon">&#128269;</div>
                    <h3>No results found</h3>
                    <p>We couldn't find any documents matching "<strong>${escapeHtml(query)}</strong>".</p>
                    <p style="margin-top: 8px; font-size: 0.85rem; color: #94a3b8;">
                        Try checking your spelling or using different keywords like "lists", "dictionaries", or "sorting".
                    </p>
                </div>
            `;
            return;
        }

        statusBar.textContent = `Found ${results.length} result${results.length === 1 ? '' : 's'} for "${query}"`;
        resultsContainer.innerHTML = "";

        results.forEach((item) => {
            const card = document.createElement("article");
            card.className = "result-card";
            card.innerHTML = `
                <div class="result-header">
                    <h2 class="result-title">${escapeHtml(item.title)}</h2>
                    <div class="result-badges">
                        <span class="result-file">${escapeHtml(item.filename)}</span>
                        <span class="result-score">Score: ${item.score}</span>
                    </div>
                </div>
                <p class="result-snippet">${highlightQuery(item.snippet, query)}</p>
            `;

            // Open document preview popup when clicking the card
            card.addEventListener("click", () => {
                openModal(item, query);
            });

            resultsContainer.appendChild(card);
        });
    }

    // ==========================================
    // 4. DOCUMENT PREVIEW POPUP (MODAL)
    // ==========================================

    // Takes in: item (object) - { title, filename, snippet, preview, score }
    //           query (string) - the search query for keyword highlighting
    // Returns: None - opens modal popup and locks background scrolling
    function openModal(item, query) {
        modalTitle.textContent = item.title || "Untitled Document";
        modalFile.textContent = item.filename || "";

        // For the popup: escape HTML first, then format code blocks, then highlight
        let popupText = item.preview || item.snippet || "No preview text available.";
        let escaped = escapeHtml(popupText);
        escaped = formatCodeBlocks(escaped);
        modalPreview.innerHTML = highlightQuery._rawHighlight(escaped, query);

        modalOverlay.classList.remove("hidden");
        document.body.classList.add("modal-open");
    }

    // Takes in: escaped HTML string with flattened Python REPL lines
    // Returns: string with line breaks before >>> prompts, tidied spacing,
    //          and each REPL line wrapped in a <span class="repl-line">
    function formatCodeBlocks(html) {
        // 1. Insert a newline before every ">>>" so each prompt starts on its own line
        //    &gt;&gt;&gt; is the escaped form of >>>
        html = html.replace(/\s*(&gt;&gt;&gt;)/g, "\n$1");

        // 2. Insert a newline before "..." continuation lines that follow >>> lines
        //    Only match "..." that comes after a >>> line (preceded by newline)
        html = html.replace(/(\n&gt;&gt;&gt;[^\n]*)\s+(\.\.\.)/g, "$1\n$2");

        // 3. Tidy spacing inside >>> lines: remove spaces before ( ) , .
        //    Process each line that starts with &gt;&gt;&gt;
        html = html.replace(/^(&gt;&gt;&gt;.*)$/gm, function(line) {
            return line
                .replace(/ \(/g, "(")     // "sorted (" -> "sorted("
                .replace(/ \)/g, ")")     // " )" -> ")"
                .replace(/ ,/g, ",")      // " ," -> ","
                .replace(/ \./g, ".");    // " ." -> "."
        });

        // 4. Wrap each >>> line in a <span class="repl-line"> for styling
        html = html.replace(/^(&gt;&gt;&gt;.*)$/gm, '<span class="repl-line">$1</span>');

        // Also wrap ... continuation lines
        html = html.replace(/^(\.\.\..*)$/gm, '<span class="repl-line">$1</span>');

        return html;
    }

    // Closes the popup modal and restores background scrolling
    function closeModal() {
        modalOverlay.classList.add("hidden");
        document.body.classList.remove("modal-open");
    }

    // Close button click
    modalCloseBtn.addEventListener("click", closeModal);

    // Close when clicking outside the modal card (on the dark overlay)
    modalOverlay.addEventListener("click", (e) => {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });

    // Close when pressing the Escape key
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modalOverlay.classList.contains("hidden")) {
            closeModal();
        }
    });

    // Helper function to safely escape HTML special characters
    function escapeHtml(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Safely escapes text first, then highlights query keywords using <mark> tags
    // Used for card snippets (plain text, no code formatting)
    function highlightQuery(text, query) {
        if (!text) return "";
        // 1. Escape HTML special characters first to prevent XSS injection
        let escaped = escapeHtml(text);
        if (!query || !query.trim()) return escaped;

        // 2. Apply highlight to the escaped text
        return highlightQuery._rawHighlight(escaped, query);
    }

    // Takes in: already-escaped HTML string and query string
    // Returns: HTML with <mark> tags around matching words
    // Used by both highlightQuery() and openModal() (after formatCodeBlocks)
    highlightQuery._rawHighlight = function(escaped, query) {
        if (!query || !query.trim()) return escaped;

        // Extract alphanumeric query words of length >= 2
        const words = query
            .trim()
            .split(/\s+/)
            .map(w => w.replace(/[^a-zA-Z0-9]/g, ""))
            .filter(w => w.length >= 2);

        if (words.length === 0) return escaped;

        // Match each word or its prefix/stem at word boundaries
        const escapedWords = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
        const regex = new RegExp(`\\b(${escapedWords.join("|")})\\w*`, "gi");

        // Wrap with <mark> tags
        return escaped.replace(regex, (match) => `<mark>${match}</mark>`);
    };
});

