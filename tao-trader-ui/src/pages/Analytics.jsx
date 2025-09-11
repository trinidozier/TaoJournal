import React, { useEffect, useState, Component } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar } from 'recharts';
import HeatMapGrid from 'react-heatmap-grid';

// Error Boundary Component
class ErrorBoundary extends Component {
  state = { error: null, errorInfo: null };

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="p-6 text-center text-red-500">
          <h2 className="text-xl font-bold mb-4">Something went wrong in Analytics</h2>
          <p>{this.state.error.toString()}</p>
          <p>Please check your dependencies (react, react-dom, recharts, react-heatmap-grid) or contact support.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const Analytics = () => {
  const navigate = useNavigate();
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [strategies, setStrategies] = useState([]);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    startTime: '00:00',
    endTime: '23:59',
    strategyId: '',
    tradeType: 'All',
    direction: 'All',
    followed: 'All',
    confidenceMin: 1,
    confidenceMax: 5,
  });
  const [analyticsData, setAnalyticsData] = useState({});

  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!token) {
      console.log('No token found, redirecting to login');
      navigate('/login');
      return;
    }
    fetchTrades();
    fetchStrategies();
  }, []);

  const fetchTrades = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('https://taojournal-production.up.railway.app/trades', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTrades(data);
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError('Failed to load trades.');
      }
    } catch (err) {
      console.error('Error fetching trades:', err);
      setError('Error fetching trades. Please try again.');
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
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      }
    } catch (err) {
      console.error('Strategies fetch error:', err);
    }
  };

  const applyFilters = (trades) => {
    if (!trades) return [];
    return trades.filter(trade => {
      const buyDate = new Date(trade.buy_timestamp);
      const buyTime = buyDate.toTimeString().slice(0, 5);

      const startDate = filters.startDate ? new Date(filters.startDate) : null;
      const endDate = filters.endDate ? new Date(filters.endDate) : null;
      if (startDate && buyDate < startDate) return false;
      if (endDate && buyDate > endDate) return false;

      if (buyTime < filters.startTime || buyTime > filters.endTime) return false;

      if (filters.strategyId && trade.strategy_id !== parseInt(filters.strategyId)) return false;

      if (filters.tradeType !== 'All' && trade.trade_type !== filters.tradeType) return false;

      if (filters.direction !== 'All' && trade.direction !== filters.direction) return false;

      const confidence = parseInt(trade.confidence) || 0;
      if (confidence < filters.confidenceMin || confidence > filters.confidenceMax) return false;

      if (filters.followed !== 'All') {
        const avgFollowed = trade.rule_adherence ? trade.rule_adherence.filter(r => r.followed).length / trade.rule_adherence.length : 1;
        if (filters.followed === 'Followed' && avgFollowed < 0.8) return false;
        if (filters.followed === 'Broken' && avgFollowed > 0.8) return false;
      }

      return true;
    });
  };

  const computeAnalytics = (filteredTrades) => {
    if (!filteredTrades || filteredTrades.length === 0) {
      return {
        totalTrades: 0,
        totalPnl: 0,
        winRate: 0,
        avgR: 0,
        longPnl: 0,
        shortPnl: 0,
        byStrategy: {},
        byRule: {},
        byType: {},
        byHour: {},
        byDayOfWeek: {},
        maxDrawdown: 0,
        sharpe: 0,
        avgRiskReward: 0,
        maxConsecutiveWins: 0,
        maxConsecutiveLosses: 0,
        behavioral: { overconfidence: '', ruleBreakImpact: '' },
        equityCurve: [],
        heatmapPnL: [],
      };
    }

    const totalTrades = filteredTrades.length;
    const totalPnl = filteredTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const wins = filteredTrades.filter(t => (t.r_multiple || 0) > 0).length;
    const winRate = ((wins / totalTrades) * 100).toFixed(1);
    const avgR = (filteredTrades.reduce((sum, t) => sum + (t.r_multiple || 0), 0) / totalTrades).toFixed(2);

    const longs = filteredTrades.filter(t => t.direction === 'Long');
    const shorts = filteredTrades.filter(t => t.direction === 'Short');
    const longPnl = longs.reduce((sum, t) => sum + (t.pnl || 0), 0) || 0;
    const shortPnl = shorts.reduce((sum, t) => sum + (t.pnl || 0), 0) || 0;

    const byStrategy = {};
    filteredTrades.forEach(t => {
      const stratName = strategies.find(s => s.id === t.strategy_id)?.name || 'No Strategy';
      if (!byStrategy[stratName]) byStrategy[stratName] = { trades: 0, pnl: 0, wins: 0, avgRisk: 0, expectancy: 0 };
      byStrategy[stratName].trades++;
      byStrategy[stratName].pnl += t.pnl || 0;
      byStrategy[stratName].avgRisk += (t.qty * t.buy_price * 0.01) || 0;
      if ((t.r_multiple || 0) > 0) byStrategy[stratName].wins++;
    });
    Object.keys(byStrategy).forEach(k => {
      const s = byStrategy[k];
      s.winRate = ((s.wins / s.trades) * 100).toFixed(1);
      s.avgR = (s.pnl / s.trades / 1000).toFixed(2);
      s.avgRisk = (s.avgRisk / s.trades).toFixed(2);
      s.expectancy = (s.winRate / 100 * parseFloat(s.avgR) - (1 - s.winRate / 100)).toFixed(2);
    });

    const byRule = {};
    filteredTrades.forEach(t => {
      t.rule_adherence?.forEach(ra => {
        const key = `${t.strategy_id}_${ra.rule_id}_${ra.followed ? 'Followed' : 'Broken'}`;
        if (!byRule[key]) byRule[key] = { trades: 0, pnl: 0, wins: 0, avgRisk: 0, expectancy: 0 };
        byRule[key].trades++;
        byRule[key].pnl += t.pnl || 0;
        byRule[key].avgRisk += (t.qty * t.buy_price * 0.01) || 0;
        if ((t.r_multiple || 0) > 0) byRule[key].wins++;
      });
    });
    Object.keys(byRule).forEach(k => {
      const s = byRule[k];
      s.winRate = ((s.wins / s.trades) * 100).toFixed(1);
      s.avgR = (s.pnl / s.trades / 1000).toFixed(2);
      s.avgRisk = (s.avgRisk / s.trades).toFixed(2);
      s.expectancy = (s.winRate / 100 * parseFloat(s.avgR) - (1 - s.winRate / 100)).toFixed(2);
    });

    const byType = {};
    filteredTrades.forEach(t => {
      const type = t.trade_type || 'Other';
      if (!byType[type]) byType[type] = { trades: 0, pnl: 0, wins: 0, avgRisk: 0, expectancy: 0 };
      byType[type].trades++;
      byType[type].pnl += t.pnl || 0;
      byType[type].avgRisk += (t.qty * t.buy_price * 0.01) || 0;
      if ((t.r_multiple || 0) > 0) byType[type].wins++;
    });
    Object.keys(byType).forEach(k => {
      const s = byType[k];
      s.winRate = ((s.wins / s.trades) * 100).toFixed(1);
      s.avgR = (s.pnl / s.trades / 1000).toFixed(2);
      s.avgRisk = (s.avgRisk / s.trades).toFixed(2);
      s.expectancy = (s.winRate / 100 * parseFloat(s.avgR) - (1 - s.winRate / 100)).toFixed(2);
    });

    const byHour = {};
    filteredTrades.forEach(t => {
      const hour = new Date(t.buy_timestamp).getHours();
      if (!byHour[hour]) byHour[hour] = { trades: 0, pnl: 0, wins: 0 };
      byHour[hour].trades++;
      byHour[hour].pnl += t.pnl || 0;
      if ((t.r_multiple || 0) > 0) byHour[hour].wins++;
    });
    Object.keys(byHour).forEach(h => {
      const s = byHour[h];
      s.winRate = ((s.wins / s.trades) * 100).toFixed(1);
      s.avgR = (s.pnl / s.trades / 1000).toFixed(2);
    });

    const byDayOfWeek = {};
    filteredTrades.forEach(t => {
      const day = new Date(t.buy_timestamp).getDay();
      if (!byDayOfWeek[day]) byDayOfWeek[day] = { trades: 0, pnl: 0, wins: 0 };
      byDayOfWeek[day].trades++;
      byDayOfWeek[day].pnl += t.pnl || 0;
      if ((t.r_multiple || 0) > 0) byDayOfWeek[day].wins++;
    });
    Object.keys(byDayOfWeek).forEach(d => {
      const s = byDayOfWeek[d];
      s.winRate = ((s.wins / s.trades) * 100).toFixed(1);
      s.avgR = (s.pnl / s.trades / 1000).toFixed(2);
    });

    const sortedPnL = filteredTrades.map(t => t.pnl || 0).sort((a, b) => a - b);
    const maxDrawdown = sortedPnL.length > 1 ? Math.min(...sortedPnL.slice(0, -1).reduce((drawdown, pnl, i) => {
      const peak = Math.max(...sortedPnL.slice(0, i + 1));
      return Math.min(drawdown, pnl - peak);
    }, 0), 0) : 0;
    const sharpe = totalPnl / Math.sqrt(totalTrades) || 0;
    const avgRiskReward = filteredTrades.reduce((sum, t) => sum + ((t.target || 0) - (t.buy_price || 0)) / ((t.buy_price || 0) - (t.stop || 0)) || 0, 0) / totalTrades || 0;
    const maxConsecutiveWins = computeConsecutive(filteredTrades, true);
    const maxConsecutiveLosses = computeConsecutive(filteredTrades, false);

    const behavioral = {
      overconfidence: highConfidenceWinRate(filteredTrades) < lowConfidenceWinRate(filteredTrades) ? `Potential overconfidence: High confidence trades win ${highConfidenceWinRate(filteredTrades).toFixed(1)}% vs. low: ${lowConfidenceWinRate(filteredTrades).toFixed(1)}%` : '',
      ruleBreakImpact: ruleBreakImpact(filteredTrades),
    };

    const equityCurve = computeEquityCurve(filteredTrades);
    const heatmapPnL = computeHeatmapPnL(filteredTrades);

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
      byDayOfWeek,
      maxDrawdown,
      sharpe,
      avgRiskReward,
      maxConsecutiveWins,
      maxConsecutiveLosses,
      behavioral,
      equityCurve,
      heatmapPnL,
    };
  };

  const computeConsecutive = (trades, isWin) => {
    let max = 0, current = 0;
    trades.forEach(t => {
      if ((t.r_multiple > 0) === isWin) {
        current++;
        max = Math.max(max, current);
      } else {
        current = 0;
      }
    });
    return max;
  };

  const highConfidenceWinRate = (trades) => {
    const high = trades.filter(t => (t.confidence || 0) > 3);
    return high.length ? (high.filter(t => t.r_multiple > 0).length / high.length) * 100 : 0;
  };

  const lowConfidenceWinRate = (trades) => {
    const low = trades.filter(t => (t.confidence || 0) <= 3);
    return low.length ? (low.filter(t => t.r_multiple > 0).length / low.length) * 100 : 0;
  };

  const ruleBreakImpact = (trades) => {
    const broken = trades.filter(t => t.rule_adherence?.some(ra => !ra.followed));
    const followed = trades.filter(t => t.rule_adherence?.every(ra => ra.followed));
    const brokenWinRate = broken.length ? (broken.filter(t => t.r_multiple > 0).length / broken.length) * 100 : 0;
    const followedWinRate = followed.length ? (followed.filter(t => t.r_multiple > 0).length / followed.length) * 100 : 0;
    return `Win rate when rules broken: ${brokenWinRate.toFixed(1)}% vs. followed: ${followedWinRate.toFixed(1)}%`;
  };

  const computeEquityCurve = (trades) => {
    const sorted = trades.sort((a, b) => new Date(a.buy_timestamp) - new Date(b.buy_timestamp));
    let cumulative = 0;
    return sorted.map(t => {
      cumulative += t.pnl || 0;
      return { date: t.buy_timestamp.slice(0, 10), pnl: cumulative };
    });
  };

  const computeHeatmapPnL = (trades) => {
    const heatmapData = [];
    for (let day = 0; day < 7; day++) {
      const row = [];
      for (let hour = 0; hour < 24; hour++) {
        const value = trades
          .filter(t => new Date(t.buy_timestamp).getDay() === day && new Date(t.buy_timestamp).getHours() === hour)
          .reduce((sum, t) => sum + (t.pnl || 0), 0);
        row.push(value);
      }
      heatmapData.push(row);
    }
    return heatmapData;
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    const filtered = applyFilters(trades);
    setAnalyticsData(computeAnalytics(filtered));
  }, [trades, filters]);

  if (loading) return <div className="p-6 text-center">Loading analytics...</div>;
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>;

  const { totalTrades, totalPnl, winRate, avgR, longPnl, shortPnl, byStrategy, byRule, byType, byHour, byDayOfWeek, maxDrawdown, sharpe, avgRiskReward, maxConsecutiveWins, maxConsecutiveLosses, behavioral, equityCurve, heatmapPnL } = analyticsData;

  const heatmapXLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const heatmapYLabels = Array.from({ length: 24 }, (_, i) => `${i}:00`);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-gray-100 to-blue-100 p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-4xl font-bold text-gray-800">Analytics Dashboard</h1>
          <button onClick={() => navigate('/dashboard')} className="bg-blue-500 text-white px-6 py-2 rounded-lg shadow-md hover:bg-blue-600 transition">
            Return to Dashboard
          </button>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
          <h2 className="text-xl font-bold mb-4">Filters</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Start Date</label>
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) => handleFilterChange('startDate', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">End Date</label>
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) => handleFilterChange('endDate', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Start Time</label>
              <input
                type="time"
                value={filters.startTime}
                onChange={(e) => handleFilterChange('startTime', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">End Time</label>
              <input
                type="time"
                value={filters.endTime}
                onChange={(e) => handleFilterChange('endTime', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Strategy</label>
              <select
                value={filters.strategyId}
                onChange={(e) => handleFilterChange('strategyId', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              >
                <option value="">All Strategies</option>
                {strategies.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Trade Type</label>
              <select
                value={filters.tradeType}
                onChange={(e) => handleFilterChange('tradeType', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              >
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
              <label className="block text-sm font-medium text-gray-700">Direction</label>
              <select
                value={filters.direction}
                onChange={(e) => handleFilterChange('direction', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              >
                <option value="All">All</option>
                <option value="Long">Long</option>
                <option value="Short">Short</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Rule Adherence</label>
              <select
                value={filters.followed}
                onChange={(e) => handleFilterChange('followed', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              >
                <option value="All">All</option>
                <option value="Followed">Followed</option>
                <option value="Broken">Broken</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Confidence Min</label>
              <input
                type="number"
                min="1"
                max="5"
                value={filters.confidenceMin}
                onChange={(e) => handleFilterChange('confidenceMin', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Confidence Max</label>
              <input
                type="number"
                min="1"
                max="5"
                value={filters.confidenceMax}
                onChange={(e) => handleFilterChange('confidenceMax', e.target.value)}
                className="w-full border p-2 rounded focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
          <h2 className="text-xl font-bold mb-4">Overall Summary</h2>
          {totalTrades === 0 ? (
            <p className="text-gray-600">No trades available. Add trades via the Dashboard to see analytics.</p>
          ) : (
            <>
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
                <h3 className="text-lg font-bold">Risk Metrics</h3>
                <p>Max Drawdown: ${maxDrawdown.toFixed(2)}</p>
                <p>Sharpe Ratio: {sharpe.toFixed(2)}</p>
                <p>Avg Risk/Reward: {avgRiskReward.toFixed(2)}</p>
                <p>Max Consecutive Wins: {maxConsecutiveWins}</p>
                <p>Max Consecutive Losses: {maxConsecutiveLosses}</p>
              </div>
              <div className="mt-4">
                <h3 className="text-lg font-bold">Behavioral Insights</h3>
                <p>{behavioral.overconfidence || 'No overconfidence detected'}</p>
                <p>{behavioral.ruleBreakImpact}</p>
              </div>
            </>
          )}
        </div>

        {totalTrades > 0 && (
          <>
            <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
              <h2 className="text-xl font-bold mb-4">Equity Curve</h2>
              <LineChart width={600} height={300} data={equityCurve} className="mx-auto">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="pnl" stroke="#8884d8" />
              </LineChart>
            </div>

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
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Risk</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expectancy</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Object.entries(byStrategy).map(([name, stats]) => (
                    <tr key={name}>
                      <td className="px-6 py-4 whitespace-nowrap">{name}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.trades}</td>
                      <td className="px-6 py-4 whitespace-nowrap">${stats.pnl.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.winRate}%</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.avgR}</td>
                      <td className="px-6 py-4 whitespace-nowrap">${stats.avgRisk}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.expectancy}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
              <h2 className="text-xl font-bold mb-4">By Rule (Followed vs. Broken)</h2>
              <p className="mb-4 text-sm text-gray-600">Aggregated across strategies; select a strategy filter for specifics.</p>
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rule Key</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trades</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Win Rate</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg R</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Risk</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expectancy</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Object.entries(byRule).map(([key, stats]) => (
                    <tr key={key}>
                      <td className="px-6 py-4 whitespace-nowrap">{key}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.trades}</td>
                      <td className="px-6 py-4 whitespace-nowrap">${stats.pnl.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.winRate}%</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.avgR}</td>
                      <td className="px-6 py-4 whitespace-nowrap">${stats.avgRisk}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.expectancy}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
              <h2 className="text-xl font-bold mb-4">By Trade Type</h2>
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trades</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Win Rate</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg R</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Risk</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expectancy</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Object.entries(byType).map(([type, stats]) => (
                    <tr key={type}>
                      <td className="px-6 py-4 whitespace-nowrap">{type}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.trades}</td>
                      <td className="px-6 py-4 whitespace-nowrap">${stats.pnl.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.winRate}%</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.avgR}</td>
                      <td className="px-6 py-4 whitespace-nowrap">${stats.avgRisk}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{stats.expectancy}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
              <h2 className="text-xl font-bold mb-4">By Hour of Day</h2>
              <BarChart
                width={600}
                height={300}
                data={Object.entries(byHour).map(([h, s]) => ({ hour: h, pnl: s.pnl }))}
                className="mx-auto"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="pnl" fill="#8884d8" />
              </BarChart>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
              <h2 className="text-xl font-bold mb-4">By Day of Week</h2>
              <BarChart
                width={600}
                height={300}
                data={Object.entries(byDayOfWeek).map(([d, s]) => ({ day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d], pnl: s.pnl }))}
                className="mx-auto"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="pnl" fill="#82ca9d" />
              </BarChart>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-200 mb-6">
              <h2 className="text-xl font-bold mb-4">PnL Heatmap (Day vs Hour)</h2>
              <p className="mb-4 text-sm text-gray-600">Hover over cells to see PnL values. Green indicates profits, red indicates losses.</p>
              <HeatMapGrid
                data={heatmapPnL}
                xLabels={heatmapXLabels}
                yLabels={heatmapYLabels}
                cellStyle={(background, value, min, max, data, x, y) => ({
                  background: value > 0
                    ? `rgba(0, 255, 0, ${Math.min(Math.abs(value) / 1000, 1)})`
                    : value < 0
                    ? `rgba(255, 0, 0, ${Math.min(Math.abs(value) / 1000, 1)})`
                    : 'rgba(200, 200, 200, 0.5)',
                  fontSize: '12px',
                  color: '#000',
                  border: '1px solid #e5e7eb',
                  padding: '4px',
                })}
                cellRender={(x, y, value) => (
                  <div title={`Day: ${heatmapXLabels[x]}, Hour: ${heatmapYLabels[y]}, PnL: $${value.toFixed(2)}`}>
                    {value.toFixed(0)}
                  </div>
                )}
                xLabelsStyle={() => ({
                  fontSize: '12px',
                  color: '#4b5563',
                  fontWeight: 'bold',
                })}
                yLabelsStyle={() => ({
                  fontSize: '12px',
                  color: '#4b5563',
                  fontWeight: 'bold',
                })}
                square
              />
            </div>
          </>
        )}

        <div className="flex gap-4">
          <button
            onClick={() => {/* TODO: Implement CSV export with /export endpoint */}}
            className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600 transition"
          >
            Export Summary (CSV)
          </button>
          <button
            onClick={() => {/* TODO: Implement PDF export with /export endpoint */}}
            className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600 transition"
          >
            Export Report (PDF)
          </button>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default Analytics;