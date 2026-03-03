/**
 * Emotion Comparison Tool Component
 * 
 * Allows side-by-side comparison of emotional metrics across different time periods.
 */

'use client';

import { useState } from 'react';

interface ComparisonData {
  period1: {
    metrics: {
      avg_sentiment: number;
      avg_mood: number;
      avg_stress: number;
      journal_entries: number;
    };
  };
  period2: {
    metrics: {
      avg_sentiment: number;
      avg_mood: number;
      avg_stress: number;
      journal_entries: number;
    };
  };
  comparison: {
    sentiment: { change: number; percentage: number; direction: string };
    mood: { change: number; percentage: number; direction: string };
    stress: { change: number; percentage: number; direction: string };
  };
}

export default function EmotionComparisonTool() {
  const [period1Start, setPeriod1Start] = useState('');
  const [period1End, setPeriod1End] = useState('');
  const [period2Start, setPeriod2Start] = useState('');
  const [period2End, setPeriod2End] = useState('');
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCompare = async () => {
    if (!period1Start || !period1End || !period2Start || !period2End) {
      alert('Please select all date ranges');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/v1/emotion-comparison/compare', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          period1_start: period1Start,
          period1_end: period1End,
          period2_start: period2Start,
          period2_end: period2End
        })
      });

      const data = await response.json();
      setComparisonData(data);
    } catch (error) {
      console.error('Comparison failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-6">Emotion Comparison Tool</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Period 1 */}
          <div className="space-y-4">
            <h3 className="font-semibold">Period 1</h3>
            <div>
              <label className="block text-sm mb-1">Start Date</label>
              <input
                type="date"
                value={period1Start}
                onChange={(e) => setPeriod1Start(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">End Date</label>
              <input
                type="date"
                value={period1End}
                onChange={(e) => setPeriod1End(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>

          {/* Period 2 */}
          <div className="space-y-4">
            <h3 className="font-semibold">Period 2</h3>
            <div>
              <label className="block text-sm mb-1">Start Date</label>
              <input
                type="date"
                value={period2Start}
                onChange={(e) => setPeriod2Start(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">End Date</label>
              <input
                type="date"
                value={period2End}
                onChange={(e) => setPeriod2End(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>
        </div>

        <button
          onClick={handleCompare}
          disabled={loading}
          className="w-full mt-6 bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Comparing...' : 'Compare Periods'}
        </button>
      </div>

      {/* Results */}
      {comparisonData && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold mb-4">Comparison Results</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border rounded">
              <div className="text-sm font-medium">Sentiment</div>
              <div className="text-2xl font-bold mt-2">
                {comparisonData.comparison.sentiment.percentage.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">
                {comparisonData.comparison.sentiment.direction === 'up' ? '↑' : '↓'}
                {comparisonData.comparison.sentiment.change.toFixed(2)}
              </div>
            </div>

            <div className="p-4 border rounded">
              <div className="text-sm font-medium">Mood</div>
              <div className="text-2xl font-bold mt-2">
                {comparisonData.comparison.mood.percentage.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">
                {comparisonData.comparison.mood.direction === 'up' ? '↑' : '↓'}
                {comparisonData.comparison.mood.change.toFixed(2)}
              </div>
            </div>

            <div className="p-4 border rounded">
              <div className="text-sm font-medium">Stress</div>
              <div className="text-2xl font-bold mt-2">
                {comparisonData.comparison.stress.percentage.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">
                {comparisonData.comparison.stress.direction === 'up' ? '↑' : '↓'}
                {comparisonData.comparison.stress.change.toFixed(2)}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            <div className="p-4 bg-gray-50 rounded">
              <h4 className="font-semibold mb-2">Period 1</h4>
              <div className="space-y-1 text-sm">
                <div>Sentiment: {comparisonData.period1.metrics.avg_sentiment.toFixed(2)}</div>
                <div>Mood: {comparisonData.period1.metrics.avg_mood.toFixed(2)}</div>
                <div>Stress: {comparisonData.period1.metrics.avg_stress.toFixed(2)}</div>
                <div>Entries: {comparisonData.period1.metrics.journal_entries}</div>
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded">
              <h4 className="font-semibold mb-2">Period 2</h4>
              <div className="space-y-1 text-sm">
                <div>Sentiment: {comparisonData.period2.metrics.avg_sentiment.toFixed(2)}</div>
                <div>Mood: {comparisonData.period2.metrics.avg_mood.toFixed(2)}</div>
                <div>Stress: {comparisonData.period2.metrics.avg_stress.toFixed(2)}</div>
                <div>Entries: {comparisonData.period2.metrics.journal_entries}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
