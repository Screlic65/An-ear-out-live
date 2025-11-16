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

print("Loading lightweight sentiment analysis model...")
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
print("Sentiment model loaded successfully.")

API_TIMEOUT = 10
MAX_CONTENT_LENGTH = 512

fastapi_app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, fastapi_app)

# ==============================================================================
# SECTION 2: GLOBAL STATE MANAGEMENT
# ==============================================================================

watched_brands = set()
global_word_corpus = deque(maxlen=2000)

# ==============================================================================
# SECTION 3: DATA FETCHING HELPERS (OPTIMIZED FOR BATCHING & 15 POSTS)
# ==============================================================================

def process_sentiments_in_batch(items, text_extractor):
    """A helper to run sentiment analysis on a batch of items for max efficiency."""
    texts_to_analyze = [text_extractor(item) for item in items]
    if not texts_to_analyze:
        return []
    # This single call is much faster than many individual calls.
    return sentiment_pipeline(texts_to_analyze)

def fetch_news_api(brand_name, api_key, gnews_key):
    """Fetches news with failover, now with batch sentiment analysis."""
    all_articles = []
    try:
        # MODIFIED: Reduced pageSize to 15
        url = f"https://newsapi.org/v2/everything?q={brand_name}&apiKey={api_key}&pageSize=15&language=en"
        articles = requests.get(url, timeout=API_TIMEOUT).json().get("articles", [])
        if articles: all_articles = articles
    except Exception as e: print(f"Warning: NewsAPI request failed: {e}.")

    if not all_articles and gnews_key:
        try:
            # MODIFIED: Reduced max to 15
            url = f"https://gnews.io/api/v4/search?q={brand_name}&token={gnews_key}&lang=en&max=15"
            all_articles = requests.get(url, timeout=API_TIMEOUT).json().get('articles', [])
        except Exception as e: print(f"Error: GNews failover also failed: {e}")
    
    sentiments = process_sentiments_in_batch(all_articles, lambda a: f"{a.get('title', '')}. {a.get('description', '')}")
    
    mentions = []
    for article, sentiment in zip(all_articles, sentiments):
        title = article.get('title', '')
        if not title or title == '[Removed]': continue
        mentions.append({
            "platform": "News", "source": article.get('source', {}).get('name', 'Unknown Source'),
            "text": title, "sentiment": sentiment['label'].upper(), "url": article.get('url'),
            "timestamp": parser.parse(article['publishedAt']).isoformat()
        })
    return mentions

def fetch_devto_mentions(brand_name):
    """Fetches Dev.to articles with batch sentiment analysis."""
    try:
        # MODIFIED: Reduced per_page to 15
        url = f"https://dev.to/api/articles?q={brand_name}&per_page=15"
        articles = requests.get(url, timeout=API_TIMEOUT).json()
        sentiments = process_sentiments_in_batch(articles, lambda a: f"{a.get('title', '')}. {a.get('description', '')}")
        
        mentions = []
        for article, sentiment in zip(articles, sentiments):
            title = article.get('title', '')
            if not title: continue
            timestamp = parser.parse(article['published_at']).isoformat() if 'published_at' in article else datetime.datetime.now().isoformat()
            mentions.append({"platform": "Dev.to", "source": "Dev.to", "text": title, "sentiment": sentiment['label'].upper(), "url": article['url'], "timestamp": timestamp})
        return mentions
    except Exception as e:
        print(f"Error: Could not fetch from Dev.to: {e}")
        return []

def fetch_hacker_news_mentions(brand_name):
    """Fetches Hacker News items with batch sentiment analysis."""
    try:
        # MODIFIED: Reduced hitsPerPage to 15
        url = f"http://hn.algolia.com/api/v1/search?query={brand_name}&tags=story,comment&hitsPerPage=15"
        hits = requests.get(url, timeout=API_TIMEOUT).json().get("hits", [])
        sentiments = process_sentiments_in_batch(hits, lambda h: f"{h.get('title', '')}. {h.get('comment_text', '')[:MAX_CONTENT_LENGTH]}")
        
        mentions = []
        for hit, sentiment in zip(hits, sentiments):
            title = hit.get("title", "")
            comment_text = hit.get("comment_text", "")
            display_text = title if title else (comment_text[:100] + '...' if comment_text else '')
            if not display_text.strip(): continue
            timestamp = datetime.datetime.fromtimestamp(hit['created_at_i'], tz=datetime.timezone.utc).isoformat() if 'created_at_i' in hit else datetime.datetime.now().isoformat()
            mentions.append({"platform": "Hacker News", "source": "Hacker News", "text": display_text, "sentiment": sentiment['label'].upper(), "url": hit.get("story_url") or f"http://news.ycombinator.com/item?id={hit.get('objectID')}", "timestamp": timestamp})
        return mentions
    except Exception as e:
        print(f"Error: Could not fetch from Hacker News: {e}")
        return []

