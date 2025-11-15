import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const ActivityChart = ({ data, brand }) => {
  const hasData = data && data.length > 0;

  const bucketMap = new Map();
  const now = new Date();

  for (let i = 0; i < 24; i++) {
    const bucketDate = new Date(now.getTime() - i * 3600 * 1000);
    bucketDate.setMinutes(0, 0, 0);
    const key = bucketDate.toISOString();
    const hourLabel = bucketDate.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
    if (!bucketMap.has(key)) {
      bucketMap.set(key, { timestamp: bucketDate.getTime(), label: hourLabel, mentions: 0 });
    }
  }

  if (hasData) {
    data.forEach(isoString => {
      // THE CRITICAL TYPO IS FIXED HERE
      const mentionDate = new Date(isoString);
      if (isNaN(mentionDate)) return;
      mentionDate.setMinutes(0, 0, 0);
      const key = mentionDate.toISOString();
      if (bucketMap.has(key)) {
        const bucket = bucketMap.get(key);
        bucket.mentions += 1;
      }
    });
  }

  const chartData = Array.from(bucketMap.values()).sort((a, b) => a.timestamp - b.timestamp);
  const totalMentions = chartData.reduce((sum, item) => sum + item.mentions, 0);

  return (
    <div className="dashboard-panel">
      <h3>Activity Trend (Last 24h)</h3>
      {totalMentions > 0 ? (
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
            <defs>
              <linearGradient id="colorMentions" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.7}/>
                <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" />
            <XAxis dataKey="label" fontSize="12px" tick={{ fill: '#6b7280' }} />
            <YAxis allowDecimals={false} tick={{ fill: '#6b7280' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#111827',
                border: 'none',
                color: 'white',
                borderRadius: '8px',
                padding: '8px 12px'
              }}
              labelStyle={{ fontWeight: 'bold' }}
            />
            <Area
              type="monotone"
              dataKey="mentions"
              name="Mentions"
              stroke="#4f46e5"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#colorMentions)"
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="chart-placeholder" style={{height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <p style={{color: '#6b7280'}}>{brand ? 'No activity found in the last 24 hours.' : 'Search for a brand to see its 24-hour activity trend.'}</p>
        </div>
      )}
    </div>
  );
};

export default ActivityChart;