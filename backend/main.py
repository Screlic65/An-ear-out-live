import os
import requests
import re
import nltk
import datetime
import feedparser
import socketio
import asyncio
from dateutil import parser
from collections import Counter, deque
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from transformers import pipeline
import tweepy 

# --- NLTK and Initializations ---
print("Checking for NLTK stopwords...")
nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords
stop_words = set(stopwords.words('english'))
print("NLTK stopwords are ready.")

load_dotenv()
news_api_key = os.getenv("NEWS_API_KEY")
gnews_api_key = os.getenv("GNEWS_API_KEY") # Load GNews Key
bearer_token = os.getenv("X_BEARER_TOKEN") 
if not news_api_key: raise ValueError("NEWS_API_KEY is not set in the .env file!")

print("Loading sentiment analysis model...")
sentiment_pipeline = pipeline("sentiment-analysis", model="finiteautomata/bertweet-base-sentiment-analysis")
print("Model loaded.")

API_TIMEOUT = 10
MAX_CONTENT_LENGTH = 512

# --- FastAPI and Socket.IO Setup ---
fastapi_app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, fastapi_app)

# --- State Management for Live Updates ---
watched_brands = set()
last_seen_timestamps = { "Reddit": datetime.datetime.now(datetime.timezone.utc), }
global_word_corpus = deque(maxlen=2000)


# --- DATA FETCHING FUNCTIONS ---

def fetch_news_api(brand_name, api_key, gnews_key):
    mentions = []
    # Try NewsAPI first
    try:
        url = f"https://newsapi.org/v2/everything?q={brand_name}&apiKey={api_key}&pageSize=40&language=en"
        articles = requests.get(url, timeout=API_TIMEOUT).json().get("articles", [])
        for a in articles:
            title = a.get('title', '')
            description = a.get('description', '')
            text_to_analyze = f"{title}. {description}"
            sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
            mentions.append({
                "platform": "NewsAPI", "source": a.get('source', {}).get('name', 'Unknown Source'),
                "text": title, "sentiment": sentiment, "url": a.get('url'),
                "timestamp": parser.parse(a['publishedAt']).isoformat()
            })
        if mentions: return mentions
        
    except Exception as e:
        print(f"NewsAPI primary failed: {e}. Trying GNews failover.")
    
    # Try GNews failover
    if gnews_key:
        try:
            url = f"https://gnews.io/api/v4/search?q={brand_name}&token={gnews_key}&lang=en&max=20"
            response = requests.get(url, timeout=API_TIMEOUT).json()
            articles = response.get('articles', [])
            for a in articles:
                title = a.get('title', '')
                description = a.get('description', '')
                text_to_analyze = f"{title}. {description}"
                sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
                mentions.append({
                    "platform": "GNews", "source": a.get('source', {}).get('name', 'Unknown Source'),
                    "text": title, "sentiment": sentiment, "url": a.get('url'),
                    "timestamp": parser.parse(a['publishedAt']).isoformat()
                })
        except Exception as e:
            print(f"GNews failover failed: {e}")
            
    return mentions


def fetch_devto_mentions(brand_name):
    # ... (body of this function is the same)
    mentions = []
    try:
        url = f"https://dev.to/api/articles?q={brand_name}&per_page=30"
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        articles = response.json()
        for article in articles:
            title = article.get('title', '')
            if not title: continue
            description = article.get('description', '')
            text_to_analyze = f"{title}. {description}"
            sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
            timestamp = parser.parse(article['published_at']).isoformat() if 'published_at' in article else datetime.datetime.now().isoformat()
            mentions.append({"platform": "Dev.to", "source": "Dev.to", "text": title, "sentiment": sentiment, "url": article['url'], "timestamp": timestamp})
    except Exception as e: print(f"ERROR fetching from Dev.to: {e}")
    return mentions

def fetch_stack_exchange_mentions(brand_name):
    # ... (body of this function is the same)
    mentions = []
    try:
        url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=activity&q={brand_name}&site=stackoverflow&pagesize=15"
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        questions = response.json().get('items', [])
        for q in questions:
            title = q.get('title', '')
            if not title: continue
            sentiment = sentiment_pipeline(title)[0]['label'].upper()
            timestamp = datetime.datetime.fromtimestamp(q['creation_date'], tz=datetime.timezone.utc).isoformat() if 'creation_date' in q else datetime.datetime.now().isoformat()
            mentions.append({"platform": "Stack Exchange", "source": "Stack Overflow", "text": title, "sentiment": sentiment, "url": q['link'], "timestamp": timestamp})
    except Exception as e: print(f"ERROR fetching from Stack Exchange: {e}")
    return mentions

