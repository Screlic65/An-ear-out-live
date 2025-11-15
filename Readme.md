#  An Ear Out: The Real-Time Brand Intelligence Cockpit

**An Ear Out** is a sophisticated, event-driven web application designed to give marketing teams and brand managers precise, real-time insight into online conversations about their brand.

The project directly tackles the challenge of information overload by transforming chaotic, multi-platform chatter into actionable, live data. It is built for speed, resilience, and superior user experience, making it a professional-grade analytics tool.

[![An Ear Out Screenshot](https://i.imgur.com/GzF4E9H.png)](https://an-ear-out.vercel.app/) 
*Note: This is a placeholder image. Replace this URL with a screenshot of your live, finished application.*

---

##  Core Solution & Achievements

We successfully met and exceeded the challenge requirements by focusing on resilient architecture and superior UX.

| Objective | Status | Implementation Detail |
| :--- | :--- | :--- |
| **Aggregation of Mentions** | **✅ Complete (9 Sources)** | Aggregates from **9 diverse sources:** NewsAPI, Reddit, Hacker News, Dev.to, Stack Exchange, and major Indian news RSS feeds. |
| **Sentiment Analysis** | **✅ Advanced** | Uses the superior **RoBERTa model** for nuanced Positive/Negative/Neutral analysis, displayed as a clear **Overall Sentiment Score (1-10)**. |
| **Topic Clustering** | **✅ Complete** | Generates a rolling list of **20 Trending Topics** based on frequency analysis across the global pool of conversations. |
| **Highlight Spikes / Trends** | **✅ Complete** | Features a **24-Hour Activity Trend Line Chart** showing conversation density over time, allowing marketers to easily spot peak hours. |
| **Real-Time Monitoring** | **✅ Event-Driven Streaming** | Data is populated in real-time using WebSockets, creating a dynamic user experience where results stream in as the backend finds them. |

---

##  Final UI/UX Design: The Analytical Cockpit

The final design was refined to maximize usability and visual impact, separating controls from content.

*   **Streaming Feed:** The central panel automatically populates mention cards as data arrives, eliminating the frustrating 10-second loading screen.
*   **Action Center (Left Panel):** Features independently scrollable sections for **Trending Topics** (clickable for instant search discovery) and **Recent Searches**.
*   **Analysis Panel (Right Panel):** Features the high-level insights: The **Overall Sentiment Score** and the **24-Hour Activity Trend Line Chart** (Vertical Timeline).
*   **Professional Polish:** Includes custom, modern disappearing scrollbars and persistent controls for a seamless user experience.

---

##  Technology Stack & Architecture

The application uses a modern, high-performance, and resilient decoupled architecture.

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

### **Backend Setup**
1.  **Clone the repository:**
    ```sh
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name/backend
    ```
2.  **Create a virtual environment and install dependencies:**
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt # (Ensure your requirements.txt lists all necessary libs)
    ```
3.  **Set up your environment variables:**
    -   Create a file named `.env` in the `backend` directory.
    -   Add your NewsAPI key:
        ```
        NEWS_API_KEY="YOUR_API_KEY_HERE"
        ```
4.  **Run the backend server:**
    ```sh
    python -m uvicorn main:app --reload 
    ```
    The backend will be running at `http://localhost:8000`.

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