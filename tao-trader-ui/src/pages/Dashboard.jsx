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
    try {
      console.log('Fetching trades with token:', token);
      const res = await fetch('https://taojournal-production.up.railway.app/trades', {
        headers: { Authorization: `Bearer ${token}` },
      });
      console.log('Trades fetch response:', res.status, await res.text());
      if (res.ok) {
        const data = await res.json();
        setTrades(data);
      } else {
        setError('Failed to load trades.');
      }
    } catch (err) {
      console.error('Trades fetch error:', err);
      setError('Error fetching trades.');
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

  if (loading) return <p className="text-center">Loading...</p>;
  if (error) return <p className="text-center text-red-500">{error}</p>;

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="flex justify-center mb-4">
        <img src={taoLogo} alt="Tao Trader Logo" className="h-16 w-auto rounded" />
      </div>
      <h1 className="text-3xl font-bold text-center mb-6">Trade Journal Dashboard</h1>
      <div className="flex flex-wrap justify-center gap-4 mb-6">
        <button onClick={() => setShowNewModal(true)} className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">New Trade</button>
        <label className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 cursor-pointer">
          Upload CSV
          <input type="file" accept=".csv" onChange={handleUploadCSV} className="hidden" />
        </label>
        <button onClick={() => handleExport('excel')} className="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600">Export Excel</button>
        <button onClick={() => handleExport('pdf')} className="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600">Export PDF</button>
        <button onClick={() => navigate('/analytics')} className="bg-indigo-500 text-white px-4 py-2 rounded hover:bg-indigo-600">Analytics</button>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white shadow-md rounded-lg">
          <thead className="bg-gray-200">
            <tr>
              <th className="py-2 px-4 border-b">Instrument</th>
              <th className="py-2 px-4 border-b">Buy Timestamp</th>
              <th className="py-2 px-4 border-b">Sell Timestamp</th>
              <th className="py-2 px-4 border-b">Direction</th>
              <th className="py-2 px-4 border-b">Qty</th>
              <th className="py-2 px-4 border-b">Buy Price</th>
              <th className="py-2 px-4 border-b">Sell Price</th>
              <th className="py-2 px-4 border-b">Strategy</th>
              <th className="py-2 px-4 border-b">Confidence</th>
              <th className="py-2 px-4 border-b">Target</th>
              <th className="py-2 px-4 border-b">Stop</th>
              <th className="py-2 px-4 border-b">R-Multiple</th>
              <th className="py-2 px-4 border-b">PnL</th>
              <th className="py-2 px-4 border-b">Notes</th>
              <th className="py-2 px-4 border-b">Goals</th>
              <th className="py-2 px-4 border-b">Preparedness</th>
              <th className="py-2 px-4 border-b">What I Learned</th>
              <th className="py-2 px-4 border-b">Changes Needed</th>
              <th className="py-2 px-4 border-b">Image</th>
              <th className="py-2 px-4 border-b">Actions</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, index) => (
              <tr key={index} className={trade.direction === 'Long' ? 'bg-green-50' : 'bg-red-50'}>
                <td className="py-2 px-4 border-b">{trade.instrument}</td>
                <td className="py-2 px-4 border-b">{trade.buy_timestamp}</td>
                <td className="py-2 px-4 border-b">{trade.sell_timestamp}</td>
                <td className="py-2 px-4 border-b">{trade.direction}</td>
                <td className="py-2 px-4 border-b">{trade.qty}</td>
                <td className="py-2 px-4 border-b">{trade.buy_price}</td>
                <td className="py-2 px-4 border-b">{trade.sell_price}</td>
                <td className="py-2 px-4 border-b">{trade.strategy}</td>
                <td className="py-2 px-4 border-b">{trade.confidence}</td>
                <td className="py-2 px-4 border-b">{trade.target}</td>
                <td className="py-2 px-4 border-b">{trade.stop}</td>
                <td className="py-2 px-4 border-b">{trade.r_multiple}</td>
                <td className="py-2 px-4 border-b">{trade.pnl}</td>
                <td className="py-2 px-4 border-b">{trade.notes}</td>
                <td className="py-2 px-4 border-b">{trade.goals}</td>
                <td className="py-2 px-4 border-b">{trade.preparedness}</td>
                <td className="py-2 px-4 border-b">{trade.what_i_learned}</td>
                <td className="py-2 px-4 border-b">{trade.changes_needed}</td>
                <td className="py-2 px-4 border-b">
                  {trade.image_path ? (
                    <button onClick={() => handleViewImage(index)} className="text-blue-500 hover:underline">View</button>
                  ) : (
                    <label className="text-blue-500 hover:underline cursor-pointer">
                      Upload
                      <input type="file" accept="image/*" onChange={(e) => handleUploadImage(index, e)} className="hidden" />
                    </label>
                  )}
                </td>
                <td className="py-2 px-4 border-b">
                  <button onClick={() => openEditModal(index)} className="text-yellow-500 hover:underline mr-2">Edit</button>
                  <button onClick={() => handleDeleteTrade(index)} className="text-red-500 hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* New Trade Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md overflow-y-auto max-h-96">
            <h2 className="text-xl font-bold mb-4">Add New Trade</h2>
            <form onSubmit={handleAddTrade} className="space-y-4">
              <input name="instrument" placeholder="Instrument" value={formData.instrument} onChange={handleInputChange} className="w-full border p-2 rounded" required />
              <input name="buy_timestamp" placeholder="Buy Timestamp (YYYY-MM-DDTHH:MM:SS)" value={formData.buy_timestamp} onChange={handleInputChange} className="w-full border p-2 rounded" required />
              <input name="sell_timestamp" placeholder="Sell Timestamp (YYYY-MM-DDTHH:MM:SS)" value={formData.sell_timestamp} onChange={handleInputChange} className="w-full border p-2 rounded" required />
              <input name="buy_price" placeholder="Buy Price" value={formData.buy_price} onChange={handleInputChange} className="w-full border p-2 rounded" required type="number" />
              <input name="sell_price" placeholder="Sell Price" value={formData.sell_price} onChange={handleInputChange} className="w-full border p-2 rounded" required type="number" />
              <input name="qty" placeholder="Quantity" value={formData.qty} onChange={handleInputChange} className="w-full border p-2 rounded" required type="number" />
              <input name="strategy" placeholder="Strategy" value={formData.strategy} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <input name="confidence" placeholder="Confidence (1-5)" value={formData.confidence} onChange={handleInputChange} className="w-full border p-2 rounded" type="number" min="1" max="5" />
              <input name="target" placeholder="Target" value={formData.target} onChange={handleInputChange} className="w-full border p-2 rounded" type="number" />
              <input name="stop" placeholder="Stop" value={formData.stop} onChange={handleInputChange} className="w-full border p-2 rounded" type="number" />
              <textarea name="notes" placeholder="Notes" value={formData.notes} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <textarea name="goals" placeholder="Goals" value={formData.goals} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <textarea name="preparedness" placeholder="Preparedness" value={formData.preparedness} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <textarea name="what_i_learned" placeholder="What I Learned" value={formData.what_i_learned} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <textarea name="changes_needed" placeholder="Changes Needed" value={formData.changes_needed} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <div className="flex justify-end gap-4">
                <button type="button" onClick={() => setShowNewModal(false)} className="bg-gray-500 text-white px-4 py-2 rounded">Cancel</button>
                <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">Add</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Trade Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md overflow-y-auto max-h-96">
            <h2 className="text-xl font-bold mb-4">Edit Trade</h2>
            <form onSubmit={handleEditTrade} className="space-y-4">
              <input name="instrument" placeholder="Instrument" value={formData.instrument} onChange={handleInputChange} className="w-full border p-2 rounded" required />
              <input name="buy_timestamp" placeholder="Buy Timestamp (YYYY-MM-DDTHH:MM:SS)" value={formData.buy_timestamp} onChange={handleInputChange} className="w-full border p-2 rounded" required />
              <input name="sell_timestamp" placeholder="Sell Timestamp (YYYY-MM-DDTHH:MM:SS)" value={formData.sell_timestamp} onChange={handleInputChange} className="w-full border p-2 rounded" required />
              <input name="buy_price" placeholder="Buy Price" value={formData.buy_price} onChange={handleInputChange} className="w-full border p-2 rounded" required type="number" />
              <input name="sell_price" placeholder="Sell Price" value={formData.sell_price} onChange={handleInputChange} className="w-full border p-2 rounded" required type="number" />
              <input name="qty" placeholder="Quantity" value={formData.qty} onChange={handleInputChange} className="w-full border p-2 rounded" required type="number" />
              <input name="strategy" placeholder="Strategy" value={formData.strategy} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <input name="confidence" placeholder="Confidence (1-5)" value={formData.confidence} onChange={handleInputChange} className="w-full border p-2 rounded" type="number" min="1" max="5" />
              <input name="target" placeholder="Target" value={formData.target} onChange={handleInputChange} className="w-full border p-2 rounded" type="number" />
              <input name="stop" placeholder="Stop" value={formData.stop} onChange={handleInputChange} className="w-full border p-2 rounded" type="number" />
              <textarea name="notes" placeholder="Notes" value={formData.notes} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <textarea name="goals" placeholder="Goals" value={formData.goals} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <textarea name="preparedness" placeholder="Preparedness" value={formData.preparedness} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <textarea name="what_i_learned" placeholder="What I Learned" value={formData.what_i_learned} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <textarea name="changes_needed" placeholder="Changes Needed" value={formData.changes_needed} onChange={handleInputChange} className="w-full border p-2 rounded" />
              <div className="flex justify-end gap-4">
                <button type="button" onClick={() => setShowEditModal(false)} className="bg-gray-500 text-white px-4 py-2 rounded">Cancel</button>
                <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;