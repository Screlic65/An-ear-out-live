import React from 'react';
import './MentionCard.css';

const ArrowIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 17L17 7M17 7H7M17 7V17" />
  </svg>
);

const MentionCard = ({ text, source, sentiment, url, timestamp, isNew }) => {
  const getSentimentClass = () => {
    if (sentiment === 'POSITIVE') return 'positive';
    if (sentiment === 'NEGATIVE') return 'negative';
    return 'neutral';
  };

  const formattedTime = timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  // Conditionally add the 'new-mention' class
  const cardClasses = `card ${getSentimentClass()} ${isNew ? 'new-mention' : ''}`;

  return (
    <div className={cardClasses}>
      <p className="card-text">"{text}"</p>
      <div className="card-footer">
        <span className="card-source">{source}</span>
        <div className="card-actions">
          <span className="card-timestamp">{formattedTime}</span>
          <a href={url} target="_blank" rel="noopener noreferrer" className="card-icon-button" title="Go to source">
            <ArrowIcon />
          </a>
        </div>
      </div>
    </div>
  );
};

export default MentionCard;