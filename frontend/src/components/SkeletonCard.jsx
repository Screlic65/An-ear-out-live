import React from 'react';
import './SkeletonCard.css';

const SkeletonCard = () => {
  return (
    <div className="skeleton-card">
      <div className="skeleton-text skeleton-line"></div>
      <div className="skeleton-text skeleton-line" style={{ width: '60%' }}></div>
      <div className="skeleton-footer">
        <div className="skeleton-source skeleton-line"></div>
        <div className="skeleton-time skeleton-line"></div>
      </div>
    </div>
  );
};

export default SkeletonCard;