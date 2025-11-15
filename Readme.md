#  An Ear Out: The Real-Time Brand Intelligence Cockpit

**An Ear Out** is a sophisticated, event-driven web application designed to give marketing teams and brand managers precise, real-time insight into online conversations about their brand.

The project directly tackles the challenge of information overload by transforming chaotic, multi-platform chatter into actionable, live data. It is built for speed, resilience, and superior user experience, making it a professional-grade analytics tool.



#Images

Searching:
https://ibb.co/35nwFfc2

Results:
https://ibb.co/svBqMwnb
---

##  Core Solution & Achievements

| **Aggregation of Mentions** | Aggregates from **9 diverse sources:** NewsAPI, Reddit, Hacker News, Dev.to, Stack Exchange, and major Indian news RSS feeds. |

| **Sentiment Analysis** | Uses the superior **RoBERTa model** for nuanced Positive/Negative/Neutral analysis, displayed as a clear **Overall Sentiment Score (1-10)**. |

| **Topic Clustering** | Generates a rolling list of **20 Trending Topics** based on frequency analysis across the global pool of conversations. |

| **Highlight Spikes / Trends** | Features a **24-Hour Activity Trend Line Chart** showing conversation density over time, allowing marketers to easily spot peak hours. |

| **Real-Time Monitoring** | Data is populated in real-time using IbSockets, creating a dynamic user experience where results stream in as the backend finds them. |

---

##  Final UI/UX Design: The Analytical Cockpit

*   **Streaming Feed:** The central panel automatically populates mention cards as data arrives, eliminating the frustrating 10-second loading screen.
*   **Action Center (Left Panel):** Features independently scrollable sections for **Trending Topics** (clickable for instant search discovery) and **Recent Searches**.
*   **Analysis Panel (Right Panel):** Features the high-level insights: The **Overall Sentiment Score** and the **24-Hour Activity Trend Line Chart** (Vertical Timeline).
*   **Professional Polish:** Includes custom, modern disappearing scrollbars and persistent controls for a seamless user experience.

---


## Engineering Challenges & Key Solutions

This project was built under strict hackathon constraints, requiring complex architectural pivots and deep debugging. These challenges demonstrate the resilience and technical maturity of the final solution:

1.  **Eliminating Latency with True Streaming:**
    *   **The Hurdle:** The initial architecture resulted in a 10-second blank loading screen because the backend waited for all 9 API calls to finish before responding.
    *   **The Solution:** I refactored the entire core data flow into an **event-driven WebSocket streaming model**. The backend now immediately broadcasts data in real-time batches as it is found, solving the latency problem by turning the "wait" into a dynamic, real-time population experience.

2.  **Timezone and Data Integrity (`analyze_activity`):**
    *   **The Hurdle:** The historical chart function failed with a fatal `TypeError` (`can't compare offset-naive and offset-aware datetimes`) due to inconsistent date formats from external APIs (like RSS feeds).
    *   **The Solution:** I implemented a surgical fix in the `analyze_activity` function, strictly enforcing **UTC timezone awareness** on all incoming timestamps (`ts.replace(tzinfo=datetime.timezone.utc)`), guaranteeing the system can correctly compare and plot the last 24 hours of data without crashing.

3.  **API Resilience and Resource Management:**
    *   **The Hurdle:** Reliance on the X (Twitter) free tier posed a risk of rate limits and demo failureI    *   **The Solution:** I implemented a system where the X API is disabled for development but integrated as a final task, saving credits. I integrated a robust **NewsAPI/GNews failover system** to ensure data continuity even if the primary News API key hits its limit.

4.  **UX & Component Stability:**
    *   **The Hurdle:** Repeated bugs arose from complex state logic (the "works on second click, not first" bug) and component crashes (the `ReferenceError`).
    *   **The Solution:** I simplified the core data fetching model to an **imperative "Direct Action" approach** (`executeSearch`), removing complex dependency chains and ensuring absolute stability and predictability for all user-initiated events (search, filtering, topic clicks).

---

##  Deployment

The final application will be deployed on vercel(frontend) and render(backend)

---

##  Technology Stack & Architecture


### **Backend (The Data Engine)**

*   **Framework:** **Python** with **FastAPI** (asynchronous and highly performant).
*   **Real-Time Communication:** **Socket.IO** (for real-time streaming of data batches).
*   **Intelligence:** **Hugging Face Transformers** (RoBERTa model) for sentiment and **NLTK** for topic analysis.
*   **Architecture:** **True Streaming Model**—the server broadcasts sequential data, solving the common API latency and resource-blocking problem.
*   **Data Sources:** Built on a resilient mix of 9 APIs, including **NewsAPI, Reddit, HN, Stack Exchange, Dev.to,** and three major **Indian News RSS Feeds**.

### **Frontend (The Interface)**

*   **Framework:** **React** (with Vite) for a fast, component-based user interface.
*   **Real-Time:** **socket.io-client** to receive and append data batches to the feed state in real-time.
*   **Visualization:** **Recharts** for the professional Sentiment Score visualization and the Activity Trend Line Chart.

---

##  Getting Started: Running Locally

To get a local copy up and running, follow these simple steps.

### **Prerequisites**
-   Python 3.9+
-   Node.js and npm
-   A working NewsAPI key
-   A working GNEWs API key
-   X(Twitter) apikey
-   although you can use it with a single api key also. just remove one of those try... catch blocks from the specifc code. 

### **Backend Setup**
1.  **Create a virtual environment and install dependencies:**
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt # (Ensure your requirements.txt lists all necessary libs)
    ```
2.  **Set up your environment variables:**
    -   Create a file named `.env` in the `backend` directory.
    -   Add your NewsAPI key:
        ```
        NEWS_API_KEY="YOUR_API_KEY_HERE"
        ```
3.  **Run the backend server:**
    ```sh
    python -m uvicorn main:app --reload 
    ```
    The backend will be running at `http://localhost:8000`.
    once it's running, it'll dispaly a json message: {"detail":"Not Found"}

### **Frontend Setup**
1.  **Navigate to the frontend directory and install dependencies:**
    ```sh
    cd ../frontend
    npm install
    ```
2.  **Run the frontend development server:**
    ```sh
    npm run dev
    ```
    The frontend will run at `http://localhost:5173` and automatically connect to the streaming backend.
