import React, { useState, useEffect } from 'react';
import './FoodRescueNegotiation.css';
import axios from 'axios';
// Add marked for markdown rendering
import { marked } from 'marked';

function FoodRescueNegotiation() {
  const [convId, setConvId] = useState(null);
  const [chat, setChat] = useState([]);
  const [input, setInput] = useState('');
  const [bizName, setBizName] = useState('');
  const [bizType, setBizType] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('business');
  const [inventoryFile, setInventoryFile] = useState(null);
  const [inventoryPreview, setInventoryPreview] = useState(null);

  const startNegotiation = async () => {
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append(
        "business_info",
        JSON.stringify({
          name: bizName,
          type: bizType,
          latitude: parseFloat(latitude),
          longitude: parseFloat(longitude),
        })
      );
      
      if (inventoryFile) {
        formData.append("inventory_file", inventoryFile);
      }
      
      const res = await axios.post("https://agentic-llm-powered-food-rescue-net-seven.vercel.app/negotiate/start", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      
      setConvId(res.data.conversation_id);
      setChat([{ from: "bot", text: res.data.message }]);
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.statusText ||
        err.message;
      alert(`Error starting negotiation: ${msg}`);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    
    setIsLoading(true);
    const userInput = input;
    setInput('');
    setChat(prev => [...prev, { from: 'user', text: userInput }]);
    
    try {
      const res = await axios.post('https://agentic-llm-powered-food-rescue-net-seven.vercel.app/negotiate/respond', {
        conversation_id: convId,
        owner_response: userInput
      });
      setChat(prev => [...prev, { from: 'bot', text: res.data.message }]);
      
      if (res.data.status !== 'ongoing') {
        setTimeout(() => {
          alert(`Negotiation ${res.data.status}!`);
        }, 500);
      }
    } catch (error) {
      alert('Error sending message: ' + (error.response?.data?.message || error.message));
      setInput(userInput);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSampleData = () => {
    setBizName('Fresh Market');
    setBizType('Supermarket');
    setLatitude('37.7749');
    setLongitude('-122.4194');
    
    // Create sample file
    const csvContent = "food,type,quantity,expiry\nBakery,Bakery,20,2024-05-20\nProduce,Produce,15,2024-05-18\nDairy,Dairy,30,2024-05-17";
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const sampleFile = new File([blob], "sample_inventory.csv", { type: 'text/csv' });
    
    setInventoryFile(sampleFile);
    setInventoryPreview(csvContent);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setInventoryFile(file);
    
    // Preview file content
    const reader = new FileReader();
    reader.onload = (event) => {
      setInventoryPreview(event.target.result);
    };
    reader.readAsText(file);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Helper to safely render markdown for bot messages
  const renderBotMessage = (text) => {
    return (
      <div
        className="bot-markdown"
        dangerouslySetInnerHTML={{ __html: marked.parse(text || "") }}
      />
    );
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo-container">
          <div className="logo-icon">🥬</div>
          <h1>Food Rescue Negotiation</h1>
        </div>
        <p>Connect businesses with food rescue organizations to reduce waste</p>
      </header>

      <main className="app-main">
        {!convId ? (
          <div className="setup-container">
            <div className="setup-tabs">
              <button 
                className={activeTab === 'business' ? 'active' : ''} 
                onClick={() => setActiveTab('business')}
              >
                Business Info
              </button>
              <button 
                className={activeTab === 'location' ? 'active' : ''} 
                onClick={() => setActiveTab('location')}
              >
                Location
              </button>
              <button 
                className={activeTab === 'inventory' ? 'active' : ''} 
                onClick={() => setActiveTab('inventory')}
              >
                Inventory
              </button>
            </div>

            <div className="setup-content">
              {activeTab === 'business' && (
                <div className="form-section">
                  <h2>Business Information</h2>
                  <div className="form-group">
                    <label>Business Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Fresh Market"
                      value={bizName}
                      onChange={e => setBizName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Business Type</label>
                    <input
                      type="text"
                      placeholder="e.g. Grocery Store, Restaurant"
                      value={bizType}
                      onChange={e => setBizType(e.target.value)}
                      required
                    />
                  </div>
                  <div className="navigation-buttons">
                    <button
                      onClick={() => setActiveTab('location')}
                      disabled={!bizName || !bizType}
                      className="next-btn"
                    >
                      Next: Location Details →
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'location' && (
                <div className="form-section">
                  <h2>Location Details</h2>
                  <div className="form-grid">
                    <div className="form-group">
                      <label>Latitude</label>
                      <input
                        type="number"
                        placeholder="e.g. 37.7749"
                        value={latitude}
                        onChange={e => setLatitude(e.target.value)}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Longitude</label>
                      <input
                        type="number"
                        placeholder="e.g. -122.4194"
                        value={longitude}
                        onChange={e => setLongitude(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="map-preview">
                    <div className="map-placeholder">
                      <div className="pin">📍</div>
                      <p>Map Preview</p>
                    </div>
                  </div>
                  <div className="navigation-buttons">
                    <button
                      onClick={() => setActiveTab('business')}
                      className="back-btn"
                    >
                      ← Back: Business Info
                    </button>
                    <button
                      onClick={() => setActiveTab('inventory')}
                      disabled={!latitude || !longitude}
                      className="next-btn"
                    >
                      Next: Inventory Details →
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'inventory' && (
                <div className="form-section">
                  <h2>Inventory Details</h2>
                  <div className="form-group">
                    <button onClick={loadSampleData} className="load-sample-btn">
                      Load Sample Data
                    </button>
                  </div>
                  <div className="inventory-upload">
                    <label className="file-upload-label">
                      <input
                        type="file"
                        accept=".csv"
                        onChange={handleFileUpload}
                      />
                      {inventoryFile ? "Change File" : "Upload Inventory CSV"}
                    </label>
                    {inventoryFile && (
                      <div className="file-info">
                        <span>{inventoryFile.name}</span>
                        <button 
                          className="remove-btn"
                          onClick={() => {
                            setInventoryFile(null);
                            setInventoryPreview(null);
                          }}
                        >
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="inventory-preview">
                    {inventoryPreview ? (
                      <pre>{inventoryPreview}</pre>
                    ) : (
                      <div className="preview-placeholder">
                        <p>Upload a CSV file or load sample data</p>
                      </div>
                    )}
                  </div>
                  <div className="navigation-buttons">
                    <button
                      onClick={() => setActiveTab('location')}
                      className="back-btn"
                    >
                      ← Back: Location Details
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            <div className="setup-actions">
              <button 
                className="primary-btn" 
                onClick={startNegotiation}
                disabled={isLoading || !bizName || !bizType || !latitude || !longitude || !inventoryFile}
              >
                {isLoading ? 'Starting...' : 'Begin Negotiation'}
              </button>
              <div className="form-progress">
                <div className={`progress-step ${bizName && bizType ? 'completed' : ''}`}>1</div>
                <div className={`progress-step ${latitude && longitude ? 'completed' : ''}`}>2</div>
                <div className={`progress-step ${inventoryFile ? 'completed' : ''}`}>3</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="chat-container">
            <div className="chat-messages">
              {chat.map((msg, i) => (
                <div key={i} className={`message ${msg.from === 'bot' ? 'bot' : 'user'}`}>
                  <div className="message-content">
                    {msg.from === 'bot'
                      ? renderBotMessage(msg.text)
                      : <span>{msg.text}</span>
                    }
                  </div>
                </div>
              ))}
            </div>
            
            <div className="chat-input">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your response..."
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
              >
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        )}
      </main>
      
      <footer className="app-footer">
        <p>Food Rescue Platform • Reducing food waste one negotiation at a time</p>
        <div className="footer-links">
          <a href="#">Help Center</a>
          <a href="#">Privacy Policy</a>
          <a href="#">Terms of Service</a>
        </div>
      </footer>
    </div>
  );
}

export default FoodRescueNegotiation;