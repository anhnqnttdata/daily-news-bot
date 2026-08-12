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
def fetch_hackernews(limit=30):
    """Lấy top stories từ Hacker News (API public, miễn phí)."""
    print("  [HackerNews] Dang lay top stories...")
    try:
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        with urllib.request.urlopen(url, timeout=10) as r:
            ids = json.loads(r.read())[:limit]

        titles = []
        for story_id in ids:
            try:
                url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                with urllib.request.urlopen(url, timeout=5) as r:
                    item = json.loads(r.read())
                if item and item.get("score", 0) >= 50:
                    title = item.get("title", "")
                    score = item.get("score", 0)
                    titles.append(f"{title} [score: {score}]")
            except:
                continue

        print(f"  [HackerNews] {len(titles)} stories (score >= 50)")
        return titles
    except Exception as e:
        print(f"  [HackerNews] Error: {e}")
        return []

# ── Reddit ────────────────────────────────────────────────────────────────
SUBREDDITS = [
    "MachineLearning",
    "artificial",
    "programming",
    "FlutterDev",
    "iOSProgramming",
    "androiddev",
    "startups",
]

def fetch_reddit(subreddit, limit=5):
    """Lấy hot posts từ subreddit (không cần API key)."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "daily-news-bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        posts = data["data"]["children"]
        titles = []
        for p in posts:
            d = p["data"]
            if not d.get("stickied"):
                titles.append(f"[r/{subreddit}] {d['title']} [upvotes: {d['score']}]")
        return titles
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

# ── Google News (tin Viet Nam) ────────────────────────────────────────────
VN_TOPICS = [
    "Vietnam technology startup 2026",
    "cong nghe Viet Nam 2026",
]

def fetch_rss(query):
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  [GoogleNews] RSS error: {e}")
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
    return all_titles

# ── Gemini ────────────────────────────────────────────────────────────────
def ask_gemini(headlines_text):
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y")
    prompt = (
        "You are a Vietnamese tech news curator. "
        "Below are today's trending stories from Hacker News (with score), Reddit (with upvotes), and Google News Vietnam (" + today + ").\n\n"
        + headlines_text +
        "\n\nInstructions:\n"
        "1. Pick EXACTLY 10 stories with the highest community interest (prioritize high score/upvotes).\n"
        "2. Prefer stories relevant to: AI, coding tools, mobile dev (Flutter/iOS/Android), Vietnam tech, startups.\n"
        "3. Write a daily report IN VIETNAMESE with full diacritics, easy to read on mobile.\n"
        "4. Mention the source (HackerNews / Reddit / VN News) for each story.\n"
        "5. Use exactly this format:\n\n"
        "BAO CAO NGAY - " + today + "\n"
        "HACKERNEWS x REDDIT x VN NEWS\n"
        "====================\n\n"
        "1. [Tieu de bang tieng Viet] (nguon: HackerNews/Reddit/VN News)\n"
        "[3 cau tom tat bang tieng Viet co dau: noi dung chinh, ly do cong dong quan tam, anh huong voi dev Viet Nam]\n\n"
        "2. ...\n3. ...\n4. ...\n5. ...\n\n"
        "====================\n"
        "Tong hop tu dong - HN x Reddit x GNews\n\n"
        "CRITICAL: Write ALL 10 stories completely with 3 full Vietnamese sentences each. Do not stop early."
    )

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.5}
    }).encode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_KEY}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
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

    print("\nDang thu thap tin tuc tu 3 nguon...")
    hn_titles     = fetch_hackernews(limit=30)
    reddit_titles = fetch_all_reddit()
    gn_titles     = fetch_google_news()

    all_titles = hn_titles + reddit_titles + gn_titles

    # Dedup
    seen, unique = set(), []
    for t in all_titles:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    print(f"\nTong cong: {len(unique)} stories (HN:{len(hn_titles)} Reddit:{len(reddit_titles)} GNews:{len(gn_titles)})")

    if not unique:
        print("Khong lay duoc tin tuc!"); sys.exit(1)

    headlines_text = "\n".join(f"- {t}" for t in unique)
    print("\nDang tom tat bang Gemini...")
    report = ask_gemini(headlines_text)

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
