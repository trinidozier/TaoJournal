import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import taoLogo from '../assets/tao-logo.jpg';

function Dashboard() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editIndex, setEditIndex] = useState(null);
  const [formData, setFormData] = useState({
    instrument: '',
    buy_timestamp: '',
    sell_timestamp: '',
    buy_price: '',
    sell_price: '',
    qty: '',
    strategy: '',
    confidence: '',
    target: '',
    stop: '',
    notes: '',
    goals: '',
    preparedness: '',
    what_i_learned: '',
    changes_needed: '',
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
  }, []);

  const fetchTrades = async () => {
    setLoading(true);
    setError('');
    try {
      console.log('Fetching trades with token:', token.substring(0, 10) + '...'); // Partial token for debug
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

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleAddTrade = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('https://taojournal-production.up.railway.app/trades', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
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
      const res = await fetch(`https://taojournal-production.up.railway.app/trades/${editIndex}`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
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

  const openEditModal = (index) => {
    setEditIndex(index);
    setFormData(trades[index]);
    setShowEditModal(true);
  };

  const handleDeleteTrade = async (index) => {
    if (!window.confirm('Delete this trade?')) return;
    try {
      const res = await fetch(`https://taojournal-production.up.railway.app/trades/${index}`, {
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
      const res = await fetch('https://taojournal-production.up.railway.app/import_csv', {
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

  const handleUploadImage = async (index, e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`https://taojournal-production.up.railway.app/trades/${index}/image`, {
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
    window.open(`https://taojournal-production.up.railway.app/trades/${index}/image?token=${token}`, '_blank');
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
      } else {
        setError(`Failed to export ${type.toUpperCase()}.`);
      }
    } catch (err) {
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
                  <td className="px-6 py-4 whitespace-nowrap">{trade.buy_timestamp}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.sell_timestamp}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.direction}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.qty}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.buy_price}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.sell_price}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{trade.strategy}</td>
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

      {/* New Trade Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-lg overflow-y-auto max-h-[80vh]">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Add New Trade</h2>
            <form onSubmit={handleAddTrade} className="space-y-4">
              <input name="instrument" placeholder="Instrument (e.g., AAPL)" value={formData.instrument} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <input name="buy_timestamp" placeholder="Buy Timestamp (YYYY-MM-DDTHH:MM:SS)" value={formData.buy_timestamp} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <input name="sell_timestamp" placeholder="Sell Timestamp (YYYY-MM-DDTHH:MM:SS)" value={formData.sell_timestamp} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <input name="buy_price" placeholder="Buy Price" value={formData.buy_price} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" step="0.01" />
              <input name="sell_price" placeholder="Sell Price" value={formData.sell_price} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" step="0.01" />
              <input name="qty" placeholder="Quantity" value={formData.qty} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" />
              <input name="strategy" placeholder="Strategy (e.g., Breakout)" value={formData.strategy} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" />
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

      {/* Edit Trade Modal (similar styling updates) */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-2xl border border-gray-200 w-full max-w-lg overflow-y-auto max-h-[80vh]">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Edit Trade</h2>
            <form onSubmit={handleEditTrade} className="space-y-4">
              {/* Same inputs as add, with values from formData */}
              <input name="instrument" placeholder="Instrument (e.g., AAPL)" value={formData.instrument} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <input name="buy_timestamp" placeholder="Buy Timestamp (YYYY-MM-DDTHH:MM:SS)" value={formData.buy_timestamp} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <input name="sell_timestamp" placeholder="Sell Timestamp (YYYY-MM-DDTHH:MM:SS)" value={formData.sell_timestamp} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required />
              <input name="buy_price" placeholder="Buy Price" value={formData.buy_price} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" step="0.01" />
              <input name="sell_price" placeholder="Sell Price" value={formData.sell_price} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" step="0.01" />
              <input name="qty" placeholder="Quantity" value={formData.qty} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" required type="number" />
              <input name="strategy" placeholder="Strategy (e.g., Breakout)" value={formData.strategy} onChange={handleInputChange} className="w-full border border-gray-300 p-2 rounded focus:border-blue-500 focus:outline-none" />
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
    </div>
  );
}

export default Dashboard;