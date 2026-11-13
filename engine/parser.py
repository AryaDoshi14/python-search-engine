"""
engine/parser.py
Extracts the title, clean main text, and a word-bounded preview from an HTML document
using BeautifulSoup. Targets Sphinx/Python documentation main content containers
and removes navigation, sidebar boilerplate, and permalink anchors.
"""

from bs4 import BeautifulSoup


# Takes in: file_path (string) - the path to an HTML file on disk
# Returns: tuple of (title, clean_text, preview)
#          - title (string): the clean document title
#          - clean_text (string): main body text with navigation stripped and single spacing
#          - preview (string): clean preview text up to ~1500 characters cut on a word boundary
def parse_html(file_path: str):
    """
    Reads an HTML file, isolates the main content area, removes scripts, styles,
    navigation headers, and Sphinx permalink anchors ('¶'), and produces clean text and preview.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Pick the main content container
    main = (soup.find("div", role="main")
            or soup.find("div", class_="body")
            or soup.find("main")
            or soup.find("div", class_="document")
            or soup)

    # 2. Remove unwanted tags from the main content
    for tag in main.find_all(["script", "style", "nav", "noscript"]):
        tag.decompose()
    for tag in main.find_all("a", class_="headerlink"):  # the ¶ permalink anchors
        tag.decompose()
    for tag in main.find_all(class_=["related", "sphinxsidebar", "mobile-menu", "mobile-nav"]):
        tag.decompose()

    # 3. Clean the text: collapse all whitespace and newlines to single spaces
    clean_text = " ".join(main.get_text(" ").split())

    # 4. Build the preview without cutting a word in half
    preview = clean_text[:1500]
    if len(clean_text) > 1500:
        preview = preview.rsplit(" ", 1)[0] + "..."

    # 5. Extract title
    if soup.title and soup.title.get_text():
        title = soup.title.get_text().strip()
        # Remove repetitive documentation suffixes (e.g. ' — Python 3.15.2 documentation')
        for sep in [" — Python ", " – Python ", " - Python "]:
            if sep in title:
                title = title.split(sep)[0].strip()
                break
    else:
        first_h1 = main.find("h1") or soup.find("h1")
        title = first_h1.get_text().strip() if first_h1 else "Untitled Document"

    return title, clean_text, preview
