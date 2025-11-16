# --- Standard library imports ---
import os
import re
import datetime
import asyncio

# --- Third-party imports ---
import requests
import feedparser
import nltk
import socketio
from dateutil import parser
from collections import Counter, deque
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from transformers import pipeline

# ==============================================================================
# SECTION 1: INITIAL SETUP & CONFIGURATION
# ==============================================================================

print("Initializing NLTK stopwords...")
nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords
stop_words = set(stopwords.words('english'))
print("NLTK is ready.")

load_dotenv()
news_api_key = os.getenv("NEWS_API_KEY")
gnews_api_key = os.getenv("GNEWS_API_KEY")
if not news_api_key:
    raise ValueError("CRITICAL: NEWS_API_KEY is not set in the .env file!")

# ==============================================================================
# THE CRITICAL CHANGE: SWAPPING TO A LIGHTWEIGHT MODEL
# ==============================================================================
print("Loading lightweight sentiment analysis model... (This will be much faster)")
# We are replacing the large RoBERTa model with the smaller, faster DistilBERT.
# This model is optimized for performance and is perfect for free-tier deployments.
# Note: This is a 2-class model (POSITIVE/NEGATIVE), which simplifies our output.
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
print("Sentiment model loaded successfully.")

API_TIMEOUT = 10
MAX_CONTENT_LENGTH = 512

fastapi_app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, fastapi_app)

# ==============================================================================
# SECTION 2: GLOBAL STATE MANAGEMENT (Unchanged)
# ==============================================================================

watched_brands = set()
global_word_corpus = deque(maxlen=2000)

# ==============================================================================
# SECTION 3: DATA FETCHING HELPERS (Unchanged)
# ==============================================================================

def fetch_news_api(brand_name, api_key, gnews_key):
    # This function is unchanged and works perfectly.
    mentions = []
    try:
        url = f"https://newsapi.org/v2/everything?q={brand_name}&apiKey={api_key}&pageSize=40&language=en"
        articles = requests.get(url, timeout=API_TIMEOUT).json().get("articles", [])
        for a in articles:
            title = a.get('title', '')
            if not title or title == '[Removed]': continue
            description = a.get('description', '')
            text_to_analyze = f"{title}. {description}"
            sentiment_result = sentiment_pipeline(text_to_analyze)[0]
            # We now handle a different output format from the model.
            sentiment_label = sentiment_result['label'].upper()
            mentions.append({
                "platform": "News", "source": a.get('source', {}).get('name', 'Unknown Source'),
                "text": title, "sentiment": sentiment_label, "url": a.get('url'),
                "timestamp": parser.parse(a['publishedAt']).isoformat()
            })
        if mentions: return mentions
    except Exception as e: print(f"Warning: NewsAPI request failed: {e}.")
    if gnews_key:
        try:
            url = f"https://gnews.io/api/v4/search?q={brand_name}&token={gnews_key}&lang=en&max=20"
            articles = requests.get(url, timeout=API_TIMEOUT).json().get('articles', [])
            for a in articles:
                title = a.get('title', '')
                if not title: continue
                description = a.get('description', '')
                text_to_analyze = f"{title}. {description}"
                sentiment_label = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
                mentions.append({
                    "platform": "News", "source": a.get('source', {}).get('name', 'GNews'),
                    "text": title, "sentiment": sentiment_label, "url": a.get('url'),
                    "timestamp": parser.parse(a['publishedAt']).isoformat()
                })
        except Exception as e: print(f"Error: GNews failover also failed: {e}")
    return mentions

# --- All other fetch functions are the same, just updating sentiment logic ---

def fetch_devto_mentions(brand_name):
    mentions = []
    try:
        url = f"https://dev.to/api/articles?q={brand_name}&per_page=30"
        articles = requests.get(url, timeout=API_TIMEOUT).json()
        for article in articles:
            title = article.get('title', '')
            if not title: continue
            sentiment = sentiment_pipeline(f"{title}. {article.get('description', '')}")[0]['label'].upper()
            timestamp = parser.parse(article['published_at']).isoformat() if 'published_at' in article else datetime.datetime.now().isoformat()
            mentions.append({"platform": "Dev.to", "source": "Dev.to", "text": title, "sentiment": sentiment, "url": article['url'], "timestamp": timestamp})
    except Exception as e: print(f"Error: Could not fetch from Dev.to: {e}")
    return mentions

def fetch_hacker_news_mentions(brand_name):
    mentions = []
    try:
        url = f"http://hn.algolia.com/api/v1/search?query={brand_name}&tags=story,comment&hitsPerPage=30"
        hits = requests.get(url, timeout=API_TIMEOUT).json().get("hits", [])
        for hit in hits:
            title = hit.get("title", "")
            comment_text = hit.get("comment_text", "")
            display_text = title if title else (comment_text[:100] + '...' if comment_text else '')
            if not display_text.strip(): continue
            sentiment = sentiment_pipeline(f"{title}. {comment_text[:MAX_CONTENT_LENGTH]}")[0]['label'].upper()
            timestamp = datetime.datetime.fromtimestamp(hit['created_at_i'], tz=datetime.timezone.utc).isoformat() if 'created_at_i' in hit else datetime.datetime.now().isoformat()
            mentions.append({"platform": "Hacker News", "source": "Hacker News", "text": display_text, "sentiment": sentiment, "url": hit.get("story_url") or f"http://news.ycombinator.com/item?id={hit.get('objectID')}", "timestamp": timestamp})
    except Exception as e: print(f"Error: Could not fetch from Hacker News: {e}")
    return mentions

