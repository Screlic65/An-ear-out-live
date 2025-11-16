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

# First-time setup for NLTK. This will download the 'stopwords' corpus if not found.
print("Initializing NLTK stopwords...")
nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords
stop_words = set(stopwords.words('english'))
print("NLTK is ready.")

# Load environment variables from a .env file for security.
load_dotenv()
news_api_key = os.getenv("NEWS_API_KEY")
gnews_api_key = os.getenv("GNEWS_API_KEY")
if not news_api_key:
    # We need at least one news key to function, so we'll exit if it's missing.
    raise ValueError("CRITICAL: NEWS_API_KEY is not set in the .env file!")

# Load the pre-trained sentiment analysis model from Hugging Face.
# This happens once on startup to avoid reloading it on every request.
print("Loading sentiment analysis model... (This may take a moment)")
sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")
print("Sentiment model loaded successfully.")

# Define some global constants for our application.
API_TIMEOUT = 10  # Seconds to wait for a response from external APIs.
MAX_CONTENT_LENGTH = 512  # Max characters to analyze for sentiment to keep things fast.

# Initialize our FastAPI and Socket.IO server.
# We allow all origins for CORS during development for simplicity.
fastapi_app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, fastapi_app)

# ==============================================================================
# SECTION 2: GLOBAL STATE MANAGEMENT
# ==============================================================================

# These variables hold state for the life of the server instance.
watched_brands = set()
global_word_corpus = deque(maxlen=2000) # A memory-efficient queue for recent words.

# ==============================================================================
# SECTION 3: DATA FETCHING HELPERS
# ==============================================================================

def fetch_news_api(brand_name, api_key, gnews_key):
    """
    Fetches news articles, with a primary (NewsAPI) and failover (GNews) source.
    This provides resilience if one of the services is down or rate-limited.
    """
    mentions = []
    # Attempt to fetch from NewsAPI first.
    try:
        url = f"https://newsapi.org/v2/everything?q={brand_name}&apiKey={api_key}&pageSize=40&language=en"
        articles = requests.get(url, timeout=API_TIMEOUT).json().get("articles", [])
        for a in articles:
            title = a.get('title', '')
            if not title or title == '[Removed]': continue # Skip articles without a title.
            description = a.get('description', '')
            text_to_analyze = f"{title}. {description}"
            sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
            mentions.append({
                "platform": "News", "source": a.get('source', {}).get('name', 'Unknown Source'),
                "text": title, "sentiment": sentiment, "url": a.get('url'),
                "timestamp": parser.parse(a['publishedAt']).isoformat()
            })
        # If we got results, we're done here.
        if mentions:
            return mentions
        
    except Exception as e:
        print(f"Warning: NewsAPI request failed: {e}. Attempting GNews failover.")
    
    # If NewsAPI fails or returns no results, try GNews as a backup.
    if gnews_key:
        try:
            url = f"https://gnews.io/api/v4/search?q={brand_name}&token={gnews_key}&lang=en&max=20"
            articles = requests.get(url, timeout=API_TIMEOUT).json().get('articles', [])
            for a in articles:
                title = a.get('title', '')
                if not title: continue
                description = a.get('description', '')
                text_to_analyze = f"{title}. {description}"
                sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
                mentions.append({
                    "platform": "News", "source": a.get('source', {}).get('name', 'GNews'),
                    "text": title, "sentiment": sentiment, "url": a.get('url'),
                    "timestamp": parser.parse(a['publishedAt']).isoformat()
                })
        except Exception as e:
            print(f"Error: GNews failover also failed: {e}")
            
    return mentions

def fetch_devto_mentions(brand_name):
    """Fetches articles from the Dev.to community platform."""
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
    except Exception as e:
        print(f"Error: Could not fetch from Dev.to: {e}")
    return mentions

def fetch_hacker_news_mentions(brand_name):
    """Fetches stories and comments from Hacker News via the Algolia API."""
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
    except Exception as e:
        print(f"Error: Could not fetch from Hacker News: {e}")
    return mentions

def fetch_reddit_mentions(brand_name):
    """Fetches the latest posts from Reddit matching the brand name."""
    mentions = []
    try:
        # Using a custom User-Agent is good practice.
        headers = {'User-Agent': 'AnEarOut/1.0'}
        url = f"https://www.reddit.com/search.json?q={brand_name}&sort=new&limit=25"
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        response.raise_for_status()
        posts = response.json().get("data", {}).get("children", [])
        for post in posts:
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            if not title: continue
            selftext = post_data.get("selftext", "")
            text_to_analyze = f"{title}. {selftext[:MAX_CONTENT_LENGTH]}"
            sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
            timestamp = datetime.datetime.fromtimestamp(post_data['created_utc'], tz=datetime.timezone.utc).isoformat()
            mentions.append({
                "platform": "Reddit", "source": f"r/{post_data.get('subreddit', 'unknown')}",
                "text": title, "sentiment": sentiment, "url": f"https://www.reddit.com{post_data.get('permalink', '')}",
                "timestamp": timestamp
            })
    except Exception as e:
        print(f"Error: Could not fetch from Reddit: {e}")
    return mentions

def fetch_rss_feed(url, brand_name, platform_name):
    """A generic helper to parse any RSS feed for mentions."""
    mentions = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title = entry.title
            if brand_name.lower() in title.lower():
                summary = entry.get('summary', '')
                # Clean up potential HTML tags in the summary.
                cleaned_summary = re.sub('<[^<]+?>', '', summary)
                text_to_analyze = f"{title}. {cleaned_summary[:MAX_CONTENT_LENGTH]}"
                sentiment = sentiment_pipeline(text_to_analyze)[0]['label'].upper()
                timestamp = parser.parse(entry.published).isoformat() if 'published' in entry else datetime.datetime.now().isoformat()
                mentions.append({"platform": platform_name, "source": platform_name, "text": title, "sentiment": sentiment, "url": entry.link, "timestamp": timestamp})
    except Exception as e:
        print(f"Error: Could not fetch RSS feed from {platform_name}: {e}")
    return mentions