def fetch_hacker_news_mentions(brand_name):
    # ... (body of this function is the same)
    mentions = []
    try:
        url = f"http://hn.algolia.com/api/v1/search?query={brand_name}&tags=story,comment&hitsPerPage=30"
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        hits = response.json().get("hits", [])
        for hit in hits:
            title = hit.get("title", "")
            comment_text = hit.get("comment_text", "")
            display_text = title if title else (comment_text[:100] + '...' if comment_text else '')
            if not display_text.strip(): continue
            text_to_analyze = f"{title}. {comment_text[:MAX_CONTENT_LENGTH]}"
            sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
            timestamp = datetime.datetime.fromtimestamp(hit['created_at_i'], tz=datetime.timezone.utc).isoformat() if 'created_at_i' in hit else datetime.datetime.now().isoformat()
            mentions.append({"platform": "Hacker News", "source": "Hacker News", "text": display_text, "sentiment": sentiment, "url": hit.get("story_url") or f"http://news.ycombinator.com/item?id={hit.get('objectID')}", "timestamp": timestamp})
    except Exception as e: print(f"ERROR fetching from Hacker News: {e}")
    return mentions

def fetch_reddit_mentions(brand_name, newer_than=None):
    # ... (body of this function is the same)
    mentions = []
    try:
        url = f"https://www.reddit.com/search.json?q={brand_name}&sort=new&limit=25"
        response = requests.get(url, headers={'User-Agent': 'AnEarOut/0.5'}, timeout=API_TIMEOUT)
        response.raise_for_status()
        posts = response.json().get("data", {}).get("children", [])
        for post in posts:
            post_data = post.get("data", {})
            created_time = datetime.datetime.fromtimestamp(post_data['created_utc'], tz=datetime.timezone.utc)
            if newer_than and created_time <= newer_than: continue
            title = post_data.get("title", "")
            if not title: continue
            selftext = post_data.get("selftext", "")
            text_to_analyze = f"{title}. {selftext[:MAX_CONTENT_LENGTH]}"
            sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
            mentions.append({
                "platform": "Reddit", "source": f"r/{post_data.get('subreddit', 'unknown')}",
                "text": title, "sentiment": sentiment, "url": f"https://www.reddit.com{post_data.get('permalink', '')}",
                "timestamp": created_time.isoformat()
            })
    except Exception as e: print(f"ERROR fetching from Reddit: {e}")
    return mentions

# --- RSS Functions (Same) ---
def fetch_rss_feed(url, brand_name, platform_name):
    # ... (body of this function is the same)
    mentions = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title = entry.title
            if brand_name.lower() in title.lower():
                summary = entry.get('summary', '')
                cleaned_summary = re.sub('<[^<]+?>', '', summary)
                text_to_analyze = f"{title}. {cleaned_summary[:MAX_CONTENT_LENGTH]}"
                sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
                timestamp = parser.parse(entry.published).isoformat() if 'published' in entry else datetime.datetime.now().isoformat()
                mentions.append({"platform": platform_name, "source": platform_name, "text": title, "sentiment": sentiment, "url": entry.link, "timestamp": timestamp})
    except Exception as e: print(f"ERROR fetching RSS from {platform_name}: {e}")
    return mentions


