import React, { useState, useEffect } from 'react';
import ExtractionForm from './components/ExtractionForm';
import JobList from './components/JobList';
import HealthStatus from './components/HealthStatus';
import ApifyProcessor from './components/ApifyProcessor';
import DataCleaner from './components/DataCleaner';
import TraitExtractor from './components/TraitExtractor';
import AirtableUpdater from './components/AirtableUpdater';
import GlobalSettings from './components/GlobalSettings';
import TerminalLogs from './components/TerminalLogs';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  // Default state starts off in extract tab
  const [activeTab, setActiveTab] = useState('extract');
  // Global filter settings
  const [globalEventFilter, setGlobalEventFilter] = useState('S25');
  const [globalTop100Filter, setGlobalTop100Filter] = useState(true);
  // Global Airtable settings
  const [globalBaseId, setGlobalBaseId] = useState('appCicrQbZaRq1Tvo');
  const [globalTableId, setGlobalTableId] = useState('tblpzAcC0vMMibdca');
  
  // Generate prefix based on event filter and top 100 filter
  const generatePrefix = (eventFilter, top100Filter) => {
    const event = eventFilter || 'S25';
    const suffix = top100Filter ? 'Top100' : 'All';
    return `${event}${suffix}`;
  };
  
  // Initialize global prefix based on default settings
  const [globalPrefix, setGlobalPrefix] = useState(generatePrefix('S25', true));

  const addMessage = (type, message) => {
    const id = Date.now();
    setMessages(prev => [...prev, { id, type, message, timestamp: new Date() }]);
    
    // Auto-remove messages after 5 seconds
    setTimeout(() => {
      setMessages(prev => prev.filter(msg => msg.id !== id));
    }, 5000);
  };

  const handleError = (error) => {
    addMessage('error', error);
  };

  const handleSuccess = (message) => {
    addMessage('success', message);
  };

  const handleJobStarted = (response) => {
    handleSuccess(`Job started successfully! Job ID: ${response.job_id}`);
    setActiveTab('jobs'); // Switch to jobs tab to see the new job
  };

  const handleJobSelected = (results) => {
    if (results.valid_urls) {
      handleSuccess(`Loaded results for job. Found ${results.valid_urls} LinkedIn URLs.`);
    } else if (results.processed_profiles) {
      handleSuccess(`Loaded Apify results. Processed ${results.processed_profiles} profiles.`);
    } else if (results.total_profiles) {
      handleSuccess(`Loaded data cleaner results. Cleaned ${results.total_profiles} profiles.`);
    } else if (results.processed_profiles && results.total_profiles) {
      handleSuccess(`Loaded trait extractor results. Processed ${results.processed_profiles} out of ${results.total_profiles} profiles.`);
    } else if (results.successful_updates) {
      handleSuccess(`Loaded Airtable updater results. Successfully updated ${results.successful_updates} records.`);
    }
  };

  const removeMessage = (id) => {
    setMessages(prev => prev.filter(msg => msg.id !== id));
  };

  const handleGlobalPrefixChange = (newPrefix) => {
    setGlobalPrefix(newPrefix);
  };

  const handleGlobalEventFilterChange = (newEventFilter) => {
    setGlobalEventFilter(newEventFilter);
    // Auto-update prefix if it matches the auto-generated pattern
    const autoPrefix = generatePrefix(newEventFilter, globalTop100Filter);
    if (globalPrefix === generatePrefix(globalEventFilter, globalTop100Filter)) {
      setGlobalPrefix(autoPrefix);
    }
  };

  const handleGlobalTop100FilterChange = (newTop100Filter) => {
    setGlobalTop100Filter(newTop100Filter);
    // Auto-update prefix if it matches the auto-generated pattern
    const autoPrefix = generatePrefix(globalEventFilter, newTop100Filter);
    if (globalPrefix === generatePrefix(globalEventFilter, globalTop100Filter)) {
      setGlobalPrefix(autoPrefix);
    }
  };

  const handleGlobalBaseIdChange = (newBaseId) => {
    setGlobalBaseId(newBaseId);
  };

  const handleGlobalTableIdChange = (newTableId) => {
    setGlobalTableId(newTableId);
  };

  return (
    <div className="App">
      <div className="container">
        <header className="app-header">
          <h1>🚀 Airtable LinkedIn URL Extractor</h1>
          <p>Extract LinkedIn URLs from Airtable, process profiles with Apify, clean data, extract traits, and update Airtable records</p>
        </header>

        {/* Global Settings */}
        <GlobalSettings 
          globalPrefix={globalPrefix}
          onPrefixChange={handleGlobalPrefixChange}
          globalEventFilter={globalEventFilter}
          onEventFilterChange={handleGlobalEventFilterChange}
          globalTop100Filter={globalTop100Filter}
          onTop100FilterChange={handleGlobalTop100FilterChange}
          globalBaseId={globalBaseId}
          onBaseIdChange={handleGlobalBaseIdChange}
          globalTableId={globalTableId}
          onTableIdChange={handleGlobalTableIdChange}
          onError={handleError}
        />

        {/* Messages */}
        {messages.length > 0 && (
          <div className="messages-container">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`message ${msg.type}-message`}
                style={{ position: 'relative' }}
              >
                <span>{msg.message}</span>
                <button
                  onClick={() => removeMessage(msg.id)}
                  style={{
                    position: 'absolute',
                    right: '8px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    fontSize: '18px',
                    cursor: 'pointer',
                    color: 'inherit'
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'extract' ? 'active' : ''}`}
            onClick={() => setActiveTab('extract')}
          >
            Extract URLs
          </button>
          <button
            className={`tab ${activeTab === 'apify' ? 'active' : ''}`}
            onClick={() => setActiveTab('apify')}
          >
            Process with Apify
          </button>
          <button
            className={`tab ${activeTab === 'cleaner' ? 'active' : ''}`}
            onClick={() => setActiveTab('cleaner')}
          >
            Data Cleaner
          </button>
          <button
            className={`tab ${activeTab === 'trait' ? 'active' : ''}`}
            onClick={() => setActiveTab('trait')}
          >
            Trait Extractor
          </button>
          <button
            className={`tab ${activeTab === 'jobs' ? 'active' : ''}`}
            onClick={() => setActiveTab('jobs')}
          >
            View Jobs
          </button>
          <button
            className={`tab ${activeTab === 'health' ? 'active' : ''}`}
            onClick={() => setActiveTab('health')}
          >
            API Health
          </button>
          <button
            className={`tab ${activeTab === 'airtable' ? 'active' : ''}`}
            onClick={() => setActiveTab('airtable')}
          >
            Update Airtable
          </button>
          <button
            className={`tab ${activeTab === 'terminal' ? 'active' : ''}`}
            onClick={() => setActiveTab('terminal')}
          >
            Terminal Logs
          </button>
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {activeTab === 'extract' && (
            <ExtractionForm
              globalPrefix={globalPrefix}
              globalEventFilter={globalEventFilter}
              globalTop100Filter={globalTop100Filter}
              globalBaseId={globalBaseId}
              globalTableId={globalTableId}
              onJobStarted={handleJobStarted}
              onError={handleError}
            />
          )}
          
          {activeTab === 'apify' && (
            <ApifyProcessor
              globalPrefix={globalPrefix}
              onJobStarted={handleJobStarted}
              onError={handleError}
            />
          )}
          
          {activeTab === 'jobs' && (
            <JobList
              onJobSelected={handleJobSelected}
              onError={handleError}
            />
          )}
          
          {activeTab === 'health' && (
            <HealthStatus onError={handleError} />
          )}

          {activeTab === 'cleaner' && (
            <DataCleaner 
              globalPrefix={globalPrefix}
              onError={handleError} 
            />
          )}

          {activeTab === 'trait' && (
            <TraitExtractor 
              globalPrefix={globalPrefix}
              onError={handleError} 
            />
          )}

          {activeTab === 'airtable' && (
            <AirtableUpdater 
              globalPrefix={globalPrefix}
              globalBaseId={globalBaseId}
              globalTableId={globalTableId}
              onError={handleError} 
            />
          )}

          {activeTab === 'terminal' && (
            <TerminalLogs />
          )}
        </div>

        {/* Footer */}
        <footer className="app-footer">
          <p>
            <strong>API Documentation:</strong>{' '}
            <a href="http://localhost:8080/docs" target="_blank" rel="noopener noreferrer">
              http://localhost:8080/docs
            </a>
          </p>
          <p>
            <strong>API Base URL:</strong> http://localhost:8080
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App; 