# ==============================================================================
# SECTION 4: ANALYSIS & UTILITY FUNCTIONS
# ==============================================================================

def analyze_mention_summary(all_mentions):
    """Calculates the percentage breakdown of sentiments from a list of mentions."""
    if not all_mentions:
        return {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
    
    sentiment_counts = Counter(m['sentiment'] for m in all_mentions)
    total = len(all_mentions)
    return {
        "POSITIVE": round((sentiment_counts.get("POSITIVE", 0) / total) * 100),
        "NEGATIVE": round((sentiment_counts.get("NEGATIVE", 0) / total) * 100),
        "NEUTRAL": round((sentiment_counts.get("NEUTRAL", 0) / total) * 100)
    }

def update_and_get_global_topics(new_mentions, brand_name):
    """Identifies common keywords to suggest as topics, excluding the brand name itself."""
    global global_word_corpus
    all_text = " ".join(m['text'] for m in new_mentions)
    # Basic text cleaning: remove non-alphanumeric characters and convert to lowercase.
    cleaned = re.sub(r'\W+', ' ', all_text).lower()
    # Find words that aren't common "stopwords" or the brand name.
    words = [
        w for w in cleaned.split() 
        if w not in stop_words and w not in {brand_name.lower()} and len(w) > 3
    ]
    global_word_corpus.extend(words)
    # Return the 20 most common topic words.
    return [word for word, freq in Counter(global_word_corpus).most_common(20)]

# ==============================================================================
# SECTION 5: CORE APPLICATION LOGIC
# ==============================================================================

async def run_search_flow(sid, brand_name):
    """
    Orchestrates the entire search process when a user requests a new brand.
    This runs in the background to avoid blocking the server.
    """
    watched_brands.add(brand_name.lower())
    print(f"Starting new search for '{brand_name}'. Adding to watch list.")
    current_search_mentions = []
    
    # We define our list of data sources to query.
    # Each task is a lambda to ensure it's called with the correct, current brand_name.
    tasks = [
        ("News", lambda: fetch_news_api(brand_name, news_api_key, gnews_api_key)),
        ("Hacker News", lambda: fetch_hacker_news_mentions(brand_name)),
        ("Reddit", lambda: fetch_reddit_mentions(brand_name)),
        ("Dev.to", lambda: fetch_devto_mentions(brand_name)),
        ("Times of India", lambda: fetch_rss_feed("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", brand_name, "Times of India")),
        ("The Hindu", lambda: fetch_rss_feed("https://www.thehindu.com/feeder/default.rss", brand_name, "The Hindu")),
    ]

    # We run each task sequentially and stream the results back to the client as soon as they're ready.
    for name, task_func in tasks:
        try:
            # Let the user know what we're doing.
            await sio.emit('status_update', {'message': f"Searching {name}..."})
            # Run the blocking network request in a separate thread.
            mentions = await asyncio.to_thread(task_func)
            if mentions:
                await sio.emit('mention_batch', mentions, to=sid)
                current_search_mentions.extend(mentions)
                print(f"Streamed {len(mentions)} mentions from {name} for '{brand_name}'")
                # Update the summary in real-time.
                summary_so_far = analyze_mention_summary(current_search_mentions)
                await sio.emit('summary_update', {"sentiment": summary_so_far}, to=sid)
        except Exception as e:
            print(f"CRITICAL ERROR in streaming task {name}: {e}")
            
    print(f"--- Search for '{brand_name}' finished. Sending final data. ---")
    
    # --- Final Data Processing ---
    # 1. Activity Chart Data: Filter the found mentions for the last 24 hours.
    # This is the most reliable way to ensure the chart matches the feed.
    now = datetime.datetime.now(datetime.timezone.utc)
    one_day_ago = now - datetime.timedelta(days=1)
    
    activity_timestamps = []
    for m in current_search_mentions:
        try:
            ts = parser.parse(m['timestamp'])
            # Ensure timestamp is timezone-aware before comparison
            if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
                ts = ts.replace(tzinfo=datetime.timezone.utc)
            if ts > one_day_ago:
                activity_timestamps.append(m['timestamp'])
        except (parser.ParserError, TypeError):
             print(f"Warning: Skipping invalid timestamp for activity chart: {m.get('timestamp')}")

    await sio.emit('activity_update', activity_timestamps, to=sid)
    
    # 2. Topic Suggestions
    final_topics = update_and_get_global_topics(current_search_mentions, brand_name)
    await sio.emit('summary_update', {"topics": final_topics}, to=sid)
    
    # 3. Signal completion to the frontend.
    await sio.emit('search_complete', to=sid)
    print(f"--- All data sent for '{brand_name}'. Search complete. ---")

# ==============================================================================
# SECTION 6: SOCKET.IO EVENT HANDLERS
# ==============================================================================

@sio.on('start_search')
async def handle_start_search(sid, data):
    """Fired when a user clicks the 'Search' button on the frontend."""
    brand_name = data.get('brand')
    if not brand_name:
        return
    # Kick off the search process in the background.
    sio.start_background_task(run_search_flow, sid, brand_name)

@sio.on('connect')
async def connect(sid, environ):
    """A new client has connected."""
    print(f"Client connected: {sid}")

@sio.on('disconnect')
def disconnect(sid):
    """A client has disconnected."""
    print(f"Client disconnected: {sid}")
