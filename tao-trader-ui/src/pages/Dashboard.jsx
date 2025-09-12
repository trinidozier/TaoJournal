import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import taoLogo from '../assets/tao-logo.jpg'; // Your logo

function Dashboard() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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
    fees: '0',
  });
  const [csvFile, setCsvFile] = useState(null);
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

  const handleAddTrade = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        instrument: formData.instrument || '',
        buy_timestamp: formData.buy_timestamp || datetime.utcnow().isoformat(),
        sell_timestamp: formData.sell_timestamp || datetime.utcnow().isoformat(),
        buy_price: parseFloat(formData.buy_price) || 0,
        sell_price: parseFloat(formData.sell_price) || 0,
        qty: parseInt(formData.qty) || 1,
        direction: formData.direction || 'Long',
        trade_type: formData.trade_type || 'Stock',
        strategy_id: parseInt(formData.strategy_id) || None,
        confidence: parseInt(formData.confidence) || None,
        target: parseFloat(formData.target) || None,
        stop: parseFloat(formData.stop) || None,
        notes: formData.notes || '',
        goals: formData.goals || '',
        preparedness: formData.preparedness || '',
        what_i_learned: formData.what_i_learned || '',
        changes_needed: formData.changes_needed || '',
        fees: parseFloat(formData.fees) || 0,
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
      const text = await res.text();
      console.log('Add trade response:', res.status, text);
      if (res.ok) {
        setFormData({
          instrument: '',
          buy_timestamp: '',
          sell_timestamp: '',
          buy_price: '',
          sell_price: '',
          qty: '',
          strategy_id: '',
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
          fees: '0',
        });
        setShowNewModal(false);
        fetchTrades();
      } else {
        setError(`Failed to add trade: ${text || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Add trade error:', err);
      setError('Error adding trade. Please try again.');
    }
  };

  const handleCsvUpload = async () => {
    if (!csvFile) {
      setError('Please select a CSV file.');
      return;
    }
    const formData = new FormData();
    formData.append('file', csvFile);
    try {
      const res = await fetch('https://taojournal-production.up.railway.app/import_csv', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      const text = await res.text();
      console.log('CSV upload response:', res.status, text);
      if (res.ok) {
        setCsvFile(null);
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
      <h1 className="text-4xl font-bold text-center mb-8 text-gray-800">Your Tao Trader Journal Dashboard</h1>

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
        <button onClick={() => navigate('/analytics')} className="bg-indigo-500 text-white px-6 py-3 rounded-lg shadow-md hover:bg-indigo-600 transition flex items-center">
          <span className="mr-2">📊</span> View Analytics
        </button>
      </div>

      {trades.length === 0 ? (
        <div className="bg-white p-8 rounded-lg shadow-xl border border-gray-200 max-w-2xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-800">Welcome to Tao Trader Journal!</h2>
          <p className="text-gray-600 mb-6">It looks like you don't have any trades yet. Get started by adding your first trade or uploading a CSV from your broker.</p>
          <div className="flex justify-center gap-4">
            <button onClick={() => setShowNewModal(true)} className="bg-green-500 text-white px-6 py-3 rounded-lg hover:bg-green-600">Add Manual Trade</button>
            <label className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 cursor-pointer">
              Upload CSV
              <input type="file" accept=".csv" onChange={handleCsvChange} className="hidden" />
            </label>
          </div>
          <p className="text-sm text-gray-500 mt-6">Tao Trader Journal helps you track, analyze, and improve your trading journey—better than the rest.</p>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
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
                  <td className="px-6 py-4 whitespace-nowrap">{trade.timestamp}</td>
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
                <label className="block text-sm font-medium text-gray-700">Instrument</label>
                <input
                  name="instrument"
                  value={formData.instrument}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Buy Price</label>
                <input
                  type="number"
                  name="buy_price"
                  value={formData.buy_price}
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
                  value={formData.sell_price}
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
                  value={formData.qty}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Direction</label>
                <select
                  name="direction"
                  value={formData.direction}
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
                  value={formData.stop}
                  onChange={handleInputChange}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Fees</label>
                <input
                  type="number"
                  name="fees"
                  value={formData.fees}
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
    </div>
  );
}

export default Dashboard;