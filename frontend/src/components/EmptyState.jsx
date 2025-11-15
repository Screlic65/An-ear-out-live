import React from 'react';
import './EmptyState.css';

// A simple SVG for visual interest
const SearchIcon = () => (
    <svg className="empty-state-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
);


const EmptyState = ({ brandName }) => {
  return (
    <div className="empty-state-container">
      <SearchIcon />
      <h3 className="empty-state-title">No Mentions Found</h3>
      <p className="empty-state-text">
        We couldn't find any recent mentions for "<strong>{brandName}</strong>".
      </p>
      <p className="empty-state-text">
        Try a different brand or check back later.
      </p>
    </div>
  );
};

export default EmptyState;