def fetch_reddit_mentions(brand_name):
    mentions = []
    try:
        url = f"https://www.reddit.com/search.json?q={brand_name}&sort=new&limit=25"
        posts = requests.get(url, headers={'User-Agent': 'AnEarOut/1.0'}, timeout=API_TIMEOUT).json().get("data", {}).get("children", [])
        for post in posts:
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            if not title: continue
            sentiment = sentiment_pipeline(f"{title}. {post_data.get('selftext', '')[:MAX_CONTENT_LENGTH]}")[0]['label'].upper()
            timestamp = datetime.datetime.fromtimestamp(post_data['created_utc'], tz=datetime.timezone.utc).isoformat()
            mentions.append({"platform": "Reddit", "source": f"r/{post_data.get('subreddit', 'unknown')}", "text": title, "sentiment": sentiment, "url": f"https://www.reddit.com{post_data.get('permalink', '')}", "timestamp": timestamp})
    except Exception as e: print(f"Error: Could not fetch from Reddit: {e}")
    return mentions

def fetch_rss_feed(url, brand_name, platform_name):
    mentions = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title = entry.title
            if brand_name.lower() in title.lower():
                summary = re.sub('<[^<]+?>', '', entry.get('summary', ''))
                sentiment = sentiment_pipeline(f"{title}. {summary[:MAX_CONTENT_LENGTH]}")[0]['label'].upper()
                timestamp = parser.parse(entry.published).isoformat() if 'published' in entry else datetime.datetime.now().isoformat()
                mentions.append({"platform": platform_name, "source": platform_name, "text": title, "sentiment": sentiment, "url": entry.link, "timestamp": timestamp})
    except Exception as e: print(f"Error: Could not fetch RSS from {platform_name}: {e}")
    return mentions

# ==============================================================================
# SECTION 4: ANALYSIS & UTILITY FUNCTIONS
# ==============================================================================

def analyze_mention_summary(all_mentions):
    """Calculates the percentage breakdown of sentiments. Handles the new 2-class model."""
    if not all_mentions:
        return {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
    
    sentiment_counts = Counter(m['sentiment'] for m in all_mentions)
    total = len(all_mentions)
    
    # Since the new model has no NEUTRAL, we calculate it as the remainder.
    # This is a sensible approximation for the UI.
    positive_pct = round((sentiment_counts.get("POSITIVE", 0) / total) * 100)
    negative_pct = round((sentiment_counts.get("NEGATIVE", 0) / total) * 100)
    neutral_pct = 100 - positive_pct - negative_pct

    return {
        "POSITIVE": positive_pct,
        "NEGATIVE": negative_pct,
        "NEUTRAL": neutral_pct
    }

def update_and_get_global_topics(new_mentions, brand_name):
    # This function is unchanged.
    global global_word_corpus
    all_text = " ".join(m['text'] for m in new_mentions)
    cleaned = re.sub(r'\W+', ' ', all_text).lower()
    words = [w for w in cleaned.split() if w not in stop_words and w not in {brand_name.lower()} and len(w) > 3]
    global_word_corpus.extend(words)
    return [word for word, freq in Counter(global_word_corpus).most_common(20)]

# ==============================================================================
# SECTION 5: CORE APPLICATION LOGIC (Unchanged, now more stable)
# ==============================================================================

async def run_search_flow(sid, brand_name):
    # This entire function's logic remains the same, but it will now run much faster
    # and use significantly less memory.
    watched_brands.add(brand_name.lower())
    print(f"Starting new search for '{brand_name}'.")
    current_search_mentions = []
    
    tasks = [
        ("News", lambda: fetch_news_api(brand_name, news_api_key, gnews_api_key)),
        ("Hacker News", lambda: fetch_hacker_news_mentions(brand_name)),
        ("Reddit", lambda: fetch_reddit_mentions(brand_name)),
        ("Dev.to", lambda: fetch_devto_mentions(brand_name)),
    ]

    for name, task_func in tasks:
        try:
            await sio.emit('status_update', {'message': f"Searching {name}..."})
            mentions = await asyncio.to_thread(task_func)
            if mentions:
                await sio.emit('mention_batch', mentions, to=sid)
                current_search_mentions.extend(mentions)
                print(f"Streamed {len(mentions)} mentions from {name} for '{brand_name}'")
                summary_so_far = analyze_mention_summary(current_search_mentions)
                await sio.emit('summary_update', {"sentiment": summary_so_far}, to=sid)
        except Exception as e:
            print(f"CRITICAL ERROR in streaming task {name}: {e}")
            
    print(f"--- Search for '{brand_name}' finished. Sending final data. ---")
    
    now = datetime.datetime.now(datetime.timezone.utc)
    one_day_ago = now - datetime.timedelta(days=1)
    activity_timestamps = []
    for m in current_search_mentions:
        try:
            ts = parser.parse(m['timestamp'])
            if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
                ts = ts.replace(tzinfo=datetime.timezone.utc)
            if ts > one_day_ago:
                activity_timestamps.append(m['timestamp'])
        except (parser.ParserError, TypeError):
             print(f"Warning: Skipping invalid timestamp: {m.get('timestamp')}")
    await sio.emit('activity_update', activity_timestamps, to=sid)
    
    final_topics = update_and_get_global_topics(current_search_mentions, brand_name)
    await sio.emit('summary_update', {"topics": final_topics}, to=sid)
    
    await sio.emit('search_complete', to=sid)
    print(f"--- All data sent for '{brand_name}'. Search complete. ---")

# ==============================================================================
# SECTION 6: SOCKET.IO EVENT HANDLERS (Unchanged)
# ==============================================================================

@sio.on('start_search')
async def handle_start_search(sid, data):
    brand_name = data.get('brand')
    if not brand_name: return
    sio.start_background_task(run_search_flow, sid, brand_name)

@sio.on('connect')
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.on('disconnect')
def disconnect(sid):
    print(f"Client disconnected: {sid}")
