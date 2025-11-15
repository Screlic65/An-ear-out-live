import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// Define consistent colors for our sentiment types
const COLORS = {
  POSITIVE: '#27ae60',
  NEGATIVE: '#c0392b',
  NEUTRAL: '#7f8c8d',
};

const SentimentChart = ({ data }) => {
  if (!data || data.length === 0) {
    return null; // Don't render if there's no data
  }

  // Calculate the counts of each sentiment from the raw mention data
  const sentimentCounts = data.reduce((acc, mention) => {
    const sentiment = mention.sentiment.toUpperCase();
    acc[sentiment] = (acc[sentiment] || 0) + 1;
    return acc;
  }, {});

  const chartData = Object.keys(sentimentCounts).map(key => ({
    name: key,
    value: sentimentCounts[key],
  }));

  return (
    <div style={{ width: '100%', height: 250 }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
            labelLine={false}
            label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
          >
            {chartData.map((entry) => (
              <Cell key={`cell-${entry.name}`} fill={COLORS[entry.name]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SentimentChart;