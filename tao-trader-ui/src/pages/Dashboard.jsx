import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import forgeLogo from '../assets/forgelogo.png';

function Dashboard() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPlaybookModal, setShowPlaybookModal] = useState(false);
  const [showStrategyEditModal, setShowStrategyEditModal] = useState(false);
  const [editStrategy, setEditStrategy] = useState(null); // For editing existing strategy (null for new)
  const [strategyForm, setStrategyForm] = useState({ name: '', description: '' });
  const [entryRules, setEntryRules] = useState(['']); // Dynamic entry rules (start with one empty)
  const [exitRules, setExitRules] = useState(['']); // Dynamic exit rules (start with one empty)
  const [strategies, setStrategies] = useState([]);
  const [editIndex, setEditIndex] = useState(null);
  const [importDates, setImportDates] = useState({ start_date: '', end_date: '' });
  const [ibkrForm, setIBKRForm] = useState({ api_token: '', account_id: '' });
  const [rules, setRules] = useState([]);
  const [ruleAdherence, setRuleAdherence] = useState({});
  const [formData, setFormData] = useState({
    instrument: '',
    buy_timestamp: '',
    sell_timestamp: '',
    buy_price: '',
    sell_price: '',
    qty: '',
    strategy_id: '',
    rule_adherence: [],
    confidence: '',
    target: '',
    stop: '',
    notes: '',
    goals: '',
    preparedness: '',
    what_i_learned: '',
    changes_needed: '',
    direction: 'Long',
    trade_type: 'Stock',
  });
  const navigate = useNavigate();
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
      console.log('Fetching trades with token:', token.substring(0, 10) + '...');
      const res = await fetch('https://taojournal-production.up.railway.app/trades', {
        headers: { Authorization: `Bearer ${token}` },
      });
      console.log('Trades fetch response status:', res.status);
      const text = await res.text();
      console.log('Trades fetch response body:', text);
      if (res.ok) {
        try {
          const data = JSON.parse(text);
          setTrades(Array.isArray(data) ? data : []);
        } catch (parseErr) {
          console.error('JSON parse error:', parseErr);
          setError('Invalid server response.');
        }
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token'); // Clear invalid token
        navigate('/login');
      } else {
        setError(`Failed to load trades: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Trades fetch error:', err);
      setError('Error fetching trades. Please check your connection or login again.');
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

  const fetchRules = async (strategy_id) => {
    try {
      const res = await fetch(`https://taojournal-production.up.railway.app/rules/${strategy_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const fetchedRules = await res.json();
        setRules(fetchedRules);
        // Default to true (followed) for new trades
        setRuleAdherence(fetchedRules.reduce((acc, rule) => ({ ...acc, [rule.id]: true }), {}));
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      }
    } catch (err) {
      console.error('Rules fetch error:', err);
    }
  };

  const fetchTradeRules = async (trade_id) => {
    try {
      const res = await fetch(`https://taojournal-production.up.railway.app/trade_rules/${trade_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const tradeRules = await res.json();
        setRuleAdherence(tradeRules.reduce((acc, rule) => ({ ...acc, [rule.id]: rule.followed }), {}));
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      }
    } catch (err) {
      console.error('Trade rules fetch error:', err);
    }
  };

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleStrategyChange = async (e) => {
    const strategy_id = e.target.value;
    setFormData({ ...formData, strategy_id });
    if (strategy_id) {
      await fetchRules(strategy_id);
    } else {
      setRules([]);
      setRuleAdherence({});
    }
  };

  const handleRuleAdherenceChange = (rule_id) => {
    setRuleAdherence({ ...ruleAdherence, [rule_id]: !ruleAdherence[rule_id] });
  };

  const handleStrategyInputChange = (e) => {
    setStrategyForm({ ...strategyForm, [e.target.name]: e.target.value });
  };

  const handleEntryRuleChange = (index, value) => {
    const newRules = [...entryRules];
    newRules[index] = value;
    setEntryRules(newRules);
  };

  const addEntryRule = () => {
    setEntryRules([...entryRules, '']);
  };

  const removeEntryRule = (index) => {
    const newRules = entryRules.filter((_, i) => i !== index);
    setEntryRules(newRules.length > 0 ? newRules : ['']);
  };

  const handleExitRuleChange = (index, value) => {
    const newRules = [...exitRules];
    newRules[index] = value;
    setExitRules(newRules);
  };

  const addExitRule = () => {
    setExitRules([...exitRules, '']);
  };

  const removeExitRule = (index) => {
    const newRules = exitRules.filter((_, i) => i !== index);
    setExitRules(newRules.length > 0 ? newRules : ['']);
  };

  const handleCreateOrUpdateStrategy = async (e) => {
    e.preventDefault();
    const method = editStrategy ? 'PUT' : 'POST';
    const url = editStrategy ? `https://taojournal-production.up.railway.app/strategies/${editStrategy.id}` : 'https://taojournal-production.up.railway.app/strategies';
    try {
      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(strategyForm),
      });
      if (res.ok) {
        const savedStrategy = await res.json();
        // Now add rules if any
        for (const ruleText of entryRules.filter(r => r.trim())) {
          await fetch('https://taojournal-production.up.railway.app/rules', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ strategy_id: savedStrategy.id, rule_type: 'entry', rule_text: ruleText }),
          });
        }
        for (const ruleText of exitRules.filter(r => r.trim())) {
          await fetch('https://taojournal-production.up.railway.app/rules', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ strategy_id: savedStrategy.id, rule_type: 'exit', rule_text: ruleText }),
          });
        }
        setShowStrategyEditModal(false);
        setStrategyForm({ name: '', description: '' });
        setEntryRules(['']);
        setExitRules(['']);
        setEditStrategy(null);
        fetchStrategies();
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError('Failed to save strategy.');
      }
    } catch (err) {
      console.error('Error saving strategy:', err);
      setError('Error saving strategy.');
    }
  };

  const openStrategyEdit = async (strategy) => {
    setShowPlaybookModal(false);
    setShowStrategyEditModal(true);
    setEditStrategy(strategy);
    setStrategyForm({ name: strategy.name, description: strategy.description });
    const res = await fetch(`https://taojournal-production.up.railway.app/rules/${strategy.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const rulesData = await res.json();
      setEntryRules(rulesData.filter(r => r.rule_type === 'entry').map(r => r.rule_text) || ['']);
      setExitRules(rulesData.filter(r => r.rule_type === 'exit').map(r => r.rule_text) || ['']);
    } else if (res.status === 401) {
      console.log('Unauthorized - redirecting to login');
      localStorage.removeItem('token');
      navigate('/login');
    }
  };

  const handleDeleteStrategy = async (id) => {
    if (window.confirm('Delete this strategy?')) {
      try {
        const res = await fetch(`https://taojournal-production.up.railway.app/strategies/${id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          fetchStrategies();
        } else if (res.status === 401) {
          console.log('Unauthorized - redirecting to login');
          localStorage.removeItem('token');
          navigate('/login');
        } else {
          setError('Failed to delete strategy.');
        }
      } catch (err) {
        console.error('Error deleting strategy:', err);
        setError('Error deleting strategy.');
      }
    }
  };

  const handleAddTrade = async (e) => {
    e.preventDefault();
    try {
      const rule_adherence = Object.keys(ruleAdherence).map(rule_id => ({
        rule_id: parseInt(rule_id),
        followed: ruleAdherence[rule_id]
      }));
      const res = await fetch('https://taojournal-production.up.railway.app/trades', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ ...formData, rule_adherence }),
      });
      if (res.ok) {
        setShowNewModal(false);
        fetchTrades();
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError('Failed to add trade.');
      }
    } catch (err) {
      console.error('Error adding trade:', err);
      setError('Error adding trade.');
    }
  };

  const handleEditTrade = async (e) => {
    e.preventDefault();
    try {
      const rule_adherence = Object.keys(ruleAdherence).map(rule_id => ({
        rule_id: parseInt(rule_id),
        followed: ruleAdherence[rule_id]
      }));
      const res = await fetch(`https://taojournal-production.up.railway.app/trades/${trades[editIndex].id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ ...formData, rule_adherence }),
      });
      if (res.ok) {
        setShowEditModal(false);
        fetchTrades();
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError('Failed to update trade.');
      }
    } catch (err) {
      console.error('Error updating trade:', err);
      setError('Error updating trade.');
    }
  };

  const openEditModal = async (index) => {
    const trade = trades[index];
    setEditIndex(index);
    setFormData({
      ...trade,
      buy_timestamp: trade.buy_timestamp.slice(0, 16),
      sell_timestamp: trade.sell_timestamp.slice(0, 16),
    });
    if (trade.strategy_id) {
      await fetchRules(trade.strategy_id);
      await fetchTradeRules(trade.id); // This sets adherence based on saved data
    }
    setShowEditModal(true);
  };

  const handleDeleteTrade = async (id) => {
    if (window.confirm('Delete this trade?')) {
      try {
        const res = await fetch(`https://taojournal-production.up.railway.app/trades/${id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          fetchTrades();
        } else if (res.status === 401) {
          console.log('Unauthorized - redirecting to login');
          localStorage.removeItem('token');
          navigate('/login');
        } else {
          setError('Failed to delete trade.');
        }
      } catch (err) {
        console.error('Error deleting trade:', err);
        setError('Error deleting trade.');
      }
    }
  };

  const handleUploadCSV = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('https://taojournal-production.up.railway.app/import_csv', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (res.ok) {
        fetchTrades();
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError('Failed to import CSV.');
      }
    } catch (err) {
      console.error('Error importing CSV:', err);
      setError('Error importing CSV.');
    }
  };

  const handleUploadImage = async (id, e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`https://taojournal-production.up.railway.app/trades/${id}/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (res.ok) {
        fetchTrades();
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError('Failed to upload image.');
      }
    } catch (err) {
      console.error('Error uploading image:', err);
      setError('Error uploading image.');
    }
  };

  const handleViewImage = (id) => {
    window.open(`https://taojournal-production.up.railway.app/trades/${id}/image?token=${token}`, '_blank');
  };

  const handleExport = async (type) => {
    try {
      const res = await fetch(`https://taojournal-production.up.railway.app/export/${type}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trades.${type}`;
        a.click();
      } else if (res.status === 401) {
        console.log('Unauthorized - redirecting to login');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError(`Failed to export ${type.toUpperCase()}.`);
      }
    } catch (err) {
      console.error('Error exporting:', err);
      setError('Error exporting.');
    }
  };

  if (loading) return <p className="text-center text-gray-600 mt-10">Loading your trades...</p>;

  if (error) return (
    <div className="text-center text-red-500 mt-10">
      {error}
      <button onClick={fetchTrades} className="ml-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Retry</button>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-100 to-blue-100 p-6">
      <div className="flex justify-center mb-6">
        <img src={forgeLogo} alt="StrategyForge Journal Logo" className="h-20 w-auto rounded shadow-md" />
      </div>
      <h1 className="text-4xl font-bold text-center mb-8 text-gray-800">Your StrategyForge Journal Dashboard</h1>

      <div className="flex flex-wrap justify-center gap-4 mb-8">
        <button onClick={() => setShowNewModal(true)} className="bg-green-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-green-600 transition flex items-center">
          <span className="mr-2">➕</span> Add New Trade
        </button>
        <label className="bg-blue-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-blue-600 transition cursor-pointer flex items-center">
          <span className="mr-2">📥</span> Upload Broker CSV
          <input type="file" accept=".csv" onChange={handleUploadCSV} className="hidden" />
        </label>
        <button className="bg-blue-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-blue-600 transition flex items-center">
          <span className="mr-2">🔗</span> Connect to Broker
        </button>
        <button onClick={() => setShowPlaybookModal(true)} className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600 transition flex items-center">
          <span className="mr-2">📖</span> Playbook
        </button>
        <button onClick={() => handleExport('excel')} className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600 transition flex items-center">
          <span className="mr-2">📤</span> Export to Excel
        </button>
        <button onClick={() => handleExport('pdf')} className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600 transition flex items-center">
          <span className="mr-2">📄</span> Export to PDF
        </button>
        <button onClick={() => navigate('/analytics')} className="bg-indigo-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-indigo-600 transition flex items-center">
          <span className="mr-2">📊</span> View Analytics
        </button>
      </div>

      {trades.length === 0 ? (
        <div className="bg-white p-8 rounded-lg shadow-xl border border-gray-200 max-w-2xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-800">Welcome to StrategyForge Journal!</h2>
          <p className="text-gray-600 mb-6">It looks like you don't have any trades yet. Get started by adding your first trade or uploading a CSV from your broker.</p>
          <div className="flex justify-center gap-4">
            <button onClick={() => setShowNewModal(true)} className="bg-green-500 text-white px-6 py-3 rounded-lg hover:bg-green-600">Add Manual Trade</button>
            <label className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 cursor-pointer">
              Upload CSV
              <input type="file" accept=".csv" onChange={handleUploadCSV} className="hidden" />
            </label>
          </div>
          <p className="text-sm text-gray-500 mt-6">StrategyForge Journal helps you track, analyze, and improve your trading journey—better than the rest.</p>
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg shadow-xl border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instrument</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trade Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Buy Timestamp</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sell Timestamp</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Direction</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Qty</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Buy Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sell Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Strategy</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Target</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stop</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">R-Multiple</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Notes</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Goals</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Preparedness</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">What I Learned</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Changes Needed</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Image</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {trades.map((trade, index) => (
                <tr key={trade.id} className={trade.direction === 'Long' ? 'hover:bg-green-100' : 'hover:bg-red-100'}>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.instrument}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.trade_type}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.buy_timestamp}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.sell_timestamp}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.direction}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.qty}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.buy_price}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.sell_price}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{strategies.find(s => s.id === trade.strategy_id)?.name || ''}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.confidence}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.target}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.stop}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.r_multiple}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.pnl}</td>
                  <td className="px-6 py-4">{trade.notes}</td>
                  <td className="px-6 py-4">{trade.goals}</td>
                  <td className="px-6 py-4">{trade.preparedness}</td>
                  <td className="px-6 py-4">{trade.what_i_learned}</td>
                  <td className="px-6 py-4">{trade.changes_needed}</td>
                  <td className="px-6 py-4">
                    {trade.image_path ? (
                      <button onClick={() => handleViewImage(trade.id)} className="text-blue-600 hover:underline">View Image</button>
                    ) : (
                      <label className="text-blue-600 hover:underline cursor-pointer">
                        Upload Image
                        <input type="file" accept="image/*" onChange={(e) => handleUploadImage(trade.id, e)} className="hidden" />
                      </label>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button onClick={() => openEditModal(index)} className="text-yellow-600 hover:underline mr-3">Edit</button>
                    <button onClick={() => handleDeleteTrade(trade.id)} className="text-red-600 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* New Trade Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-lg overflow-y-auto max-h-[80vh]">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Add New Trade</h2>
            <form onSubmit={handleAddTrade} className="space-y-4">
              <input name="instrument" placeholder="Instrument (e.g., AAPL)" value={formData.instrument} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <select name="trade_type" value={formData.trade_type} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none">
                <option value="Stock">Stock</option>
                <option value="Call">Call</option>
                <option value="Put">Put</option>
                <option value="Straddle">Straddle</option>
                <option value="Covered Call">Covered Call</option>
                <option value="Cash Secured Put">Cash Secured Put</option>
                <option value="Other">Other</option>
              </select>
              <input name="buy_timestamp" type="datetime-local" value={formData.buy_timestamp} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <input name="sell_timestamp" type="datetime-local" value={formData.sell_timestamp} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <select name="direction" value={formData.direction} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none">
                <option value="Long">Long</option>
                <option value="Short">Short</option>
              </select>
              <select name="strategy_id" value={formData.strategy_id} onChange={handleStrategyChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none">
                <option value="">Select Strategy</option>
                {strategies.map(strat => (
                  <option key={strat.id} value={strat.id}>{strat.name}</option>
                ))}
              </select>
              {rules.map(rule => (
                <label key={rule.id} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={ruleAdherence[rule.id] !== false} // Default true
                    onChange={() => handleRuleAdherenceChange(rule.id)}
                    className="mr-2"
                  />
                  {rule.rule_type}: {rule.rule_text}
                </label>
              ))}
              <input name="buy_price" placeholder="Buy Price" value={formData.buy_price} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" step="0.01" />
              <input name="sell_price" placeholder="Sell Price" value={formData.sell_price} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" step="0.01" />
              <input name="qty" placeholder="Quantity" value={formData.qty} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" />
              <input name="confidence" placeholder="Confidence (1-5)" value={formData.confidence} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" type="number" min="1" max="5" />
              <input name="target" placeholder="Target Price" value={formData.target} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" type="number" step="0.01" />
              <input name="stop" placeholder="Stop Loss Price" value={formData.stop} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" type="number" step="0.01" />
              <textarea name="notes" placeholder="Notes" value={formData.notes} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <textarea name="goals" placeholder="Goals for this trade" value={formData.goals} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <textarea name="preparedness" placeholder="Preparedness level" value={formData.preparedness} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <textarea name="what_i_learned" placeholder="What I Learned" value={formData.what_i_learned} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <textarea name="changes_needed" placeholder="Changes Needed" value={formData.changes_needed} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <div className="flex justify-end gap-4 mt-6">
                <button type="button" onClick={() => setShowNewModal(false)} className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600">Cancel</button>
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">Add Trade</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Trade Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-lg overflow-y-auto max-h-[80vh]">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Edit Trade</h2>
            <form onSubmit={handleEditTrade} className="space-y-4">
              <input name="instrument" placeholder="Instrument (e.g., AAPL)" value={formData.instrument} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <select name="trade_type" value={formData.trade_type} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none">
                <option value="Stock">Stock</option>
                <option value="Call">Call</option>
                <option value="Put">Put</option>
                <option value="Straddle">Straddle</option>
                <option value="Covered Call">Covered Call</option>
                <option value="Cash Secured Put">Cash Secured Put</option>
                <option value="Other">Other</option>
              </select>
              <input name="buy_timestamp" type="datetime-local" value={formData.buy_timestamp} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <input name="sell_timestamp" type="datetime-local" value={formData.sell_timestamp} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <select name="direction" value={formData.direction} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none">
                <option value="Long">Long</option>
                <option value="Short">Short</option>
              </select>
              <select name="strategy_id" value={formData.strategy_id} onChange={handleStrategyChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none">
                <option value="">Select Strategy</option>
                {strategies.map(strat => (
                  <option key={strat.id} value={strat.id}>{strat.name}</option>
                ))}
              </select>
              {rules.map(rule => (
                <label key={rule.id} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={ruleAdherence[rule.id] !== false} // Default true
                    onChange={() => handleRuleAdherenceChange(rule.id)}
                    className="mr-2"
                  />
                  {rule.rule_type}: {rule.rule_text}
                </label>
              ))}
              <input name="buy_price" placeholder="Buy Price" value={formData.buy_price} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" step="0.01" />
              <input name="sell_price" placeholder="Sell Price" value={formData.sell_price} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" step="0.01" />
              <input name="qty" placeholder="Quantity" value={formData.qty} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" />
              <input name="confidence" placeholder="Confidence (1-5)" value={formData.confidence} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" type="number" min="1" max="5" />
              <input name="target" placeholder="Target Price" value={formData.target} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" type="number" step="0.01" />
              <input name="stop" placeholder="Stop Loss Price" value={formData.stop} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" type="number" step="0.01" />
              <textarea name="notes" placeholder="Notes" value={formData.notes} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <textarea name="goals" placeholder="Goals for this trade" value={formData.goals} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <textarea name="preparedness" placeholder="Preparedness level" value={formData.preparedness} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <textarea name="what_i_learned" placeholder="What I Learned" value={formData.what_i_learned} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <textarea name="changes_needed" placeholder="Changes Needed" value={formData.changes_needed} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" rows="3" />
              <div className="flex justify-end gap-4 mt-6">
                <button type="button" onClick={() => setShowEditModal(false)} className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600">Cancel</button>
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Playbook Modal - List Strategies */}
      {showPlaybookModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Playbook</h2>
            <button onClick={() => { setEditStrategy(null); setStrategyForm({ name: '', description: '' }); setEntryRules(['']); setExitRules(['']); setShowPlaybookModal(false); setShowStrategyEditModal(true); }} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 mb-4">Create New Strategy</button>
            <ul className="space-y-2">
              {strategies.map(strat => (
                <li key={strat.id} className="flex justify-between items-center">
                  <span>{strat.name}</span>
                  <div>
                    <button onClick={() => openStrategyEdit(strat)} className="text-yellow-600 hover:underline mr-3">Edit</button>
                    <button onClick={() => handleDeleteStrategy(strat.id)} className="text-red-600 hover:underline">Delete</button>
                  </div>
                </li>
              ))}
            </ul>
            <div className="flex justify-end mt-6">
              <button type="button" onClick={() => setShowPlaybookModal(false)} className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Strategy Edit Modal - Create/Edit Strategy with Dynamic Rules */}
      {showStrategyEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-md overflow-y-auto max-h-[80vh]">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">{editStrategy ? 'Edit Strategy' : 'Create New Strategy'}</h2>
            <form onSubmit={handleCreateOrUpdateStrategy} className="space-y-4">
              <input
                name="name"
                placeholder="Strategy Name (e.g., Breakout)"
                value={strategyForm.name}
                onChange={handleStrategyInputChange}
                className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                required
              />
              <textarea
                name="description"
                placeholder="Description"
                value={strategyForm.description}
                onChange={handleStrategyInputChange}
                className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                rows="3"
              />
              <h3 className="text-lg font-bold">Entry Rules</h3>
              {entryRules.map((rule, index) => (
                <div key={index} className="flex items-center">
                  <input
                    value={rule}
                    onChange={(e) => handleEntryRuleChange(index, e.target.value)}
                    placeholder={`Entry Rule ${index + 1}`}
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                  />
                  <button type="button" onClick={() => removeEntryRule(index)} className="ml-2 text-red-600 hover:underline">-</button>
                </div>
              ))}
              <button type="button" onClick={addEntryRule} className="text-blue-600 hover:underline">+ Add Entry Rule</button>
              <h3 className="text-lg font-bold">Exit Rules</h3>
              {exitRules.map((rule, index) => (
                <div key={index} className="flex items-center">
                  <input
                    value={rule}
                    onChange={(e) => handleExitRuleChange(index, e.target.value)}
                    placeholder={`Exit Rule ${index + 1}`}
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                  />
                  <button type="button" onClick={() => removeExitRule(index)} className="ml-2 text-red-600 hover:underline">-</button>
                </div>
              ))}
              <button type="button" onClick={addExitRule} className="text-blue-600 hover:underline">+ Add Exit Rule</button>
              <div className="flex justify-end gap-4 mt-6">
                <button type="button" onClick={() => { setShowStrategyEditModal(false); setShowPlaybookModal(true); }} className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600">Cancel</button>
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">Save Strategy</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;