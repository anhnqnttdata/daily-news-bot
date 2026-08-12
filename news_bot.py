# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")
GEMINI_KEY     = os.environ.get("GEMINI_KEY", "")

# ── Hacker News ───────────────────────────────────────────────────────────
def fetch_hackernews(limit=40):
    print("  [HackerNews] Dang lay top stories...")
    try:
        with urllib.request.urlopen("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10) as r:
            ids = json.loads(r.read())[:limit]
        titles = []
        for sid in ids:
            try:
                with urllib.request.urlopen(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5) as r:
                    item = json.loads(r.read())
                if item and item.get("score", 0) >= 50:
                    titles.append(f"[HackerNews] {item.get('title','')} [score:{item.get('score',0)}]")
            except:
                continue
        print(f"  [HackerNews] {len(titles)} stories")
        return titles
    except Exception as e:
        print(f"  [HackerNews] Error: {e}")
        return []

# ── Reddit ────────────────────────────────────────────────────────────────
SUBREDDITS = ["MachineLearning", "artificial", "programming", "FlutterDev", "iOSProgramming", "androiddev", "startups"]

def fetch_reddit(subreddit, limit=5):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "daily-news-bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        posts = []
        for p in data["data"]["children"]:
            d = p["data"]
            if not d.get("stickied"):
                posts.append(f"[Reddit r/{subreddit}] {d['title']} [upvotes:{d['score']}]")
        return posts
    except Exception as e:
        print(f"  [Reddit r/{subreddit}] Error: {e}")
        return []

def fetch_all_reddit():
    print("  [Reddit] Dang lay hot posts...")
    all_posts = []
    for sub in SUBREDDITS:
        posts = fetch_reddit(sub, limit=5)
        all_posts.extend(posts)
        print(f"  [Reddit r/{sub}] {len(posts)} posts")
    return all_posts

# ── Google News ───────────────────────────────────────────────────────────
VN_TOPICS = ["Vietnam technology startup 2026", "cong nghe Viet Nam 2026"]

def fetch_rss(query):
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  [GoogleNews] Error: {e}")
        return ""

def parse_titles(xml, limit=5):
    import re
    items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
    titles = []
    for item in items[:limit]:
        m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item)
        if not m:
            m = re.search(r"<title>(.*?)</title>", item)
        if m:
            titles.append(m.group(1).strip())
    return titles

def fetch_google_news():
    print("  [GoogleNews] Dang lay tin Viet Nam...")
    all_titles = []
    for topic in VN_TOPICS:
        xml = fetch_rss(topic)
        titles = parse_titles(xml, limit=5)
        all_titles.extend(titles)
        print(f"  [GoogleNews] '{topic[:30]}' -> {len(titles)} headlines")
    return [f"[VN News] {t}" for t in all_titles]

# ── Gemini ────────────────────────────────────────────────────────────────
def ask_gemini(headlines_text, today):
    prompt = "\n".join([
        "You are a Vietnamese tech news curator.",
        "Below are today's trending stories (" + today + ") from HackerNews, Reddit, and Vietnam News.",
        "",
        headlines_text,
        "",
        "TASK: Write a daily tech report in Vietnamese with EXACTLY 10 stories.",
        "- Prioritize stories with highest score/upvotes.",
        "- Prefer topics: AI, coding, mobile dev (Flutter/iOS/Android), Vietnam tech, startups.",
        "- Each story: title in Vietnamese + 3 full sentences in Vietnamese explaining content and why it matters.",
        "- Mention the source (HackerNews / Reddit / VN News).",
        "",
        "FORMAT (follow exactly):",
        "BAO CAO NGAY - " + today,
        "HACKERNEWS x REDDIT x VN NEWS",
        "====================",
        "",
        "1. [Ten tin bang tieng Viet] (HackerNews)",
        "[Cau 1. Cau 2. Cau 3.]",
        "",
        "2. [Ten tin] (Reddit)",
        "[Cau 1. Cau 2. Cau 3.]",
        "",
        "... (continue until story 10)",
        "",
        "====================",
        "Tong hop tu dong - HN x Reddit x GNews",
        "",
        "RULES:",
        "- You MUST write stories numbered 1 through 10. All 10. No exceptions.",
        "- Each story must have 3 complete Vietnamese sentences.",
        "- Do NOT write placeholders like '...' or stop before story 10.",
        "- Use proper Vietnamese with full diacritics.",
    ])

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.5}
    }).encode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_KEY}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        print(f"  Gemini HTTP error {e.code}: {e.read().decode()}")
        raise
    except Exception as e:
        print(f"  Gemini error: {e}")
        raise

# ── Telegram ──────────────────────────────────────────────────────────────
def send_telegram(text):
    MAX = 4000
    chunks = []
    while text:
        if len(text) <= MAX:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, MAX)
        if split_at == -1:
            split_at = MAX
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    print(f"  Chia thanh {len(chunks)} phan...")
    ok = True
    for i, chunk in enumerate(chunks):
        body = json.dumps({"chat_id": CHAT_ID, "text": chunk}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                result = json.loads(r.read())
            print(f"  Phan {i+1}/{len(chunks)}: {'OK' if result.get('ok') else 'FAIL'}")
            if not result.get("ok"):
                ok = False
        except urllib.error.HTTPError as e:
            print(f"  Telegram error {e.code}: {e.read().decode()}")
            ok = False
    return ok

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print("Kiem tra config...")
    if not TELEGRAM_TOKEN: print("TELEGRAM_TOKEN chua set!"); sys.exit(1)
    if not CHAT_ID:        print("CHAT_ID chua set!");        sys.exit(1)
    if not GEMINI_KEY:     print("GEMINI_KEY chua set!");     sys.exit(1)
    print(f"  OK TOKEN ...{TELEGRAM_TOKEN[-6:]}")
    print(f"  OK CHAT_ID {CHAT_ID}")
    print(f"  OK GEMINI ...{GEMINI_KEY[-6:]}")

    print("\nDang thu thap tin tuc...")
    hn      = fetch_hackernews(limit=40)
    reddit  = fetch_all_reddit()
    gn      = fetch_google_news()

    all_titles = hn + reddit + gn
    seen, unique = set(), []
    for t in all_titles:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    print(f"\nTong: {len(unique)} stories (HN:{len(hn)} Reddit:{len(reddit)} GNews:{len(gn)})")
    if not unique:
        print("Khong lay duoc tin tuc!"); sys.exit(1)

    today = datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y")
    headlines_text = "\n".join(f"- {t}" for t in unique)

    print("\nDang tom tat bang Gemini...")
    report = ask_gemini(headlines_text, today)

    print(f"\n--- BAO CAO ({len(report)} ky tu) ---")
    print(report)
    print("---------------\n")

    print("Dang gui Telegram...")
    ok = send_telegram(report)
    if ok:
        print("Gui thanh cong!")
    else:
        print("Gui that bai!"); sys.exit(1)

if __name__ == "__main__":
    main()
