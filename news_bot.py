# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ── Config ──────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")
GEMINI_KEY     = os.environ.get("GEMINI_KEY", "")

TOPICS = [
    "AI artificial intelligence agent LLM",
    "Flutter iOS Android mobile development",
    "software engineering coding tools 2026",
    "Vietnam technology startup",
    "business tech startup funding",
]

# ── Helpers ──────────────────────────────────────────────────────────────
def fetch_rss(query):
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=vi&gl=VN&ceid=VN:vi"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  ⚠ RSS error [{query[:20]}]: {e}")
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

def ask_gemini(headlines_text):
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y")
    prompt = f"""Duoi day la cac headline tin tuc hom nay ({today}) ve AI, cong nghe, mobile dev, Flutter, iOS, Android, startup Viet Nam:

{headlines_text}

Hay chon 4-5 tin dang chu y nhat va viet thanh bao cao ngan gon bang tieng Viet co dau, de doc tren dien thoai.
Format:

BAO CAO NGAY - {today}
AI - TECH - MOBILE - STARTUP
====================

1. [Tieu de ngan]
[2-3 cau tom tat, neu ro tai sao quan trong voi dev nguoi Viet]

2. ...

====================
Tong hop tu dong - Gemini AI

Chi tra ve noi dung bao cao, khong giai thich them."""

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1000}
    }).encode("utf-8")

    # Dùng gemini-2.0-flash — model mới nhất, miễn phí
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"  Gemini HTTP error {e.code}: {err_body}")
        raise
    except Exception as e:
        print(f"  Gemini error: {e}")
        raise

def send_telegram(text):
    body = json.dumps({"chat_id": CHAT_ID, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
        return result.get("ok", False)
    except urllib.error.HTTPError as e:
        print(f"  Telegram HTTP error {e.code}: {e.read().decode()}")
        return False

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    print("Kiem tra config...")
    if not TELEGRAM_TOKEN: print("TELEGRAM_TOKEN chua set!"); sys.exit(1)
    if not CHAT_ID:        print("CHAT_ID chua set!");        sys.exit(1)
    if not GEMINI_KEY:     print("GEMINI_KEY chua set!");     sys.exit(1)
    print(f"  OK TELEGRAM_TOKEN: ...{TELEGRAM_TOKEN[-6:]}")
    print(f"  OK CHAT_ID: {CHAT_ID}")
    print(f"  OK GEMINI_KEY: ...{GEMINI_KEY[-6:]}")

    print("\nDang lay tin tuc...")
    all_titles = []
    for topic in TOPICS:
        xml = fetch_rss(topic)
        titles = parse_titles(xml, limit=5)
        all_titles.extend(titles)
        print(f"  {topic[:35]} -> {len(titles)} headlines")

    if not all_titles:
        print("Khong lay duoc tin tuc nao!"); sys.exit(1)

    headlines_text = "\n".join(f"- {t}" for t in all_titles)
    print(f"\nTong {len(all_titles)} headlines, dang tom tat bang Gemini 2.0 Flash...")

    report = ask_gemini(headlines_text)
    print("\n--- BAO CAO ---")
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
