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

TOPICS = [
    "AI artificial intelligence agent LLM 2026",
    "Flutter iOS Android mobile development 2026",
    "software engineering coding tools 2026",
    "Vietnam technology startup 2026",
    "business tech startup funding 2026",
]

def fetch_rss(query):
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  RSS error: {e}")
        return ""

def parse_titles(xml, limit=6):
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

def ask_gemini(headlines_text):
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y")
    prompt = (
        "You are a Vietnamese tech news summarizer. "
        "Below are today's headlines (" + today + ") about AI, tech, mobile dev, Flutter, iOS, Android, Vietnam startup.\n\n"
        + headlines_text +
        "\n\nInstructions:\n"
        "1. Pick EXACTLY 5 of the most important stories.\n"
        "2. Write a daily report IN VIETNAMESE with full diacritics, easy to read on mobile.\n"
        "3. Use exactly this format:\n\n"
        "BAO CAO NGAY - " + today + "\n"
        "AI - TECH - MOBILE - STARTUP\n"
        "====================\n\n"
        "1. [Tieu de bang tieng Viet]\n"
        "[Viet 3 cau day du bang tieng Viet co dau ve noi dung va ly do quan trong]\n\n"
        "2. [Tieu de]\n"
        "[3 cau]\n\n"
        "3. [Tieu de]\n"
        "[3 cau]\n\n"
        "4. [Tieu de]\n"
        "[3 cau]\n\n"
        "5. [Tieu de]\n"
        "[3 cau]\n\n"
        "====================\n"
        "Tong hop tu dong - Gemini AI\n\n"
        "CRITICAL: You MUST write all 5 stories completely. Each summary must be 3 full sentences in Vietnamese. "
        "Do not stop early. Do not truncate any story."
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

def send_telegram(text):
    """Chia nho neu bao cao qua 4000 ky tu (gioi han Telegram)."""
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

    print(f"  Chia thanh {len(chunks)} phan de gui...")
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
            if result.get("ok"):
                print(f"  Phan {i+1}/{len(chunks)} gui OK")
            else:
                print(f"  Phan {i+1} that bai: {result}")
                ok = False
        except urllib.error.HTTPError as e:
            print(f"  Telegram HTTP error {e.code}: {e.read().decode()}")
            ok = False
    return ok

def main():
    print("Kiem tra config...")
    if not TELEGRAM_TOKEN: print("TELEGRAM_TOKEN chua set!"); sys.exit(1)
    if not CHAT_ID:        print("CHAT_ID chua set!");        sys.exit(1)
    if not GEMINI_KEY:     print("GEMINI_KEY chua set!");     sys.exit(1)
    print(f"  OK TOKEN ...{TELEGRAM_TOKEN[-6:]}")
    print(f"  OK CHAT_ID {CHAT_ID}")
    print(f"  OK GEMINI ...{GEMINI_KEY[-6:]}")

    print("\nDang lay tin tuc...")
    all_titles = []
    for topic in TOPICS:
        xml = fetch_rss(topic)
        titles = parse_titles(xml, limit=6)
        all_titles.extend(titles)
        print(f"  {topic[:40]} -> {len(titles)} headlines")

    if not all_titles:
        print("Khong lay duoc tin tuc!"); sys.exit(1)

    seen, unique = set(), []
    for t in all_titles:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    headlines_text = "\n".join(f"- {t}" for t in unique)
    print(f"\nTong {len(unique)} headlines, dang tom tat...")

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
