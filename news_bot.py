# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json
import os
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
    """Dùng Google News RSS để lấy headlines miễn phí."""
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=vi&gl=VN&ceid=VN:vi"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"RSS error: {e}")
        return ""

def parse_titles(xml, limit=5):
    """Trích title từ RSS XML thô."""
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
    """Gọi Gemini API (miễn phí) để tóm tắt & chọn insight."""
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y")
    prompt = f"""Dưới đây là các headline tin tức hôm nay ({today}) về AI, công nghệ, mobile dev, Flutter, iOS, Android, startup Việt Nam, business tech:

{headlines_text}

Hãy:
1. Chọn 4-5 tin đáng chú ý nhất, ưu tiên tin mới và có tác động thực tế.
2. Viết thành báo cáo ngắn gọn bằng tiếng Việt, dễ đọc trên điện thoại.
3. Format đúng như sau (dùng emoji, xuống dòng rõ ràng):

📰 BÁO CÁO NGÀY — {today}
🤖 AI · TECH · MOBILE · STARTUP
━━━━━━━━━━━━━━━━━━━━

1️⃣ [Tiêu đề ngắn]
[2-3 câu tóm tắt, nêu rõ tại sao quan trọng với dev/tech người Việt]

2️⃣ ...

━━━━━━━━━━━━━━━━━━━━
🔗 Tổng hợp tự động · Gemini AI

Chỉ trả về nội dung báo cáo, không giải thích thêm."""

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())
    return result["candidates"][0]["content"]["parts"][0]["text"]

def send_telegram(text):
    """Gửi message qua Telegram Bot API."""
    body = json.dumps({"chat_id": CHAT_ID, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read())
    return result.get("ok", False)

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    print("📡 Đang lấy tin tức...")
    all_titles = []
    for topic in TOPICS:
        xml = fetch_rss(topic)
        titles = parse_titles(xml, limit=5)
        all_titles.extend(titles)
        print(f"  ✓ {topic[:30]}... → {len(titles)} headlines")

    if not all_titles:
        print("❌ Không lấy được tin tức.")
        return

    headlines_text = "\n".join(f"- {t}" for t in all_titles)
    print(f"\n📝 Tổng {len(all_titles)} headlines, đang tóm tắt bằng Gemini...")

    report = ask_gemini(headlines_text)
    print("\n--- BÁO CÁO ---")
    print(report)
    print("---------------\n")

    print("📨 Đang gửi Telegram...")
    ok = send_telegram(report)
    if ok:
        print("✅ Gửi thành công!")
    else:
        print("❌ Gửi thất bại.")

if __name__ == "__main__":
    main()
