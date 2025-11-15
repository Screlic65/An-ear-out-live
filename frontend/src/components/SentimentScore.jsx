import React from 'react';
import './SentimentScore.css';

const SentimentScore = ({ sentiment }) => {
  // Guard clause for when data is not yet available
  if (!sentiment || sentiment.POSITIVE === undefined) {
    return (
      <div className="score-container">
        <div className="score-placeholder">--</div>
        <div className="score-label">Overall Sentiment</div>
      </div>
    );
  }

  // --- SCORE CALCULATION ---
  // A simple weighted score: Positive is +1, Negative is -1, Neutral is 0.
  // We scale this to a 1-10 range.
  const rawScore = (sentiment.POSITIVE * 1) + (sentiment.NEGATIVE * -1);
  // Scale from [-100, 100] to [1, 10]
  const finalScore = ((rawScore + 100) / 200) * 9 + 1;

  // --- COLOR LOGIC ---
  // Determine the overall color based on the score
  let scoreColorClass = 'neutral-score';
  if (finalScore > 6.5) scoreColorClass = 'positive-score';
  if (finalScore < 4.5) scoreColorClass = 'negative-score';

  return (
    <div className="score-container">
      <div className={`score-value ${scoreColorClass}`}>
        {finalScore.toFixed(1)}
      </div>
      <div className="score-label">Overall Sentiment Score</div>

      {/* --- MULTI-COLORED BAR --- */}
      <div className="sentiment-breakdown-bar">
        <div 
          className="bar-segment positive-bg" 
          style={{ width: `${sentiment.POSITIVE}%` }}
          title={`Positive: ${sentiment.POSITIVE}%`}
        />
        <div 
          className="bar-segment negative-bg" 
          style={{ width: `${sentiment.NEGATIVE}%` }}
          title={`Negative: ${sentiment.NEGATIVE}%`}
        />
        <div 
          className="bar-segment neutral-bg" 
          style={{ width: `${sentiment.NEUTRAL}%` }}
          title={`Neutral: ${sentiment.NEUTRAL}%`}
        />
      </div>
    </div>
  );
};

export default SentimentScore;