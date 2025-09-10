import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import taoLogo from '../assets/tao-logo.jpg';

function Dashboard() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [showEditStrategiesModal, setShowEditStrategiesModal] = useState(false);
  const [showEditStrategyModal, setShowEditStrategyModal] = useState(false);
  const [showConnectBrokerModal, setShowConnectBrokerModal] = useState(false);
  const [editIndex, setEditIndex] = useState(null);
  const [brokerType, setBrokerType] = useState('');
  const [strategies, setStrategies] = useState([]);
  const [rules, setRules] = useState([]);
  const [ruleAdherence, setRuleAdherence] = useState({});
  const [entryRules, setEntryRules] = useState(['']);
  const [exitRules, setExitRules] = useState(['']);
  const [editStrategy, setEditStrategy] = useState(null);
  const [editEntryRules, setEditEntryRules] = useState(['']);
  const [editExitRules, setEditExitRules] = useState(['']);
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
  const [strategyForm, setStrategyForm] = useState({ name: '', description: '' });

  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
      const res = await fetch(`${API_BASE_URL}/trades`, {
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
      } else {
        setError('Failed to load trades.');
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
      const res = await fetch(`${API_BASE_URL}/strategies`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setStrategies(await res.json());
      }
    } catch (err) {
      console.error('Strategies fetch error:', err);
    }
  };

  const fetchRules = async (strategy_id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/rules/${strategy_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const fetchedRules = await res.json();
        setRules(fetchedRules);
        setRuleAdherence(fetchedRules.reduce((acc, rule) => ({ ...acc, [rule.id]: false }), {}));
      }
    } catch (err) {
      console.error('Rules fetch error:', err);
    }
  };

  const fetchTradeRules = async (trade_id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/trade_rules/${trade_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const tradeRules = await res.json();
        setRuleAdherence(tradeRules.reduce((acc, rule) => ({ ...acc, [rule.id]: rule.followed }), {}));
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

  const addRuleField = (type, setRules, rules) => {
    setRules([...rules, '']);
  };

  const removeRuleField = (type, index, setRules, rules) => {
    setRules(rules.filter((_, i) => i !== index));
  };

  const updateRule = (type, index, value, setRules, rules) => {
    const newRules = [...rules];
    newRules[index] = value;
    setRules(newRules);
  };

  const handleAddTrade = async (e) => {
    e.preventDefault();
    try {
      const rule_adherence = Object.keys(ruleAdherence).map(rule_id => ({
        rule_id: parseInt(rule_id),
        followed: ruleAdherence[rule_id]
      }));
      const res = await fetch(`${API_BASE_URL}/trades`, {
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
      } else {
        setError('Failed to add trade.');
      }
    } catch (err) {
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
      const res = await fetch(`${API_BASE_URL}/trades/${editIndex}`, {
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
      } else {
        setError('Failed to update trade.');
      }
    } catch (err) {
      setError('Error updating trade.');
    }
  };

  const handleCreateStrategy = async (e) => {
    e.preventDefault();
    try {
      const entry_rules = entryRules.filter((r) => r);
      const exit_rules = exitRules.filter((r) => r);
      const res = await fetch(`${API_BASE_URL}/strategies`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ ...strategyForm, entry_rules, exit_rules }),
      });
      if (res.ok) {
        setShowStrategyModal(false);
        setStrategyForm({ name: '', description: '' });
        setEntryRules(['']);
        setExitRules(['']);
        fetchStrategies();
      } else {
        setError('Failed to create strategy.');
      }
    } catch (err) {
      setError('Error creating strategy.');
    }
  };

  const handleEditStrategy = async (e) => {
    e.preventDefault();
    try {
      const entry_rules = editEntryRules.filter((r) => r);
      const exit_rules = editExitRules.filter((r) => r);
      const res = await fetch(`${API_BASE_URL}/strategies/${editStrategy.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: strategyForm.name,
          description: strategyForm.description,
          entry_rules,
          exit_rules,
        }),
      });
      if (res.ok) {
        setShowEditStrategyModal(false);
        setEditStrategy(null);
        setStrategyForm({ name: '', description: '' });
        setEditEntryRules(['']);
        setEditExitRules(['']);
        fetchStrategies();
      } else {
        setError('Failed to update strategy.');
      }
    } catch (err) {
      setError('Error updating strategy.');
    }
  };

  const handleDeleteStrategy = async () => {
    if (!window.confirm('Are you sure you want to delete this strategy?')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/strategies/${editStrategy.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setShowEditStrategyModal(false);
        setEditStrategy(null);
        fetchStrategies();
      } else {
        setError('Failed to delete strategy.');
      }
    } catch (err) {
      setError('Error deleting strategy.');
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
      await fetchTradeRules(index);
    }
    setShowEditModal(true);
  };

  const handleDeleteTrade = async (index) => {
    if (!window.confirm('Delete this trade?')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/trades/${index}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        fetchTrades();
      } else {
        setError('Failed to delete trade.');
      }
    } catch (err) {
      setError('Error deleting trade.');
    }
  };

  const handleUploadCSV = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API_BASE_URL}/import_csv`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (res.ok) {
        fetchTrades();
      } else {
        setError('Failed to import CSV.');
      }
    } catch (err) {
      setError('Error importing CSV.');
    }
  };

  const handleConnectBroker = async (e) => {
    e.preventDefault();
    const form = e.target;
    let creds = {};
    if (brokerType === 'ibkr') {
      creds = {
        host: form.host.value,
        port: parseInt(form.port.value),
        client_id: parseInt(form.client_id.value),
      };
    } else if (brokerType === 'schwab') {
      creds = {
        api_token: form.api_token.value,
        account_id: form.account_id.value,
      };
    }
    try {
      const res = await fetch(`${API_BASE_URL}/brokers`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ broker_type: brokerType, creds }),
      });
      if (res.ok) {
        setShowConnectBrokerModal(false);
        setBrokerType('');
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to connect broker.');
      }
    } catch (err) {
      setError('Error connecting broker.');
    }
  };

  const handleImportFromBroker = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/import_from_broker`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        fetchTrades();
      } else {
        const err = await res.json();
        setError(err.detail || 'Error importing. You must first connect a supported broker, if your broker is not supported download your trade history to a csv file and import the csv through upload broker csv button.');
      }
    } catch (err) {
      setError('Error importing from broker.');
    }
  };

  const handleUploadImage = async (index, e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API_BASE_URL}/trades/${index}/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (res.ok) {
        fetchTrades();
      } else {
        setError('Failed to upload image.');
      }
    } catch (err) {
      setError('Error uploading image.');
    }
  };

  const handleViewImage = (index) => {
    window.open(`${API_BASE_URL}/trades/${index}/image?token=${token}`, '_blank');
  };

  const handleExport = async (type) => {
    try {
      const res = await fetch(`${API_BASE_URL}/export/${type}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trades.${type}`;
        a.click();
      } else {
        setError(`Failed to export ${type.toUpperCase()}.`);
      }
    } catch (err) {
      setError('Error exporting.');
    }
  };

  const handleBrokerTypeChange = (e) => {
    setBrokerType(e.target.value);
  };

  const loadEditStrategy = async (strategy) => {
    setEditStrategy(strategy);
    setShowEditStrategiesModal(false);
    setShowEditStrategyModal(true);
    try {
      const res = await fetch(`${API_BASE_URL}/rules/${strategy.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const rules = await res.json();
        setEditEntryRules(rules.filter((r) => r.rule_type === 'entry').map((r) => r.rule_text));
        setEditExitRules(rules.filter((r) => r.rule_type === 'exit').map((r) => r.rule_text));
        if (!rules.filter((r) => r.rule_type === 'entry').length) setEditEntryRules(['']);
        if (!rules.filter((r) => r.rule_type === 'exit').length) setEditExitRules(['']);
        setStrategyForm({ name: strategy.name, description: strategy.description });
      } else {
        setError('Failed to fetch rules.');
      }
    } catch (err) {
      setError('Error fetching rules.');
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
        <img src={taoLogo} alt="Tao Trader Logo" className="h-20 w-auto rounded shadow-md" />
      </div>
      <h1 className="text-4xl font-bold text-center mb-8 text-gray-800">Your Tao Trader Dashboard</h1>
      <div className="flex flex-wrap justify-center gap-4 mb-8">
        <button onClick={() => setShowNewModal(true)} className="bg-green-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-green-600 transition flex items-center">
          <span className="mr-2">➕</span> Add New Trade
        </button>
        <label className="bg-blue-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-blue-600 transition cursor-pointer flex items-center">
          <span className="mr-2">📥</span> Upload Broker CSV
          <input type="file" accept=".csv" onChange={handleUploadCSV} className="hidden" />
        </label>
        <button onClick={() => setShowConnectBrokerModal(true)} className="bg-blue-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-blue-600 transition flex items-center">
          <span className="mr-2">🔗</span> Connect Broker
        </button>
        <button onClick={handleImportFromBroker} className="bg-blue-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-blue-600 transition flex items-center">
          <span className="mr-2">📥</span> Import from Broker
        </button>
        <button onClick={() => setShowStrategyModal(true)} className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600 transition flex items-center">
          <span className="mr-2">📋</span> Add Strategy
        </button>
        <button onClick={() => setShowEditStrategiesModal(true)} className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600 transition flex items-center">
          <span className="mr-2">✏️</span> Edit Strategies
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
          <h2 className="text-2xl font-bold mb-4 text-gray-800">Welcome to Tao Trader!</h2>
          <p className="text-gray-600 mb-6">It looks like you don't have any trades yet. Get started by adding your first trade or uploading a CSV from your broker.</p>
          <div className="flex justify-center gap-4">
            <button onClick={() => setShowNewModal(true)} className="bg-green-500 text-white px-6 py-3 rounded-lg hover:bg-green-600">Add Manual Trade</button>
            <label className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 cursor-pointer">
              Upload CSV
              <input type="file" accept=".csv" onChange={handleUploadCSV} className="hidden" />
            </label>
          </div>
          <p className="text-sm text-gray-500 mt-6">Tao Trader helps you track, analyze, and improve your trading journey—better than the rest.</p>
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
                <tr key={index} className={trade.direction === 'Long' ? 'hover:bg-green-100' : 'hover:bg-red-100'}>
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
                      <button onClick={() => handleViewImage(index)} className="text-blue-600 hover:underline">View Image</button>
                    ) : (
                      <label className="text-blue-600 hover:underline cursor-pointer">
                        Upload Image
                        <input type="file" accept="image/*" onChange={(e) => handleUploadImage(index, e)} className="hidden" />
                      </label>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button onClick={() => openEditModal(index)} className="text-yellow-600 hover:underline mr-3">Edit</button>
                    <button onClick={() => handleDeleteTrade(index)} className="text-red-600 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {/* Connect Broker Modal */}
      {showConnectBrokerModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Connect Broker</h2>
            <form onSubmit={handleConnectBroker} className="space-y-4">
              <select
                value={brokerType}
                onChange={handleBrokerTypeChange}
                className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                required
              >
                <option value="">Select Broker</option>
                <option value="ibkr">IBKR</option>
                <option value="schwab">Schwab</option>
              </select>
              {brokerType === 'ibkr' && (
                <>
                  <input
                    name="host"
                    placeholder="Host (e.g., 127.0.0.1)"
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                    defaultValue="127.0.0.1"
                    required
                  />
                  <input
                    name="port"
                    type="number"
                    placeholder="Port (e.g., 7497)"
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                    defaultValue="7497"
                    required
                  />
                  <input
                    name="client_id"
                    type="number"
                    placeholder="Client ID"
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                    required
                  />
                </>
              )}
              {brokerType === 'schwab' && (
                <>
                  <input
                    name="api_token"
                    placeholder="API Token"
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                    required
                  />
                  <input
                    name="account_id"
                    placeholder="Account ID"
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                    required
                  />
                </>
              )}
              <div className="flex justify-end gap-4 mt-6">
                <button type="button" onClick={() => setShowConnectBrokerModal(false)} className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600">Cancel</button>
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">Connect</button>
              </div>
            </form>
          </div>
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
                    checked={ruleAdherence[rule.id] || false}
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
                    checked={ruleAdherence[rule.id] || false}
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
      {/* Strategy Modal */}
      {showStrategyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Add New Strategy</h2>
            <form onSubmit={handleCreateStrategy} className="space-y-4">
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
              <h3 className="text-lg font-semibold">Entry Rules</h3>
              {entryRules.map((rule, index) => (
                <div key={index} className="flex items-center">
                  <input
                    type="text"
                    value={rule}
                    onChange={(e) => updateRule('entry', index, e.target.value, setEntryRules, entryRules)}
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => removeRuleField('entry', index, setEntryRules, entryRules)}
                    className="ml-2 bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => addRuleField('entry', setEntryRules, entryRules)}
                className="text-blue-600 hover:underline"
              >
                Add another entry rule
              </button>
              <h3 className="text-lg font-semibold">Exit Rules</h3>
              {exitRules.map((rule, index) => (
                <div key={index} className="flex items-center">
                  <input
                    type="text"
                    value={rule}
                    onChange={(e) => updateRule('exit', index, e.target.value, setExitRules, exitRules)}
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => removeRuleField('exit', index, setExitRules, exitRules)}
                    className="ml-2 bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => addRuleField('exit', setExitRules, exitRules)}
                className="text-blue-600 hover:underline"
              >
                Add another exit rule
              </button>
              <div className="flex justify-end gap-4 mt-6">
                <button type="button" onClick={() => setShowStrategyModal(false)} className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600">Cancel</button>
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">Add Strategy</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Edit Strategies Modal */}
      {showEditStrategiesModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Edit Strategies</h2>
            <div>
              {strategies.map((strat) => (
                <div
                  key={strat.id}
                  onClick={() => loadEditStrategy(strat)}
                  className="p-2 hover:bg-gray-100 cursor-pointer"
                >
                  {strat.name}
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-6">
              <button onClick={() => setShowEditStrategiesModal(false)} className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600">Close</button>
            </div>
          </div>
        </div>
      )}
      {/* Edit Strategy Modal */}
      {showEditStrategyModal && editStrategy && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Edit Strategy</h2>
            <form onSubmit={handleEditStrategy} className="space-y-4">
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
              <h3 className="text-lg font-semibold">Entry Rules</h3>
              {editEntryRules.map((rule, index) => (
                <div key={index} className="flex items-center">
                  <input
                    type="text"
                    value={rule}
                    onChange={(e) => updateRule('entry', index, e.target.value, setEditEntryRules, editEntryRules)}
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => removeRuleField('entry', index, setEditEntryRules, editEntryRules)}
                    className="ml-2 bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => addRuleField('entry', setEditEntryRules, editEntryRules)}
                className="text-blue-600 hover:underline"
              >
                Add another entry rule
              </button>
              <h3 className="text-lg font-semibold">Exit Rules</h3>
              {editExitRules.map((rule, index) => (
                <div key={index} className="flex items-center">
                  <input
                    type="text"
                    value={rule}
                    onChange={(e) => updateRule('exit', index, e.target.value, setEditExitRules, editExitRules)}
                    className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => removeRuleField('exit', index, setEditExitRules, editExitRules)}
                    className="ml-2 bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => addRuleField('exit', setEditExitRules, editExitRules)}
                className="text-blue-600 hover:underline"
              >
                Add another exit rule
              </button>
              <div className="flex justify-end gap-4 mt-6">
                <button type="button" onClick={() => setShowEditStrategyModal(false)} className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600">Cancel</button>
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">Update Strategy</button>
                <button type="button" onClick={handleDeleteStrategy} className="bg-red-600 text-white px-6 py-2 rounded hover:bg-red-700">Delete Strategy</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;