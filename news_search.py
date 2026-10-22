import requests, feedparser, re, csv
from bs4 import BeautifulSoup
from urllib.parse import quote


STOP = {
    "the","a","an","is","are","was","were","has","have","had","to","of",
    "in","on","for","and","or","with","this","that","from","by","will",
    "be","been","their","they","it","its","as","at","into","about",
    "after","before","according","says","said","claim","claims","news",
    "report","reports","reported"
}

RULES = list(csv.DictReader(open("data/evidence_rules.csv", encoding="utf-8")))
GLOBAL_TERMS = {r["value"] for r in RULES if r["type"] == "scope" and r["category"] == "global"}


def get_source_score(source):
    source = source.lower()

    scores = {
        5: [
            "reuters", "associated press", "ap news", "bbc",
            "nasa", "isro", "pib", "who", "un", "gov"
        ],
        4: [
            "ndtv", "the hindu", "indian express", "india today",
            "times of india", "cnbc", "businessline",
            "moneycontrol", "economic times", "business standard",
            "techcrunch", "yahoo finance", "newsonair", "dw",
            "lawfare", "associated press"
        ],
        3: [
            "new scientist", "science daily", "scientific american",
            "nature", "university", "college", "edu",
            "science.feedback", "yourstory", "hindustan times",
            "statesman", "space daily", "ani news", "jagran josh"
        ]
    }

    for score, names in scores.items():
        if any(name in source for name in names):
            return score

    return 1


def clean_text(text):
    return re.sub(r"[^a-zA-Z0-9\s-]","",text).strip()


def create_search_queries(text):
    cleaned = clean_text(text)
    words = [
        w for w in cleaned.split()
        if len(w) > 3 and w.lower() not in STOP
    ]

    if not words:
        return [cleaned]

    main = " ".join(words[:10])
    queries = [f'"{cleaned}"', main, main + " fact check"]

    if any(term in cleaned.lower() for term in GLOBAL_TERMS):
        queries += [
            main + " worldwide",
            main + " global operations",
            main + " continues operations",
            main + " expansion 2026"
        ]

        if re.search(r"\b(shut down|shutdown|close|closure|exit|withdraw)\b", cleaned.lower()):
            subject = words[0]
            queries += [
                f"{subject} continues operations worldwide",
                f"{subject} global operations 2026",
                f"{subject} expands globally 2026"
            ]

    return queries

def result_score(title,claim):
    title_words = {
        w.lower()
        for w in clean_text(title).split()
        if len(w) > 3 and w.lower() not in STOP
    }

    claim_words = {
        w.lower()
        for w in clean_text(claim).split()
        if len(w) > 3 and w.lower() not in STOP
    }

    if not claim_words:
        return 0

    return len(title_words & claim_words) / len(claim_words)


def get_article_body(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent":"Mozilla/5.0"},
            timeout=3
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text,"html.parser")

        for tag in soup([
            "script","style","nav","header","footer","aside"
        ]):
            tag.decompose()

        paragraphs = soup.find_all("p")

        return " ".join(
            p.get_text(" ",strip=True)
            for p in paragraphs
        )[:8000]

    except Exception:
        return ""


def search_news(query,max_results=5):

    queries = create_search_queries(query)

    results = []
    seen_titles = set()

    for search in queries:

        print("\nTRUTHLENS SEARCH QUERY:")
        print(search)

        url = (
            "https://news.google.com/rss/search?"
            f"q={quote(search)}&hl=en-IN&gl=IN&ceid=IN:en"
        )

        try:
            response = requests.get(
                url,
                headers={"User-Agent":"Mozilla/5.0"},
                timeout=5
            )

            response.raise_for_status()

            feed = feedparser.parse(response.content)

            for entry in feed.entries:

                title = entry.get("title","").strip()

                if not title:
                    continue

                key = title.lower()

                if key in seen_titles:
                    continue

                seen_titles.add(key)

                source = ""

                if hasattr(entry,"source"):
                    source = entry.source.get("title","")

                results.append({
                    "title": title,
                    "link": entry.get("link",""),
                    "published": entry.get("published",""),
                    "source": source,
                    "source_score": get_source_score(source),
                    "search_score": result_score(title,query),
                    "body": ""
                })

        except Exception as error:
            print("Search error:",error)

    results.sort(
        key=lambda r: (
            r.get("search_score",0),
            r.get("source_score",1)
        ),
        reverse=True
    )

    results = results[:max_results * 2]

    print(f"\nTOP RESULTS SELECTED: {len(results)}")

    return results