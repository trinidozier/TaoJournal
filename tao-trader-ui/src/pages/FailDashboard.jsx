import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import forgeLogo from '../assets/forgelogo.png';

function Dashboard() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPlaybookModal, setShowPlaybookModal] = useState(false);
  const [showStrategyEditModal, setShowStrategyEditModal] = useState(false);
  const [editStrategy, setEditStrategy] = useState(null);
  const [strategyForm, setStrategyForm] = useState({ name: '', description: '' });
  const [entryRules, setEntryRules] = useState(['']);
  const [exitRules, setExitRules] = useState(['']);
  const [strategies, setStrategies] = useState([]);
  const [editIndex, setEditIndex] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [importDates, setImportDates] = useState({ start_date: '', end_date: '' });
  const [ibkrForm, setIBKRForm] = useState({ api_token: '', account_id: '' });
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
    setSuccess('');
    try {
      console.log('Fetching trades with token:', token ? token.substring(0, 10) + '...' : 'No token');
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
        localStorage.removeItem('token');
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
      setError('Error fetching strategies. Please try again.');
    }
  };

  const handleInputChange = (e) => {
    setFormData({ ...FormData, [e.target.name]: e.target.value });
  };

  const handleAddTrade = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        buy_price: parseFloat(FormData.buy_price) || 0,
        sell_price: parseFloat(FormData.sell_price) || 0,
        qty: parseInt(FormData.qty) || 1,
        buy_timestamp: FormData.buy_timestamp || null,
        sell_timestamp: FormData.sell_timestamp || null,
        direction: FormData.direction || 'Long',
        stop: parseFloat(FormData.stop) || null,
        fees: parseFloat(FormData.fees) || 0,
      };
      console.log('Submitting trade:', payload);
      const res = await fetch('https://taojournal-production.up.railway.app/trades', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      console.log('Add trade response status:', res.status);
      const text = await res.text();
      console.log('Add trade response body:', text);
      if (res.ok) {
        setFormData({
          buy_price: '',
          sell_price: '',
          qty: '',
          buy_timestamp: '',
          sell_timestamp: '',
          direction: 'Long',
          stop: '',
          fees: '0',
        });
        setShowNewModal(false);
        setSuccess('Trade added successfully!');
        fetchTrades();
      } else {
        setError(`Failed to add trade: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Add trade error:', err);
      setError('Error adding trade. Please try again.');
    }
  };

  const handleEditTrade = (trade) => {
    setFormData({
      buy_price: trade.buy_price || '',
      sell_price: trade.sell_price || '',
      qty: trade.qty || '',
      buy_timestamp: trade.buy_timestamp || '',
      sell_timestamp: trade.sell_timestamp || '',
      direction: trade.direction || 'Long',
      stop: trade.stop || '',
      fees: trade.fees || '0',
    });
    setEditIndex(trade.id);
    setShowEditModal(true);
  };

  const handleUpdateTrade = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        buy_price: parseFloat(FormData.buy_price) || 0,
        sell_price: parseFloat(FormData.sell_price) || 0,
        qty: parseInt(FormData.qty) || 1,
        buy_timestamp: FormData.buy_timestamp || null,
        sell_timestamp: FormData.sell_timestamp || null,
        direction: FormData.direction || 'Long',
        stop: parseFloat(FormData.stop) || null,
        fees: parseFloat(FormData.fees) || 0,
      };
      const res = await fetch(`https://taojournal-production.up.railway.app/trades/${editIndex}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      console.log('Update trade response status:', res.status);
      const text = await res.text();
      console.log('Update trade response body:', text);
      if (res.ok) {
        setFormData({
          buy_price: '',
          sell_price: '',
          qty: '',
          buy_timestamp: '',
          sell_timestamp: '',
          direction: 'Long',
          stop: '',
          fees: '0',
        });
        setShowEditModal(false);
        setSuccess('Trade updated successfully!');
        fetchTrades();
      } else {
        setError(`Failed to update trade: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Update trade error:', err);
      setError('Error updating trade. Please try again.');
    }
  };

  const handleDeleteTrade = async (trade_id) => {
    try {
      console.log('Deleting trade:', trade_id);
      const res = await fetch(`https://taojournal-production.up.railway.app/trades/${trade_id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      console.log('Delete trade response status:', res.status);
      const text = await res.text();
      console.log('Delete trade response body:', text);
      if (res.ok) {
        setSuccess('Trade deleted successfully!');
        fetchTrades();
      } else {
        setError(`Failed to delete trade: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Delete trade error:', err);
      setError('Error deleting trade. Please try again.');
    }
  };

  const handleCsvUpload = async () => {
    if (!csvFile) {
      setError('Please select a CSV file.');
      return;
    }
    setError('');
    setSuccess('');
    const formData = new FormData();
    formData.append('file', csvFile);
    try {
      console.log('Uploading CSV with token:', token ? token.substring(0, 10) + '...' : 'No token');
      const res = await fetch('https://taojournal-production.up.railway.app/import_csv', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      console.log('CSV upload response status:', res.status);
      const text = await res.text();
      console.log('CSV upload response body:', text);
      if (res.ok) {
        setCsvFile(null);
        setSuccess('CSV uploaded successfully!');
        fetchTrades();
      } else {
        setError(`Failed to upload CSV: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('CSV upload error:', err);
      setError('Error uploading CSV. Please try again.');
    }
  };

  const handleCsvChange = (e) => {
    setCsvFile(e.target.files[0]);
  };

  const handleExport = async (type) => {
    try {
      console.log(`Exporting trades as ${type} with token:`, token ? token.substring(0, 10) + '...' : 'No token');
      const res = await fetch(`https://taojournal-production.up.railway.app/export/${type}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      console.log(`Export ${type} response status:`, res.status);
      const text = await res.text();
      console.log(`Export ${type} response body:`, text);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trades.${type}`;
        a.click();
        window.URL.revokeObjectURL(url);
        setSuccess(`Exported trades to ${type} successfully!`);
      } else {
        setError(`Failed to export ${type}: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(`Export ${type} error:`, err);
      setError(`Error exporting ${type}. Please try again.');
    }
  };

  const handleStrategyInputChange = (e) => {
    setStrategyForm({ ...strategyForm, [e.target.name]: e.target.value });
  };

  const handleEntryRuleChange = (index, value) => {
    const newRules = [...entryRules];
    newRules[index] = value;
    setEntryRules(newRules);
  };

  const handleExitRuleChange = (index, value) => {
    const newRules = [...exitRules];
    newRules[index] = value;
    setExitRules(newRules);
  };

  const addEntryRule = () => {
    setEntryRules([...entryRules, '']);
  };

  const addExitRule = () => {
    setExitRules([...exitRules, '']);
  };

  const removeEntryRule = (index) => {
    setEntryRules(entryRules.filter((_, i) => i !== index));
  };

  const removeExitRule = (index) => {
    setExitRules(exitRules.filter((_, i) => i !== index));
  };

  const handleAddStrategy = async (e) => {
    e.preventDefault();
    try {
      const payload = { name: strategyForm.name, description: strategyForm.description };
      console.log('Adding strategy:', payload);
      const res = await fetch('https://taojournal-production.up.railway.app/strategies', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      console.log('Add strategy response status:', res.status);
      const text = await res.text();
      console.log('Add strategy response body:', text);
      if (res.ok) {
        const strategy = JSON.parse(text);
        for (const ruleText of entryRules) {
          if (ruleText) {
            await fetch('https://taojournal-production.up.railway.app/rules', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ strategy_id: strategy.id, rule_type: 'entry', rule_text: ruleText }),
            });
          }
        }
        for (const ruleText of exitRules) {
          if (ruleText) {
            await fetch('https://taojournal-production.up.railway.app/rules', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ strategy_id: strategy.id, rule_type: 'exit', rule_text: ruleText }),
            });
          }
        }
        setStrategyForm({ name: '', description: '' });
        setEntryRules(['']);
        setExitRules(['']);
        setShowStrategyEditModal(false);
        setSuccess('Strategy added successfully!');
        fetchStrategies();
      } else {
        setError(`Failed to add strategy: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Add strategy error:', err);
      setError('Error adding strategy. Please try again.');
    }
  };

  const handleEditStrategy = (strategy) => {
    setEditStrategy(strategy);
    setStrategyForm({ name: strategy.name, description: strategy.description });
    setEntryRules(['']);
    setExitRules(['']);
    setShowStrategyEditModal(true);
  };

  const handleUpdateStrategy = async (e) => {
    e.preventDefault();
    try {
      const payload = { name: strategyForm.name, description: strategyForm.description };
      console.log('Updating strategy:', payload);
      const res = await fetch(`https://taojournal-production.up.railway.app/strategies/${editStrategy.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      console.log('Update strategy response status:', res.status);
      const text = await res.text();
      console.log('Update strategy response body:', text);
      if (res.ok) {
        await fetch(`https://taojournal-production.up.railway.app/rules/${editStrategy.id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        for (const ruleText of entryRules) {
          if (ruleText) {
            await fetch('https://taojournal-production.up.railway.app/rules', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ strategy_id: editStrategy.id, rule_type: 'entry', rule_text: ruleText }),
            });
          }
        }
        for (const ruleText of exitRules) {
          if (ruleText) {
            await fetch('https://taojournal-production.up.railway.app/rules', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ strategy_id: editStrategy.id, rule_type: 'exit', rule_text: ruleText }),
            });
          }
        }
        setStrategyForm({ name: '', description: '' });
        setEntryRules(['']);
        setExitRules(['']);
        setShowStrategyEditModal(false);
        setSuccess('Strategy updated successfully!');
        fetchStrategies();
      } else {
        setError(`Failed to update strategy: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Update strategy error:', err);
      setError('Error updating strategy. Please try again.');
    }
  };

  const handleDeleteStrategy = async (strategy_id) => {
    try {
      console.log('Deleting strategy:', strategy_id);
      const res = await fetch(`https://taojournal-production.up.railway.app/strategies/${strategy_id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      console.log('Delete strategy response status:', res.status);
      const text = await res.text();
      console.log('Delete strategy response body:', text);
      if (res.ok) {
        setSuccess('Strategy deleted successfully!');
        fetchStrategies();
      } else {
        setError(`Failed to delete strategy: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Delete strategy error:', err);
      setError('Error deleting strategy. Please try again.');
    }
  };

  const handleImageUpload = async (trade_id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      console.log('Uploading image for trade:', trade_id);
      const res = await fetch(`https://taojournal-production.up.railway.app/trades/${trade_id}/image`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      console.log('Image upload response status:', res.status);
      const text = await res.text();
      console.log('Image upload response body:', text);
      if (res.ok) {
        setSuccess('Image uploaded successfully!');
      } else {
        setError(`Failed to upload image: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Image upload error:', err);
      setError('Error uploading image. Please try again.');
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
      <h1 className="text-4xl font-bold text-center mb-8 text-gray-800">StrategyForge Journal Dashboard</h1>
      {success && (
        <div className="text-center text-green-500 mb-4">{success}</div>
      )}
      <div className="flex flex-wrap justify-center gap-4 mb-8">
        <button onClick={() => setShowNewModal(true)} className="bg-green-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-green-600 transition flex items-center">
          <span className="mr-2">➕</span> Add New Trade
        </button>
        <label className="bg-blue-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-blue-600 transition cursor-pointer flex items-center">
          <span className="mr-2">📥</span> Upload Broker CSV
          <input type="file" accept=".csv" onChange={handleCsvChange} className="hidden" />
        </label>
        <button onClick={handleCsvUpload} className="bg-green-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-green-600 transition flex items-center" disabled={!csvFile}>
          <span className="mr-2">↑</span> Process CSV
        </button>
        <button onClick={() => setShowPlaybookModal(true)} className="bg-purple-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-purple-600 transition flex items-center">
          <span className="mr-2">📘</span> Playbook
        </button>
        <button onClick={() => navigate('/analytics')} className="bg-indigo-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-indigo-600 transition flex items-center">
          <span className="mr-2">📊</span> View Analytics
        </button>
        <button onClick={() => handleExport('excel')} className="bg-teal-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-teal-600 transition flex items-center">
          <span className="mr-2">📈</span> Export to Excel
        </button>
        <button onClick={() => handleExport('pdf')} className="bg-teal-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-teal-600 transition flex items-center">
          <span className="mr-2">📄</span> Export to PDF
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
              <input type="file" accept=".csv" onChange={handleCsvChange} className="hidden" />
            </label>
          </div>
          <p className="text-sm text-gray-500 mt-6">StrategyForge Journal helps you track, analyze, and improve your trading journey—better than the rest.</p>
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg shadow-xl border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Buy Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sell Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Qty</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Direction</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">R-Multiple</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {trades.map((trade) => (
                <tr key={trade.id} className={trade.direction === 'Long' ? 'hover:bg-green-100' : 'hover:bg-red-100'}>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap">${trade.buy_price.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">${trade.sell_price.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.qty}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.direction}</td>
                  <td className="px-6 py-4 whitespace-nowrap">${trade.pnl.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.r_multiple.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.timestamp}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button onClick={() => handleEditTrade(trade)} className="text-blue-600 hover:text-blue-800 mr-2">Edit</button>
                    <button onClick={() => handleDeleteTrade(trade.id)} className="text-red-600 hover:text-red-800">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* New Trade Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Add New Trade</h2>
            <form onSubmit={handleAddTrade}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Buy Price</label>
                <input
                  type="number"
                  name="buy_price"
                  value={FormData.buy_price}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Sell Price</label>
                <input
                  type="number"
                  name="sell_price"
                  value={FormData.sell_price}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Quantity</label>
                <input
                  type="number"
                  name="qty"
                  value={FormData.qty}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Buy Timestamp</label>
                <input
                  type="datetime-local"
                  name="buy_timestamp"
                  value={FormData.buy_timestamp}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Sell Timestamp</label>
                <input
                  type="datetime-local"
                  name="sell_timestamp"
                  value={FormData.sell_timestamp}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Direction</label>
                <select
                  name="direction"
                  value={FormData.direction}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                >
                  <option value="Long">Long</option>
                  <option value="Short">Short</option>
                </select>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Stop Price</label>
                <input
                  type="number"
                  name="stop"
                  value={FormData.stop}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Fees</label>
                <input
                  type="number"
                  name="fees"
                  value={FormData.fees}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  step="0.01"
                />
              </div>
              <div className="flex justify-end gap-4">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="bg-gray-500 text-white px-4 py-2 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-blue-500 text-white px-4 py-2 rounded"
                >
                  Save Trade
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Trade Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Edit Trade</h2>
            <form onSubmit={handleUpdateTrade}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Buy Price</label>
                <input
                  type="number"
                  name="buy_price"
                  value={FormData.buy_price}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Sell Price</label>
                <input
                  type="number"
                  name="sell_price"
                  value={FormData.sell_price}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Quantity</label>
                <input
                  type="number"
                  name="qty"
                  value={FormData.qty}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Buy Timestamp</label>
                <input
                  type="datetime-local"
                  name="buy_timestamp"
                  value={FormData.buy_timestamp}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Sell Timestamp</label>
                <input
                  type="datetime-local"
                  name="sell_timestamp"
                  value={FormData.sell_timestamp}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Direction</label>
                <select
                  name="direction"
                  value={FormData.direction}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                >
                  <option value="Long">Long</option>
                  <option value="Short">Short</option>
                </select>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Stop Price</label>
                <input
                  type="number"
                  name="stop"
                  value={FormData.stop}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Fees</label>
                <input
                  type="number"
                  name="fees"
                  value={FormData.fees}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  step="0.01"
                />
              </div>
              <div className="flex justify-end gap-4">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="bg-gray-500 text-white px-4 py-2 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-blue-500 text-white px-4 py-2 rounded"
                >
                  Update Trade
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Playbook Modal */}
      {showPlaybookModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-2xl w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Trading Playbook</h2>
            <div className="mb-4">
              <button
                onClick={() => {
                  setStrategyForm({ name: '', description: '' });
                  setEntryRules(['']);
                  setExitRules(['']);
                  setEditStrategy(null);
                  setShowStrategyEditModal(true);
                }}
                className="bg-green-500 text-white px-4 py-2 rounded"
              >
                Add New Strategy
              </button>
            </div>
            <div className="space-y-4">
              {strategies.map((strategy) => (
                <div key={strategy.id} className="border p-4 rounded">
                  <h3 className="text-lg font-semibold">{strategy.name}</h3>
                  <p className="text-gray-600">{strategy.description || 'No description'}</p>
                  <div className="mt-2">
                    <button
                      onClick={() => handleEditStrategy(strategy)}
                      className="text-blue-600 hover:text-blue-800 mr-2"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteStrategy(strategy.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={() => setShowPlaybookModal(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Strategy Edit Modal */}
      {showStrategyEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">{editStrategy ? 'Edit Strategy' : 'Add New Strategy'}</h2>
            <form onSubmit={editStrategy ? handleUpdateStrategy : handleAddStrategy}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Strategy Name</label>
                <input
                  name="name"
                  value={strategyForm.name}
                  onChange={handleStrategyInputChange}
                  className="w-full border p-2 rounded"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  name="description"
                  value={strategyForm.description}
                  onChange={handleStrategyInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Entry Rules</label>
                {entryRules.map((rule, index) => (
                  <div key={index} className="flex mb-2">
                    <input
                      value={rule}
                      onChange={(e) => handleEntryRuleChange(index, e.target.value)}
                      className="w-full border p-2 rounded"
                    />
                    <button
                      type="button"
                      onClick={() => removeEntryRule(index)}
                      className="ml-2 text-red-600 hover:text-red-800"
                    >
                      Remove
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addEntryRule}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Add Entry Rule
                </button>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Exit Rules</label>
                {exitRules.map((rule, index) => (
                  <div key={index} className="flex mb-2">
                    <input
                      value={rule}
                      onChange={(e) => handleExitRuleChange(index, e.target.value)}
                      className="w-full border p-2 rounded"
                    />
                    <button
                      type="button"
                      onClick={() => removeExitRule(index)}
                      className="ml-2 text-red-600 hover:text-red-800"
                    >
                      Remove
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addExitRule}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Add Exit Rule
                </button>
              </div>
              <div className="flex justify-end gap-4">
                <button
                  type="button"
                  onClick={() => setShowStrategyEditModal(false)}
                  className="bg-gray-500 text-white px-4 py-2 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-blue-500 text-white px-4 py-2 rounded"
                >
                  {editStrategy ? 'Update Strategy' : 'Add Strategy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;