# --- ANALYSIS FUNCTIONS (Same) ---
def analyze_mention_summary(all_mentions):
    if not all_mentions: return { "POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0 }
    sentiment_counts = Counter(m['sentiment'] for m in all_mentions)
    total = len(all_mentions)
    return {
        "POSITIVE": round((sentiment_counts.get("POSITIVE", 0) / total) * 100),
        "NEGATIVE": round((sentiment_counts.get("NEGATIVE", 0) / total) * 100),
        "NEUTRAL": round((sentiment_counts.get("NEUTRAL", 0) / total) * 100)
    }

def update_and_get_global_topics(new_mentions, brand_name):
    global global_word_corpus
    all_text = " ".join(m['text'] for m in new_mentions)
    cleaned = re.sub(r'\W+', ' ', all_text).lower()
    words = [w for w in cleaned.split() if w not in stop_words and w not in {brand_name.lower()} and len(w) > 3]
    global_word_corpus.extend(words)
    return [w for w, freq in Counter(global_word_corpus).most_common(20)]

def analyze_activity(current_search_mentions):
    now = datetime.datetime.now(datetime.timezone.utc)
    one_day_ago = now - datetime.timedelta(days=1)
    
    all_timestamps = []
    
    # We will filter the mentions for the last 24 hours
    for m in current_search_mentions:
        try:
            # Parse the string into an datetime object
            ts = parser.parse(m['timestamp'])
            
            # THE FIX: If the timestamp is naive (lacks timezone), make it UTC aware.
            if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
                ts = ts.replace(tzinfo=datetime.timezone.utc)
            
            # Now the comparison is safe
            if ts > one_day_ago:
                all_timestamps.append(m['timestamp'])
                
        except Exception as e:
            # Log any bad date string but don't crash the server
            print(f"Warning: Could not parse timestamp {m.get('timestamp')}: {e}")
            continue

    # We return the list of valid timestamps within the 24h window
    return all_timestamps
# --- CORE STREAMING LOGIC ---
async def run_search_flow(sid, brand_name):
    watched_brands.add(brand_name.lower())
    print(f"--- [INITIAL SEARCH] for: {brand_name}. Added to watch list. ---")
    current_search_mentions = []
    
    # Define all fetching tasks in order
    tasks = [
        ("X", lambda: fetch_x_mentions(brand_name, bearer_token)),
        ("NewsAPI/GNews", lambda: fetch_news_api(brand_name, news_api_key, gnews_api_key)), # NEW: Pass both keys
        ("Hacker News", lambda: fetch_hacker_news_mentions(brand_name)),
        ("Reddit", lambda: fetch_reddit_mentions(brand_name)),
        ("Dev.to", lambda: fetch_devto_mentions(brand_name)),
        ("Stack Exchange", lambda: fetch_stack_exchange_mentions(brand_name)),
        ("Times of India", lambda: fetch_rss_feed("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", brand_name, "Times of India")),
        ("The Hindu", lambda: fetch_rss_feed("https://www.thehindu.com/feeder/default.rss", brand_name, "The Hindu")),
        ("Hindustan Times", lambda: fetch_rss_feed("https://www.hindustantimes.com/rss/top-news/rssfeed.xml", brand_name, "Hindustan Times")),
    ]

    for name, task_func in tasks:
        try:
            await sio.emit('status_update', {'message': f"Searching {name}..."})
            mentions = await asyncio.to_thread(task_func)
            if mentions:
                await sio.emit('mention_batch', mentions, to=sid)
                current_search_mentions.extend(mentions)
                print(f"Streamed {len(mentions)} mentions from {name}")
                summary_so_far = analyze_mention_summary(current_search_mentions)
                await sio.emit('summary_update', {"sentiment": summary_so_far}, to=sid)
        except Exception as e:
            print(f"ERROR in streaming task {name}: {e}")
            
    print("--- Stream finished. Sending final updates. ---")
    
    activity_timestamps = analyze_activity(current_search_mentions)
    await sio.emit('activity_update', activity_timestamps, to=sid)
    
    final_topics = update_and_get_global_topics(current_search_mentions, brand_name)
    await sio.emit('summary_update', {"topics": final_topics}, to=sid)
    
    await sio.emit('search_complete', to=sid)
    print("--- Initial Search Complete ---")

# --- Live Update Background Task ---
async def background_polling_task():
    # ... (body of this function is the same)
    pass

@fastapi_app.on_event("startup")
async def startup_event():
    # We remove the background poller until the X logic is fully integrated
    pass

# --- Socket.IO Event Handlers ---
@sio.on('start_search')
async def handle_start_search(sid, data):
    brand_name = data.get('brand')
    if not brand_name: return
    sio.start_background_task(run_search_flow, sid, brand_name)

@sio.on('connect')
async def connect(sid, environ):
    print('Client connected:', sid)

@sio.on('disconnect')
def disconnect(sid):
    print('Client disconnected:', sid)
