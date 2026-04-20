import json
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import feedparser
import requests
from dateutil import parser
from dotenv import load_dotenv

load_dotenv()

TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")
if not TEAMS_WEBHOOK_URL:
    raise ValueError("TEAMS_WEBHOOK_URL environment variable is required.")

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "prev_articles.db")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "180"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
REQUEST_TIMEOUT_SECONDS = 15

lock = Lock()

private_rss_feed_list = [
    ["https://grahamcluley.com/feed/", "Graham Cluley"],
    ["https://threatpost.com/feed/", "Threatpost"],
    ["https://krebsonsecurity.com/feed/", "Krebs on Security"],
    ["https://www.darkreading.com/rss.xml", "Dark Reading"],
    ["https://feeds.feedburner.com/eset/blog", "We Live Security"],
    ["https://davinciforensics.co.za/cybersecurity/feed/", "DaVinci Forensics"],
    ["https://blogs.cisco.com/security/feed", "Cisco"],
    ["https://www.infosecurity-magazine.com/rss/news/", "Information Security Magazine"],
    ["https://feeds.feedburner.com/GoogleOnlineSecurityBlog", "Google"],
    ["https://feeds.trendmicro.com/TrendMicroResearch", "Trend Micro"],
    ["https://www.bleepingcomputer.com/feed/", "Bleeping Computer"],
    ["https://www.proofpoint.com/us/rss.xml", "Proof Point"],
    ["https://feeds.feedburner.com/TheHackersNews?format=xml", "Hacker News"],
    ["https://www.schneier.com/feed/atom/", "Schneier on Security"],
    ["https://www.binarydefense.com/feed/", "Binary Defense"],
    ["https://securelist.com/feed/", "Securelist"],
    ["https://research.checkpoint.com/feed/", "Checkpoint Research"],
    ["https://www.virusbulletin.com/rss", "VirusBulletin"],
    ["https://modexp.wordpress.com/feed/", "Modexp"],
    ["https://www.tiraniddo.dev/feeds/posts/default", "James Forshaw"],
    ["https://blog.xpnsec.com/rss.xml", "Adam Chester"],
    ["https://msrc-blog.microsoft.com/feed/", "Microsoft Security"],
    ["https://www.recordedfuture.com/feed", "Recorded Future"],
    ["https://www.sentinelone.com/feed/", "SentinelOne"],
    ["https://redcanary.com/feed/", "RedCanary"],
    ["https://cybersecurity.att.com/site/blog-all-rss", "ATT"],
    ["https://www.cisa.gov/uscert/ncas/alerts.xml", "US-CERT CISA"],
    ["https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml", "NCSC"],
    ["https://www.cisecurity.org/feed/advisories", "Center of Internet Security"],
]

json_feed_url = "https://raw.githubusercontent.com/joshhighet/ransomwatch/main/posts.json"

EDU_KEYWORDS = [
    "university",
    "college",
    "higher education",
    "academic",
    ".edu",
    "campus",
    "universities",
    "student",
    "faculty",
    "tuition",
    "scholarship",
    "professor",
]
SECURITY_KEYWORDS = [
    "ransomware",
    "vulnerabilities",
    "exploit",
    "vulnerability",
    "malware",
    "breach",
    "zero day",
    "zero-day",
    "security patch",
    "hack",
    "apt",
]
BLUE_SOURCES = {"CISA", "US-CERT CISA", "Center of Internet Security", "NCSC"}