def fetch_reddit_mentions(brand_name):
    mentions = []
    try:
        # MODIFIED: Reduced limit to 15
        url = f"https://www.reddit.com/search.json?q={brand_name}&sort=new&limit=15"
        posts = requests.get(url, headers={'User-Agent': 'AnEarOut/1.0'}, timeout=API_TIMEOUT).json().get("data", {}).get("children", [])
        texts_to_process = [f"{p.get('data', {}).get('title', '')}. {p.get('data', {}).get('selftext', '')[:MAX_CONTENT_LENGTH]}" for p in posts]
        sentiments = sentiment_pipeline(texts_to_process)
        
        for post, sentiment in zip(posts, sentiments):
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            if not title: continue
            timestamp = datetime.datetime.fromtimestamp(post_data['created_utc'], tz=datetime.timezone.utc).isoformat()
            mentions.append({"platform": "Reddit", "source": f"r/{post_data.get('subreddit', 'unknown')}", "text": title, "sentiment": sentiment['label'].upper(), "url": f"https://www.reddit.com{post_data.get('permalink', '')}", "timestamp": timestamp})
    except Exception as e: print(f"Error: Could not fetch from Reddit: {e}")
    return mentions

def analyze_mention_summary(all_mentions):
    if not all_mentions: return {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 100}
    sentiment_counts = Counter(m['sentiment'] for m in all_mentions)
    total = len(all_mentions)
    positive_pct = round((sentiment_counts.get("POSITIVE", 0) / total) * 100)
    negative_pct = round((sentiment_counts.get("NEGATIVE", 0) / total) * 100)
    return {"POSITIVE": positive_pct, "NEGATIVE": negative_pct, "NEUTRAL": 100 - positive_pct - negative_pct}

def update_and_get_global_topics(new_mentions, brand_name):
    global global_word_corpus
    all_text = " ".join(m['text'] for m in new_mentions)
    cleaned = re.sub(r'\W+', ' ', all_text).lower()
    words = [w for w in cleaned.split() if w not in stop_words and w not in {brand_name.lower()} and len(w) > 3]
    global_word_corpus.extend(words)
    return [word for word, freq in Counter(global_word_corpus).most_common(20)]


# ==============================================================================
# SECTION 4: CORE APPLICATION LOGIC (WITH PARALLEL FETCHING)
# ==============================================================================

async def run_search_flow(sid, brand_name):
    """
    Orchestrates the search process with parallel fetching and batch processing.
    """
    watched_brands.add(brand_name.lower())
    print(f"Starting new search for '{brand_name}'.")
    
    # Create a list of coroutines to run concurrently.
    tasks_to_run = [
        asyncio.to_thread(fetch_news_api, brand_name, news_api_key, gnews_api_key),
        asyncio.to_thread(fetch_hacker_news_mentions, brand_name),
        asyncio.to_thread(fetch_reddit_mentions, brand_name),
        asyncio.to_thread(fetch_devto_mentions, brand_name),
    ]

    print(f"--- Firing all API requests in parallel for '{brand_name}'... ---")
    results = await asyncio.gather(*tasks_to_run, return_exceptions=True)
    print(f"--- All API requests have completed for '{brand_name}'. Processing results... ---")

    current_search_mentions = []
    for result in results:
        if isinstance(result, Exception):
            print(f"A fetching task failed with an exception: {result}")
        elif result:
            await sio.emit('mention_batch', result, to=sid)
            current_search_mentions.extend(result)
            # We can send a summary update after each successful batch.
            summary_so_far = analyze_mention_summary(current_search_mentions)
            await sio.emit('summary_update', {"sentiment": summary_so_far}, to=sid)

    # --- Final Data Processing (After all parallel tasks are done) ---
    print(f"--- Search for '{brand_name}' finished. Sending final data packets. ---")
    now = datetime.datetime.now(datetime.timezone.utc)
    one_day_ago = now - datetime.timedelta(days=1)
    
    # Safely filter timestamps for the activity chart.
    activity_timestamps = []
    for m in current_search_mentions:
        try:
            ts = parser.parse(m['timestamp'])
            if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
                ts = ts.replace(tzinfo=datetime.timezone.utc)
            if ts > one_day_ago:
                activity_timestamps.append(m['timestamp'])
        except (parser.ParserError, TypeError):
            continue # Safely skip any unparseable timestamps

    await sio.emit('activity_update', activity_timestamps, to=sid)
    
    final_topics = update_and_get_global_topics(current_search_mentions, brand_name)
    await sio.emit('summary_update', {"topics": final_topics}, to=sid)
    
    await sio.emit('search_complete', to=sid)
    print(f"--- All data sent for '{brand_name}'. Search complete. ---")

# ==============================================================================
# SECTION 5: SOCKET.IO EVENT HANDLERS
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
