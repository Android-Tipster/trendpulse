import streamlit as st
import requests
import re
import time
from datetime import datetime, timezone, timedelta
from collections import Counter

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="TrendPulse — TikTok Pre-Trend Radar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 900px; }
    .signal-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .badge-breaking { background: #ef4444; color: white; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    .badge-hot      { background: #f97316; color: white; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    .badge-rising   { background: #eab308; color: white; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    .badge-watch    { background: #3b82f6; color: white; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    .velocity-big { font-size: 2rem; font-weight: 800; color: #111; line-height: 1; }
    .velocity-label { font-size: 12px; color: #9ca3af; margin-top: 2px; }
    .kw-pill {
        display: inline-block;
        background: #f3f4f6;
        color: #374151;
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 12px;
        margin: 2px;
    }
    .thread-link { font-size: 13px; color: #6b7280; }
    .window-bar {
        background: #fefce8;
        border: 1px solid #fde68a;
        border-radius: 8px;
        padding: 0.7rem 1rem;
        margin-bottom: 1.5rem;
        font-size: 14px;
        color: #92400e;
    }
    h1 { font-size: 1.9rem !important; font-weight: 800 !important; letter-spacing: -0.5px !important; }
    .subhead { font-size: 15px; color: #6b7280; margin-top: -0.5rem; margin-bottom: 1.5rem; }
    .how-to { background: #f9fafb; border-radius: 8px; padding: 1rem 1.2rem; font-size: 13px; color: #4b5563; }
    .stButton > button {
        background: #111 !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        width: 100%;
    }
    .stButton > button:hover { background: #374151 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

REDDIT_HEADERS = {"User-Agent": "TrendPulse/1.0 tiktok-pre-trend-radar"}

NICHE_SUBREDDITS = {
    "Beauty & Skincare": ["SkincareAddiction", "MakeupAddiction", "beauty", "NailArt", "HairDye", "30PlusSkinCare"],
    "Fitness & Gym": ["fitness", "bodyweightfitness", "xxfitness", "loseit", "WeightLossSupport", "gym"],
    "Food & Cooking": ["food", "recipes", "Cooking", "MealPrepSunday", "EatCheapAndHealthy", "Baking"],
    "Personal Finance": ["personalfinance", "financialindependence", "investing", "Frugal", "povertyfinance"],
    "Fashion & Style": ["femalefashionadvice", "malefashionadvice", "streetwear", "ThriftStoreHauls", "OUTFITS"],
    "Tech & AI": ["technology", "gadgets", "artificial", "ChatGPT", "singularity", "Futurology"],
    "Relationships": ["AmItheAsshole", "relationship_advice", "dating_advice", "Marriage"],
    "Mental Health": ["mentalhealth", "Anxiety", "depression", "selfimprovement", "getdisciplined"],
    "Business & Side Hustles": ["Entrepreneur", "smallbusiness", "startups", "SideProject", "passive_income"],
    "Pets": ["dogs", "cats", "aww", "puppy101", "Pets"],
    "Travel": ["travel", "solotravel", "shoestring", "backpacking", "digitalnomad"],
    "Pop Culture": ["popculturechat", "entertainment", "television", "movies", "Oscars"],
    "Parenting": ["Parenting", "NewParents", "beyondthebump", "Mommit", "daddit"],
    "Gaming": ["gaming", "Games", "pcgaming", "indiegaming"],
    "DIY & Home": ["DIY", "HomeImprovement", "InteriorDesign", "malelivingspace"],
}

STOP_WORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with","by","from",
    "is","are","was","were","be","been","have","has","had","do","does","did","will",
    "would","could","should","may","might","shall","can","i","my","me","we","our",
    "you","your","he","she","it","its","they","their","this","that","these","those",
    "what","how","why","when","where","who","which","not","no","so","if","as","just",
    "about","up","out","get","got","like","need","want","use","used","using","make",
    "made","new","one","two","any","all","more","much","very","also","really","know",
    "think","feel","look","good","great","best","first","last","after","before","now",
    "still","already","ever","never","always","today","yesterday","week","month","year",
    "am","im","ive","dont","doesnt","didnt","cant","wont","thats","heres","whats",
    "anyone","someone","thing","things","people","time","way","day","days","going",
    "help","tried","trying","started","nothing","something","than","then","there",
    "here","some","been","only","even","into","over","such","both","each","most",
    "other","same","too","because","while","during","since","without","between",
    "through","against","being","having","doing","show","post","posts","thread",
    "comment","comments","reddit","question","asking","asked","tell","told","said",
    "says","saying","everyone","somebody","anybody","everything","many","few","less",
    "least","long","short","high","low","old","young","big","small","right","left",
    "back","front","side","top","bottom","every","another","however","although",
    "though","whether","either","neither","yet","once","twice","again","actually",
}

# ---------------------------------------------------------------------------
# Engine (same core as trendpulse.py, self-contained)
# ---------------------------------------------------------------------------

def fetch_subreddit(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100"
    try:
        resp = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
        if resp.status_code == 429:
            time.sleep(2)
            resp = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        return resp.json().get("data", {}).get("children", [])
    except Exception:
        return []


def calculate_velocity(posts, window_hours=3):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)
    day_start = now - timedelta(hours=24)
    recent, day_count = [], 0
    for post in posts:
        d = post.get("data", {})
        created = datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc)
        if created >= day_start:
            day_count += 1
        if created >= window_start:
            recent.append({
                "title": d.get("title", ""),
                "score": d.get("score", 1),
                "comments": d.get("num_comments", 0),
                "url": f"https://reddit.com{d.get('permalink', '')}",
            })
    expected = max(1, day_count * (window_hours / 24))
    return {
        "velocity_ratio": round(len(recent) / expected, 2),
        "recent": len(recent),
        "day": day_count,
        "hot": sorted(recent, key=lambda x: x["comments"] + x["score"], reverse=True)[:4],
    }


def extract_keywords(titles, top_n=10):
    words, phrases = [], []
    for title in titles:
        cleaned = re.sub(r"[^a-zA-Z0-9\s'-]", " ", title.lower())
        tokens = [t.strip("'-") for t in cleaned.split()
                  if len(t.strip("'-")) >= 4 and t.strip("'-") not in STOP_WORDS and not t.strip("'-").isdigit()]
        words.extend(tokens)
        for i in range(len(tokens) - 1):
            phrases.append(f"{tokens[i]} {tokens[i+1]}")

    combined = dict(Counter(words).most_common(top_n * 2))
    for ph, cnt in Counter(phrases).most_common(top_n):
        if cnt >= 2:
            combined[ph] = cnt * 1.4
    return sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_n]


def scan(selected_niches, progress_cb=None):
    results = []
    total = len(selected_niches)
    for idx, niche in enumerate(selected_niches):
        if progress_cb:
            progress_cb(idx / total, f"Scanning {niche}...")
        subs = NICHE_SUBREDDITS[niche]
        all_titles, velocities, hot_posts = [], [], []
        for sub in subs:
            posts = fetch_subreddit(sub)
            if not posts:
                continue
            stats = calculate_velocity(posts)
            velocities.append(stats["velocity_ratio"])
            all_titles.extend([p["title"] for p in stats["hot"]])
            hot_posts.extend(stats["hot"])
            time.sleep(0.4)
        if not velocities:
            continue
        max_v = max(velocities)
        avg_v = sum(velocities) / len(velocities)
        keywords = extract_keywords(all_titles)
        top_posts = sorted(hot_posts, key=lambda x: x["comments"] + x["score"], reverse=True)[:3]
        engagement = sum(p["comments"] + p["score"] for p in top_posts[:3]) / max(1, len(top_posts[:3]))
        score = round(max_v * 0.5 + avg_v * 0.3 + min(1.0, engagement / 200) * 0.2, 3)
        results.append({
            "niche": niche,
            "score": score,
            "velocity": round(max_v, 2),
            "keywords": keywords[:6],
            "posts": top_posts[:3],
        })
    if progress_cb:
        progress_cb(1.0, "Done.")
    return sorted(results, key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.markdown("# 📡 TrendPulse")
st.markdown('<p class="subhead">Spot TikTok trends 6-12 hours before they hit the FYP — based on Reddit velocity signals</p>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("**Select your niches** (pick 1-5 that match your content)")
    all_niches = list(NICHE_SUBREDDITS.keys())

    # Default selections
    defaults = ["Relationships", "Mental Health", "Business & Side Hustles", "Tech & AI", "Pop Culture"]
    selected = st.multiselect(
        label="Niches",
        options=all_niches,
        default=defaults,
        label_visibility="collapsed",
    )

with col2:
    st.markdown("&nbsp;", unsafe_allow_html=True)
    st.markdown("&nbsp;", unsafe_allow_html=True)
    run_btn = st.button("Run Scan", use_container_width=True)

st.markdown("---")

if run_btn:
    if not selected:
        st.warning("Pick at least one niche.")
        st.stop()

    now = datetime.now(timezone.utc)
    post_by = now + timedelta(hours=18)
    st.markdown(
        f'<div class="window-bar">⏱ <strong>Action window:</strong> Post by <strong>{post_by.strftime("%H:%M UTC")}</strong> to catch the FYP boost before saturation. Signals refresh every 3-6 hours.</div>',
        unsafe_allow_html=True,
    )

    progress = st.progress(0, text="Starting scan...")
    signals = scan(selected, progress_cb=lambda v, t: progress.progress(v, text=t))
    progress.empty()

    if not signals:
        st.info("No velocity signals detected in this window. Try again in 2-3 hours.")
        st.stop()

    st.markdown(f"### {len(signals)} signals found across {len(selected)} niches")
    st.caption(f"Scanned at {now.strftime('%H:%M UTC')} — monitoring {sum(len(NICHE_SUBREDDITS[n]) for n in selected)} subreddits")

    for sig in signals:
        v = sig["velocity"]
        if v >= 2.5:
            badge = '<span class="badge-breaking">BREAKING</span>'
            note = f"{v}x normal activity in last 3 hours"
        elif v >= 1.8:
            badge = '<span class="badge-hot">HOT</span>'
            note = f"{v}x normal activity — building fast"
        elif v >= 1.3:
            badge = '<span class="badge-rising">RISING</span>'
            note = f"{v}x normal activity — early momentum"
        else:
            badge = '<span class="badge-watch">WATCH</span>'
            note = f"{v}x — mild uptick, monitor"

        kw_pills = "".join([f'<span class="kw-pill">{kw}</span>' for kw, _ in sig["keywords"]])

        posts_html = ""
        for p in sig["posts"][:2]:
            title = p["title"][:90] + ("..." if len(p["title"]) > 90 else "")
            posts_html += f'<div class="thread-link" style="margin-top:6px;">↗ <a href="{p["url"]}" target="_blank" style="color:#6b7280;text-decoration:none;">{title}</a> <span style="color:#d1d5db;font-size:11px;">({p["comments"]} comments · {p["score"]} upvotes)</span></div>'

        st.markdown(f"""
        <div class="signal-card">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                {badge}
                <span style="font-size:17px;font-weight:700;color:#111;">{sig['niche']}</span>
                <span style="margin-left:auto;font-size:12px;color:#9ca3af;">{note}</span>
            </div>
            <div style="margin-bottom:10px;">{kw_pills}</div>
            {posts_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div class="how-to">
    <strong>How to use these signals:</strong><br>
    1. Pick the signal that matches your niche<br>
    2. Make a 30-60 second video reacting to or answering the trending conversation<br>
    3. Use the keyword pills verbatim in your caption and first spoken sentence — that's your hook<br>
    4. Post within the action window above for maximum FYP distribution before saturation
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="background:#f9fafb;border-radius:10px;padding:2rem;text-align:center;color:#6b7280;">
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">📡</div>
        <div style="font-size:16px;font-weight:600;color:#374151;margin-bottom:0.5rem;">Ready to scan</div>
        <div style="font-size:14px;">Select your niches above and hit <strong>Run Scan</strong> to see what's gaining velocity right now on Reddit — before it hits TikTok.</div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    '<p style="font-size:12px;color:#d1d5db;text-align:center;">TrendPulse monitors Reddit velocity signals across 15 creator niches. '
    'Data refreshes every run. Not affiliated with TikTok or Reddit.</p>',
    unsafe_allow_html=True,
)
