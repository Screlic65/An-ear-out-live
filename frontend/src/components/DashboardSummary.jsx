import React from 'react';
import SentimentScore from './SentimentScore';
import './DashboardSummary.css';

// ### MODIFIED: Accepts new props for filtering ###
const DashboardSummary = ({ summary, platforms, activeFilter, onFilterClick }) => {
  // A robust guard clause to handle the initial loading state
  if (!summary || !summary.sentiment) {
    return (
      <div className="summary-container placeholder-summary">
        {/* Placeholder to prevent layout shift */}
      </div>
    );
  }

  return (
    <div className="summary-container">
      {/* ### NEW: The filter buttons now live here ### */}
      <div className="summary-left">
        <h3 className="filter-title">Filter by Source</h3>
        <div className="filter-buttons">
          <button onClick={() => onFilterClick('All')} className={activeFilter === 'All' ? 'active' : ''}>All</button>
          {platforms.map(platform => (
            <button key={platform} onClick={() => onFilterClick(platform)} className={activeFilter === platform ? 'active' : ''}>
              {platform}
            </button>
          ))}
        </div>
      </div>
      
      {/* The Sentiment Score now lives on the right */}
      <div className="summary-right">
        <SentimentScore sentiment={summary.sentiment} />
      </div>
    </div>
  );
};

export default DashboardSummary;