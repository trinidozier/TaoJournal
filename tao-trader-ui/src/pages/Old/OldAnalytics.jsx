import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar } from 'recharts';  // Removed invalid HeatMap

const Analytics = () => {
  const navigate = useNavigate();
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [strategies, setStrategies] = useState([]);  // For dropdowns
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    startTime: '00:00',
    endTime: '23:59',
    strategyId: '',
    tradeType: 'All',  // All, Long, Short, Stock, Call, Put, etc.
    direction: 'All',  // All, Long, Short
    followed: 'All',  // All, Followed, Broken (for rules)
    confidenceMin: 1,
    confidenceMax: 5,
  });
  const [analyticsData, setAnalyticsData] = useState({});  // Computed metrics
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }
    fetchTrades();
    fetchStrategies();
  }, []);

  const fetchTrades = async () => {
    try {
      const res = await fetch('https://taojournal-production.up.railway.app/trades', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTrades(data);
      } else {
        setError('Failed to load trades.');
      }
    } catch (err) {
      setError('Error fetching trades.');
    } finally {
      setLoading(false);
    }
  };

  const fetchStrategies = async () => {
    try {
      const res = await fetch('https://taojournal-production.up.railway.app/strategies', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setStrategies(await res.json());
      }
    } catch (err) {
      console.error('Strategies fetch error:', err);
    }
  };

  const applyFilters = (trades) => {
    return trades.filter(trade => {
      const buyDate = new Date(trade.buy_timestamp);
      const buyTime = buyDate.toTimeString().slice(0, 5);

      // Date filter
      const startDate = filters.startDate ? new Date(filters.startDate) : null;
      const endDate = filters.endDate ? new Date(filters.endDate) : null;
      if (startDate && buyDate < startDate) return false;
      if (endDate && buyDate > endDate) return false;

      // Time filter
      if (buyTime < filters.startTime || buyTime > filters.endTime) return false;

      // Strategy filter
      if (filters.strategyId && trade.strategy_id !== parseInt(filters.strategyId)) return false;

      // Trade type filter
      if (filters.tradeType !== 'All' && trade.trade_type !== filters.tradeType) return false;

      // Direction filter
      if (filters.direction !== 'All' && trade.direction !== filters.direction) return false;

      // Confidence filter
      const confidence = parseInt(trade.confidence) || 0;
      if (confidence < filters.confidenceMin || confidence > filters.confidenceMax) return false;

      // Rule followed filter (simplified; for specific rule, we'd need rule_id param)
      if (filters.followed !== 'All') {
        const avgFollowed = trade.rule_adherence ? trade.rule_adherence.filter(r => r.followed).length / trade.rule_adherence.length : 1;
        if (filters.followed === 'Followed' && avgFollowed < 0.8) return false;  // 80% threshold
        if (filters.followed === 'Broken' && avgFollowed > 0.8) return false;
      }

      return true;
    });
  };

  const computeAnalytics = (filteredTrades) => {
    if (filteredTrades.length === 0) return { totalTrades: 0, totalPnl: 0, winRate: 0, avgR: 0 };

    const totalTrades = filteredTrades.length;
    const totalPnl = filteredTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const wins = filteredTrades.filter(t => (t.r_multiple || 0) > 0).length;
    const winRate = ((wins / totalTrades) * 100).toFixed(1);
    const avgR = (filteredTrades.reduce((sum, t) => sum + (t.r_multiple || 0), 0) / totalTrades).toFixed(2);

    // Long/Short
    const longs = filteredTrades.filter(t => t.direction === 'Long');
    const shorts = filteredTrades.filter(t => t.direction === 'Short');
    const longPnl = longs.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const shortPnl = shorts.reduce((sum, t) => sum + (t.pnl || 0), 0);

    // By Strategy
    const byStrategy = {};
    filteredTrades.forEach(t => {
      const stratName = strategies.find(s => s.id === t.strategy_id)?.name || 'No Strategy';
      if (!byStrategy[stratName]) byStrategy[stratName] = { trades: 0, pnl: 0, wins: 0 };
      byStrategy[stratName].trades++;
      byStrategy[stratName].pnl += t.pnl || 0;
      if ((t.r_multiple || 0) > 0) byStrategy[stratName].wins++;
    });

    // By Rule (simplified; group by rule_type + followed)
    const byRule = {};
    filteredTrades.forEach(t => {
      t.rule_adherence?.forEach(ra => {
        const key = `${t.strategy_id}_${ra.rule_id}_${ra.followed ? 'Followed' : 'Broken'}`;
        if (!byRule[key]) byRule[key] = { trades: 0, pnl: 0, wins: 0 };
        byRule[key].trades++;
        byRule[key].pnl += t.pnl || 0;
        if ((t.r_multiple || 0) > 0) byRule[key].wins++;
      });
    });

    // By Trade Type
    const byType = {};
    filteredTrades.forEach(t => {
      const type = t.trade_type || 'Other';
      if (!byType[type]) byType[type] = { trades: 0, pnl: 0, wins: 0 };
      byType[type].trades++;
      byType[type].pnl += t.pnl || 0;
      if ((t.r_multiple || 0) > 0) byType[type].wins++;
    });

    // Time Breakdown (Hour of Day)
    const byHour = {};
    filteredTrades.forEach(t => {
      const hour = new Date(t.buy_timestamp).getHours();
      if (!byHour[hour]) byHour[hour] = { trades: 0, pnl: 0, wins: 0 };
      byHour[hour].trades++;
      byHour[hour].pnl += t.pnl || 0;
      if ((t.r_multiple || 0) > 0) byHour[hour].wins++;
    });

    // Risk Metrics (simplified)
    const sortedPnL = filteredTrades.map(t => t.pnl || 0).sort((a, b) => a - b);
    const maxDrawdown = Math.min(...sortedPnL.slice(0, -1).reduce((drawdown, pnl, i) => {
      const peak = Math.max(...sortedPnL.slice(0, i + 1));
      return Math.min(drawdown, pnl - peak);
    }, 0), 0);
    const sharpe = totalPnl / Math.sqrt(totalTrades) || 0;  // Simplified Sharpe (assume risk-free=0, std dev approx)

    return {
      totalTrades,
      totalPnl,
      winRate,
      avgR,
      longPnl,
      shortPnl,
      byStrategy,
      byRule,
      byType,
      byHour,
      maxDrawdown,
      sharpe,
    };
  };

  useEffect(() => {
    const filtered = applyFilters(trades);
    setAnalyticsData(computeAnalytics(filtered));
  }, [trades, filters]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  if (loading) return <div className="p-6 text-center">Loading analytics...</div>;
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>;

  const { totalTrades, totalPnl, winRate, avgR, longPnl, shortPnl, byStrategy, byRule, byType, byHour, maxDrawdown, sharpe } = analyticsData;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-100 to-blue-100 p-6">
      {/* Header with Return Button */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-4xl font-bold text-gray-800">Analytics Dashboard</h1>
        <button onClick={() => navigate('/dashboard')} className="bg-blue-500 text-white px-6 py-2 rounded-lg shadow-md hover:bg-blue-600 transition">
          Return to Dashboard
        </button>
      </div>

      {/* Filters Section */}
      <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
        <h2 className="text-xl font-bold mb-4">Filters</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div>
            <label>Start Date</label>
            <input type="date" value={filters.startDate} onChange={(e) => handleFilterChange('startDate', e.target.value)} className="w-full border p-2 rounded" />
          </div>
          <div>
            <label>End Date</label>
            <input type="date" value={filters.endDate} onChange={(e) => handleFilterChange('endDate', e.target.value)} className="w-full border p-2 rounded" />
          </div>
          <div>
            <label>Start Time</label>
            <input type="time" value={filters.startTime} onChange={(e) => handleFilterChange('startTime', e.target.value)} className="w-full border p-2 rounded" />
          </div>
          <div>
            <label>End Time</label>
            <input type="time" value={filters.endTime} onChange={(e) => handleFilterChange('endTime', e.target.value)} className="w-full border p-2 rounded" />
          </div>
          <div>
            <label>Strategy</label>
            <select value={filters.strategyId} onChange={(e) => handleFilterChange('strategyId', e.target.value)} className="w-full border p-2 rounded">
              <option value="">All Strategies</option>
              {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label>Trade Type</label>
            <select value={filters.tradeType} onChange={(e) => handleFilterChange('tradeType', e.target.value)} className="w-full border p-2 rounded">
              <option value="All">All</option>
              <option value="Stock">Stock</option>
              <option value="Call">Call</option>
              <option value="Put">Put</option>
              <option value="Straddle">Straddle</option>
              <option value="Covered Call">Covered Call</option>
              <option value="Cash Secured Put">Cash Secured Put</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label>Direction</label>
            <select value={filters.direction} onChange={(e) => handleFilterChange('direction', e.target.value)} className="w-full border p-2 rounded">
              <option value="All">All</option>
              <option value="Long">Long</option>
              <option value="Short">Short</option>
            </select>
          </div>
          <div>
            <label>Rule Adherence</label>
            <select value={filters.followed} onChange={(e) => handleFilterChange('followed', e.target.value)} className="w-full border p-2 rounded">
              <option value="All">All</option>
              <option value="Followed">Followed</option>
              <option value="Broken">Broken</option>
            </select>
          </div>
          <div>
            <label>Confidence Min</label>
            <input type="number" min="1" max="5" value={filters.confidenceMin} onChange={(e) => handleFilterChange('confidenceMin', e.target.value)} className="w-full border p-2 rounded" />
          </div>
          <div>
            <label>Confidence Max</label>
            <input type="number" min="1" max="5" value={filters.confidenceMax} onChange={(e) => handleFilterChange('confidenceMax', e.target.value)} className="w-full border p-2 rounded" />
          </div>
        </div>
      </div>

      {/* Overall Summary */}
      <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
        <h2 className="text-xl font-bold mb-4">Overall Summary</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded">
            <h3 className="text-2xl font-bold">${totalPnl.toFixed(2)}</h3>
            <p>Total PnL</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <h3 className="text-2xl font-bold">{winRate}%</h3>
            <p>Win Rate</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <h3 className="text-2xl font-bold">{avgR}</h3>
            <p>Avg R-Ratio</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded">
            <h3 className="text-2xl font-bold">{totalTrades}</h3>
            <p>Total Trades</p>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3>Long Trades: ${longPnl.toFixed(2)}</h3>
          </div>
          <div>
            <h3>Short Trades: ${shortPnl.toFixed(2)}</h3>
          </div>
        </div>
        <div className="mt-4">
          <h3>Risk Metrics</h3>
          <p>Max Drawdown: ${maxDrawdown.toFixed(2)}</p>
          <p>Sharpe Ratio: {sharpe.toFixed(2)}</p>
        </div>
      </div>

      {/* By Strategy */}
      <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
        <h2 className="text-xl font-bold mb-4">By Strategy</h2>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Strategy</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trades</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Win Rate</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg R</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {Object.entries(byStrategy).map(([name, stats]) => (
              <tr key={name}>
                <td className="px-6 py-4 whitespace-nowrap">{name}</td>
                <td className="px-6 py-4 whitespace-nowrap">{stats.trades}</td>
                <td className="px-6 py-4 whitespace-nowrap">${stats.pnl.toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap">{((stats.wins / stats.trades) * 100).toFixed(1)}%</td>
                <td className="px-6 py-4 whitespace-nowrap">{(stats.pnl / stats.trades / 1000).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* By Rule Adherence */}
      <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
        <h2 className="text-xl font-bold mb-4">By Rule (Followed vs. Broken)</h2>
        <p className="mb-4">Note: Aggregated across strategies; select a strategy filter for specifics.</p>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rule Key</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trades</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Win Rate</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {Object.entries(byRule).map(([key, stats]) => (
              <tr key={key}>
                <td className="px-6 py-4 whitespace-nowrap">{key}</td>
                <td className="px-6 py-4 whitespace-nowrap">{stats.trades}</td>
                <td className="px-6 py-4 whitespace-nowrap">${stats.pnl.toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap">{((stats.wins / stats.trades) * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* By Trade Type */}
      <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
        <h2 className="text-xl font-bold mb-4">By Trade Type</h2>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trades</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Win Rate</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {Object.entries(byType).map(([type, stats]) => (
              <tr key={type}>
                <td className="px-6 py-4 whitespace-nowrap">{type}</td>
                <td className="px-6 py-4 whitespace-nowrap">{stats.trades}</td>
                <td className="px-6 py-4 whitespace-nowrap">${stats.pnl.toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap">{((stats.wins / stats.trades) * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* By Hour of Day (Time Breakdown) */}
      <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
        <h2 className="text-xl font-bold mb-4">By Hour of Day</h2>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
          {Object.entries(byHour).map(([hour, stats]) => (
            <div key={hour} className="text-center p-4 bg-gray-50 rounded">
              <h3 className="font-bold">{hour}:00</h3>
              <p>Trades: {stats.trades}</p>
              <p>PnL: ${stats.pnl.toFixed(2)}</p>
              <p>Win: {((stats.wins / stats.trades) * 100).toFixed(1)}%</p>
            </div>
          ))}
        </div>
      </div>

      {/* Export Buttons */}
      <div className="flex gap-4">
        <button onClick={() => {/* Export logic using backend /export/analytics */}} className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600">
          Export Summary (CSV)
        </button>
        <button onClick={() => {/* Similar for PDF */}} className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600">
          Export Report (PDF)
        </button>
      </div>
    </div>
  );
};

export default Analytics;