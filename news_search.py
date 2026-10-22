
import requests
import feedparser
import re
import csv
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse

STOP = {
    "the", "and", "for", "with", "that", "this", "from", "have",
    "has", "was", "were", "are", "will", "its", "into", "about",
    "after", "before", "been", "being", "their", "they", "said",
    "says", "news", "report", "reports", "latest", "new", "claim"
}

with open("data/evidence_rules.csv", encoding="utf-8") as file:
    RULES = list(csv.DictReader(file))

GLOBAL_TERMS = {
    r["value"] for r in RULES
    if r["type"] == "scope" and r["category"] == "global"
}

# Known publisher domains and configured source scores
NEWS_SOURCES = {
    "reuters.com": 5,
    "apnews.com": 5,
    "bbc.com": 5,
    "bbc.co.uk": 5,
    "thehindu.com": 4,
    "indianexpress.com": 4,
    "ndtv.com": 4,
    "hindustantimes.com": 4,
    "wionews.com": 4,
    "indiatimes.com": 4,
    "theguardian.com": 4,
    "aljazeera.com": 4,
    "bloomberg.com": 4,
    "ft.com": 4,
    "washingtonpost.com": 4,
    "nytimes.com": 4,
    "cnbc.com": 4,
    "moneycontrol.com": 3,
    "business-standard.com": 3,
    "livemint.com": 3,
    "indiatoday.in": 3,
    "cnn.com": 3,
    "forbes.com": 3,
    "techcrunch.com": 3,
    "theverge.com": 3,
    "scroll.in": 3,
    "deccanherald.com": 3,
    "yourstory.com": 3,
    "inc42.com": 3,
    "financialexpress.com": 3,
    "economictimes.com": 3,
    "theprint.in": 3,
    "firstpost.com": 3
}

SOCIAL_DOMAINS = {
    "facebook.com", "instagram.com", "x.com", "twitter.com",
    "youtube.com", "youtu.be", "linkedin.com", "tiktok.com",
    "reddit.com", "threads.net", "pinterest.com", "snapchat.com",
    "whatsapp.com", "t.me", "telegram.org"
}

OFFICIAL_ACCOUNTS = {
    "press information bureau": 5,
    "pib india": 5,
    "isro": 5,
    "nasa": 5,
    "world health organization": 5,
    "who": 5,
    "united nations": 5,
    "reserve bank of india": 5,
    "rbi": 5,
    "election commission of india": 5,
    "ministry of health and family welfare": 5
}

# Publisher-name fallbacks for Google News RSS results
PUBLISHER_SCORES = {
    5: [
        "reuters", "associated press", "ap news",
        "bbc", "nasa", "isro"
    ],
    4: [
        "the hindu", "indian express", "ndtv",
        "hindustan times", "wion", "times of india",
        "the guardian", "al jazeera", "bloomberg",
        "economic times", "news on air", "newsonair",
        "france 24", "new indian express", "cnbc tv18"
    ],
    3: [
        "assam tribune", "moneycontrol", "business standard",
        "livemint", "india today", "cnn", "forbes",
        "techcrunch", "swarajya", "news24online",
        "free press journal", "rediff", "the statesman",
        "outlook india", "cricket addictor",
        "gujarat samachar", "open magazine",
        "news mobile", "daily excelsior", "etv bharat",
        "upstox", "apa.az", "swarajyamag",
        "times now", "telangana today", "news18",
        "lokmat times", "free press kashmir",
        "marine insight", "firstpost"
    ]
}


def get_domain(url):
    if not url:
        return ""

    if "://" not in url:
        url = "//" + url

    domain = urlparse(url).hostname or ""
    return domain.lower().removeprefix("www.")


def is_social_source(source, link=""):
    source_domain = get_domain(source)
    link_domain = get_domain(link)

    return any(
        domain == site or domain.endswith("." + site)
        for site in SOCIAL_DOMAINS
        for domain in (source_domain, link_domain)
    )


def get_source_score(source, link=""):
    source_name = source.lower().strip()
    domain = get_domain(source)

    # Match recognized publisher domains
    for site, score in NEWS_SOURCES.items():
        if domain == site or domain.endswith("." + site):
            return score

    # Match publisher names supplied by Google News RSS
    for score, names in PUBLISHER_SCORES.items():
        if any(name in source_name for name in names):
            return score

    # Recognize official institutional publishers
    if source_name in OFFICIAL_ACCOUNTS:
        return OFFICIAL_ACCOUNTS[source_name]

    # Exclude ordinary social-media sources from credibility scoring
    if is_social_source(source, link):
        return 0

    return 1


def clean_text(text):
    return re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip()


def create_search_queries(text):
    cleaned = clean_text(text)

    words = [
        word for word in cleaned.split()
        if len(word) > 3 and word.lower() not in STOP
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

        if re.search(
            r"\b(shut down|shutdown|close|closure|exit|withdraw)\b",
            cleaned.lower()
        ):
            subject = words[0]
            queries += [
                f"{subject} continues operations worldwide",
                f"{subject} global operations 2026",
                f"{subject} expansion 2026"
            ]

    return queries


def result_score(title, claim):
    title_words = {
        word.lower() for word in clean_text(title).split()
        if len(word) > 3 and word.lower() not in STOP
    }

    claim_words = {
        word.lower() for word in clean_text(claim).split()
        if len(word) > 3 and word.lower() not in STOP
    }

    if not claim_words:
        return 0

    return len(title_words & claim_words) / len(claim_words)


def get_article_body(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=3
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(
            ["script", "style", "nav", "header", "footer", "aside"]
        ):
            tag.decompose()

        paragraphs = soup.find_all("p")

        return " ".join(
            paragraph.get_text(" ", strip=True)
            for paragraph in paragraphs
        )[:8000]

    except Exception:
        return ""


def search_news(query, max_results=5):
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
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                title = entry.get("title", "").strip()

                if not title:
                    continue

                key = title.lower()

                if key in seen_titles:
                    continue

                link = entry.get("link", "")
                source = ""

                if hasattr(entry, "source"):
                    source = entry.source.get("title", "").strip()

                if not source:
                    source = get_domain(link)

                score = get_source_score(source, link)

                if is_social_source(source, link):
                    if source.lower().strip() not in OFFICIAL_ACCOUNTS:
                        continue

                seen_titles.add(key)

                results.append({
                    "title": title,
                    "link": link,
                    "published": entry.get("published", ""),
                    "source": source,
                    "source_score": score,
                    "search_score": result_score(title, query),
                    "body": ""
                })

        except Exception as error:
            print("Search error:", error)

    results.sort(
        key=lambda result: (
            result.get("search_score", 0),
            result.get("source_score", 1)
        ),
        reverse=True
    )

    results = results[:max_results * 2]

    print(f"\nTOP RESULTS SELECTED: {len(results)}")

    return results