def initialize_db() -> None:
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS PREV_ARTICLES (
                source TEXT PRIMARY KEY,
                added_at TEXT NOT NULL DEFAULT current_timestamp
            )
            """
        )


def reserve_article(article_identifier: str) -> bool:
    with lock:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO PREV_ARTICLES (source) VALUES (?)",
                (article_identifier,),
            )
            conn.commit()
            return cursor.rowcount == 1


def unreserve_article(article_identifier: str) -> None:
    with lock:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            conn.execute("DELETE FROM PREV_ARTICLES WHERE source = ?", (article_identifier,))
            conn.commit()


def get_articles(feed_url: str):
    try:
        response = requests.get(feed_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return feedparser.parse(response.content).entries
    except requests.RequestException as exc:
        print(f"Failed to fetch RSS feed {feed_url}: {exc}")
    except Exception as exc:
        print(f"Failed to parse RSS feed {feed_url}: {exc}")
    return []


def get_articles_from_json(json_url: str):
    try:
        response = requests.get(json_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print(f"Failed to fetch JSON feed {json_url}: {exc}")
    except ValueError as exc:
        print(f"Invalid JSON from {json_url}: {exc}")
    return []


def send_to_teams(teams_card: dict) -> bool:
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(
            TEAMS_WEBHOOK_URL,
            headers=headers,
            data=json.dumps(teams_card),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.ok:
            return True
        print(f"Teams webhook error: {response.status_code} {response.text}")
    except requests.RequestException as exc:
        print(f"Failed to send to Teams: {exc}")
    return False


def article_value(article, key: str, default: str = "") -> str:
    if isinstance(article, dict):
        return article.get(key, default)
    return getattr(article, key, default)


def format_article(article, source: str, color: str) -> dict:
    raw_date = article_value(article, "published", "")
    if not raw_date:
        raw_date = article_value(article, "updated", "")
    try:
        published_date = parser.parse(raw_date).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        published_date = "Unknown date"

    title = article_value(article, "title", "Untitled")
    text = article_value(article, "summary", "") or article_value(article, "description", "")
    link = article_value(article, "link", "")

    return {
        "@context": "https://schema.org/extensions",
        "@type": "MessageCard",
        "themeColor": color,
        "title": title,
        "text": text,
        "sections": [
            {
                "facts": [
                    {"name": "Source", "value": source},
                    {"name": "Date", "value": published_date},
                ]
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "Read More",
                "targets": [{"os": "default", "uri": link}],
            }
        ],
    }


def format_json_article(article: dict, color: str) -> dict:
    try:
        published_date = parser.parse(article.get("discovered", "")).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        published_date = "Unknown date"

    return {
        "@context": "https://schema.org/extensions",
        "@type": "MessageCard",
        "themeColor": color,
        "title": "Victim: " + article.get("post_title", "Unknown"),
        "text": "New extortion case has been reported on Ransomwatch.",
        "sections": [
            {
                "facts": [
                    {"name": "Source", "value": article.get("group_name", "Ransomwatch")},
                    {"name": "Date", "value": published_date},
                ]
            }
        ],
    }


def process_feed(feed_url: str, source: str) -> None:
    articles = get_articles(feed_url)
    for article in articles:
        title = (article_value(article, "title", "") or "").lower()
        summary = (article_value(article, "summary", "") or article_value(article, "description", "")).lower()

        color = None
        if source in BLUE_SOURCES:
            color = "0000FF"
        elif any(keyword in title or keyword in summary for keyword in SECURITY_KEYWORDS):
            color = "008000"
        elif any(keyword in title or keyword in summary for keyword in EDU_KEYWORDS):
            color = "FFA500"

        if color is None:
            continue

        article_identifier = (article_value(article, "link", "") or "").strip()
        if not article_identifier:
            continue
        if not reserve_article(article_identifier):
            continue

        teams_card = format_article(article, source, color)
        if not send_to_teams(teams_card):
            unreserve_article(article_identifier)


def process_json_feed(json_articles) -> None:
    for article in json_articles:
        post_title = (article.get("post_title", "") or "").lower()
        if not any(keyword in post_title for keyword in EDU_KEYWORDS):
            continue

        article_identifier = json.dumps(
            {
                "post_title": article.get("post_title", ""),
                "discovered": article.get("discovered", ""),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        if not reserve_article(article_identifier):
            continue

        teams_card = format_json_article(article, "FFA500")
        if not send_to_teams(teams_card):
            unreserve_article(article_identifier)


def process_json_feed_url(json_url: str) -> None:
    process_json_feed(get_articles_from_json(json_url))


def main() -> None:
    initialize_db()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        try:
            while True:
                futures = [executor.submit(process_feed, feed, source) for feed, source in private_rss_feed_list]
                futures.append(executor.submit(process_json_feed_url, json_feed_url))

                for future in futures:
                    try:
                        future.result()
                    except Exception as exc:
                        print(f"Worker error: {exc}")

                time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("Shutting down bot.")


if __name__ == "__main__":
    main()
