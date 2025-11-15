import { useState, useEffect } from 'react';
import io from 'socket.io-client';
import './App.css';
import MentionCard from './components/MentionCard';
import ActivityChart from './components/ActivityChart';
import SentimentScore from './components/SentimentScore';
import SkeletonCard from './components/SkeletonCard';
import EmptyState from './components/EmptyState';

const BACKEND_URL = import.meta.env.VITE_APP_BACKEND_URL || 'http://localhost:8000';
const socket = io(BACKEND_URL);

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentBrand, setCurrentBrand] = useState(null);
  const [activeFilter, setActiveFilter] = useState('All');
  const [searchHistory, setSearchHistory] = useState([]);
  const [summary, setSummary] = useState({ sentiment: {}, topics: [] });
  const [allMentions, setAllMentions] = useState([]);
  const [filteredMentions, setFilteredMentions] = useState([]);
  const [activityData, setActivityData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [platforms, setPlatforms] = useState([]);

  useEffect(() => {
    const handleMentionBatch = (newBatch) => setAllMentions(prev => [...prev, ...newBatch]);
    const handleSummaryUpdate = (update) => setSummary(prev => ({ ...prev, ...update }));
    const handleActivityUpdate = (data) => setActivityData(data);
    const handleSearchComplete = () => setLoading(false);
    
    const handleLiveMention = (newMentions) => {
      console.log("Received live update!", newMentions);
      const markedNew = newMentions.map(m => ({ ...m, isNew: true }));
      setAllMentions(prevMentions => [...markedNew, ...prevMentions]);
      setTimeout(() => {
        setAllMentions(prev => prev.map(m => ({...m, isNew: false})));
      }, 1500);
    };

    socket.on('mention_batch', handleMentionBatch);
    socket.on('summary_update', handleSummaryUpdate);
    socket.on('activity_update', handleActivityUpdate);
    socket.on('search_complete', handleSearchComplete);
    socket.on('live_mention_update', handleLiveMention);

    return () => {
      socket.off('mention_batch', handleMentionBatch);
      socket.off('summary_update', handleSummaryUpdate);
      socket.off('activity_update', handleActivityUpdate);
      socket.off('search_complete', handleSearchComplete);
      socket.off('live_mention_update', handleLiveMention);
    };
  }, []);

  useEffect(() => {
    const filtered = activeFilter === 'All' ? allMentions : allMentions.filter(m => m.platform === activeFilter);
    setFilteredMentions(filtered);
    const uniquePlatforms = [...new Set(allMentions.map(m => m.platform))];
    setPlatforms(uniquePlatforms);
  }, [activeFilter, allMentions]);

  const executeSearch = (term) => {
    if (term.trim() === '' || loading) return;
    const newBrandName = term.trim();
    setAllMentions([]);
    setSummary(prev => ({ sentiment: {}, topics: prev.topics }));
    setActivityData([]);
    setError(null);
    setLoading(true);
    setCurrentBrand(newBrandName);
    setActiveFilter('All');
    socket.emit('start_search', { brand: newBrandName });
    if (!searchHistory.includes(newBrandName)) {
      setSearchHistory([newBrandName, ...searchHistory.slice(0, 9)]);
    }
  };

  const handleKeyPress = (event) => { if (event.key === 'Enter') executeSearch(searchTerm); };

  const renderFeedContent = () => {
    if (loading) {
      return Array.from({ length: 5 }).map((_, index) => <SkeletonCard key={index} />);
    }
    if (error) {
      return <div className="centered" style={{ color: 'red' }}>{error}</div>;
    }
    if (currentBrand && !loading && filteredMentions.length === 0) {
        return <EmptyState brandName={currentBrand} />;
    }
    if (filteredMentions.length > 0) {
      return filteredMentions.map((mention, index) => (
        <MentionCard key={`${mention.url}-${index}`} {...mention} />
      ));
    }
    return (
      <div className="centered initial-prompt">
        <h2>Your brand's pulse is just a search away.</h2>
      </div>
    );
  };
  
  return (
    <div className="app-container">
      <aside className="left-sidebar">
        <header className="app-header">
          <h1>An Ear Out</h1>
          <p>Your brand's pulse, across the web.</p>
        </header>
        <div className="sidebar-section">
          <h3>Top Suggestions</h3>
          <div className="sidebar-scroll-container">
            {summary && summary.topics.length > 0 ? (
              summary.topics.map((topic, index) => (<button key={index} className="topic-tag-button" onClick={() => executeSearch(topic)}>{topic}</button>))
            ) : (<p className="sidebar-placeholder">Search a brand to see topics.</p>)}
          </div>
        </div>
        <div className="sidebar-section">
          <h3>Recent Searches</h3>
          <div className="sidebar-scroll-container">
            {searchHistory.length > 0 ? (
              searchHistory.map(term => (<button key={term} className="history-button" onClick={() => executeSearch(term)}>{term}</button>))
            ) : (<p className="sidebar-placeholder">Your history appears here.</p>)}
          </div>
        </div>
      </aside>
      <main className="main-content-area">
        <div className="main-layout">
          <section className="center-panel">
            <div className="control-panel">
              <div className="search-bar">
                <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} onKeyPress={handleKeyPress} placeholder="Enter a brand name..."/>
                <button onClick={() => executeSearch(searchTerm)} disabled={loading}>{loading ? 'Searching...' : 'Search'}</button>
              </div>
              {currentBrand && (
                <div className="filter-controls">
                  <div className="filter-buttons">
                    <button onClick={() => setActiveFilter('All')} className={activeFilter === 'All' ? 'active' : ''}>All ({allMentions.length})</button>
                    {platforms.map(platform => (
                      <button key={platform} onClick={() => setActiveFilter(platform)} className={activeFilter === platform ? 'active' : ''}>
                        {platform} ({allMentions.filter(m => m.platform === platform).length})
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="feed-container">
              {renderFeedContent()}
            </div>
          </section>
          <aside className="right-sidebar">
            <div className="dashboard-panel">
              <SentimentScore sentiment={summary ? summary.sentiment : null} />
            </div>
            <ActivityChart data={activityData} brand={currentBrand} />
          </aside>
        </div>
      </main>
    </div>
  );
}

export default App;
