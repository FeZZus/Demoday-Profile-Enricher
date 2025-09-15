import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

const GlobalSettings = ({ 
  globalPrefix, 
  onPrefixChange, 
  globalEventFilter, 
  onEventFilterChange, 
  globalTop100Filter, 
  onTop100FilterChange,
  globalBaseId,
  onBaseIdChange,
  globalTableId,
  onTableIdChange,
  onError 
}) => {
  const [localEventFilter, setLocalEventFilter] = useState(globalEventFilter || 'S25');
  const [localTop100Filter, setLocalTop100Filter] = useState(globalTop100Filter !== undefined ? globalTop100Filter : true);
  const [localBaseId, setLocalBaseId] = useState(globalBaseId || 'appCicrQbZaRq1Tvo');
  const [localTableId, setLocalTableId] = useState(globalTableId || 'tblpzAcC0vMMibdca');
  
  // Track if user has manually overridden the auto-generated prefix
  const [isPrefixManuallySet, setIsPrefixManuallySet] = useState(false);
  const [localPrefix, setLocalPrefix] = useState(globalPrefix || 'S25Top100');

  // Generate prefix based on event filter and top 100 filter
  const generatePrefix = (eventFilter, top100Filter) => {
    const event = eventFilter || 'S25';
    const suffix = top100Filter ? 'Top100' : 'All';
    return `${event}${suffix}`;
  };

  // Update local prefix when global prefix changes
  useEffect(() => {
    if (!isPrefixManuallySet) {
      const autoPrefix = generatePrefix(globalEventFilter, globalTop100Filter);
      setLocalPrefix(autoPrefix);
    } else {
      setLocalPrefix(globalPrefix || 'S25Top100');
    }
  }, [globalPrefix, globalEventFilter, globalTop100Filter, isPrefixManuallySet]);

  useEffect(() => {
    setLocalEventFilter(globalEventFilter || 'S25');
  }, [globalEventFilter]);

  useEffect(() => {
    setLocalTop100Filter(globalTop100Filter !== undefined ? globalTop100Filter : true);
  }, [globalTop100Filter]);

  useEffect(() => {
    setLocalBaseId(globalBaseId || 'appCicrQbZaRq1Tvo');
  }, [globalBaseId]);

  useEffect(() => {
    setLocalTableId(globalTableId || 'tblpzAcC0vMMibdca');
  }, [globalTableId]);

  const handlePrefixChange = (e) => {
    const newPrefix = e.target.value;
    setLocalPrefix(newPrefix);
    setIsPrefixManuallySet(true); // Mark as manually set
    if (onPrefixChange) {
      onPrefixChange(newPrefix);
    }
  };

  const handleEventFilterChange = (e) => {
    const newEventFilter = e.target.value;
    setLocalEventFilter(newEventFilter);
    
    // Auto-update prefix if not manually set
    if (!isPrefixManuallySet) {
      const newPrefix = generatePrefix(newEventFilter, localTop100Filter);
      setLocalPrefix(newPrefix);
      if (onPrefixChange) {
        onPrefixChange(newPrefix);
      }
    }
    
    if (onEventFilterChange) {
      onEventFilterChange(newEventFilter);
    }
  };

  const handleTop100FilterChange = (e) => {
    const newTop100Filter = e.target.checked;
    setLocalTop100Filter(newTop100Filter);
    
    // Auto-update prefix if not manually set
    if (!isPrefixManuallySet) {
      const newPrefix = generatePrefix(localEventFilter, newTop100Filter);
      setLocalPrefix(newPrefix);
      if (onPrefixChange) {
        onPrefixChange(newPrefix);
      }
    }
    
    if (onTop100FilterChange) {
      onTop100FilterChange(newTop100Filter);
    }
  };

  const handleBaseIdChange = (e) => {
    const newBaseId = e.target.value;
    setLocalBaseId(newBaseId);
    if (onBaseIdChange) {
      onBaseIdChange(newBaseId);
    }
  };

  const handleTableIdChange = (e) => {
    const newTableId = e.target.value;
    setLocalTableId(newTableId);
    if (onTableIdChange) {
      onTableIdChange(newTableId);
    }
  };

  const handleResetPrefix = () => {
    const autoPrefix = generatePrefix(localEventFilter, localTop100Filter);
    setLocalPrefix(autoPrefix);
    setIsPrefixManuallySet(false);
    if (onPrefixChange) {
      onPrefixChange(autoPrefix);
    }
  };

  const [isCancellingAll, setIsCancellingAll] = useState(false);

  const handleEmergencyRestart = async () => {
    if (!window.confirm('🚨 EMERGENCY RESTART: This will kill ALL processes and restart the entire application. This action cannot be undone. Continue?')) {
      return;
    }

    setIsCancellingAll(true);
    try {
      const results = await apiService.emergencyRestart();
      
      if (onError) {
        onError(`🚨 Emergency restart initiated: ${results.message}. Services will restart in a new window.`);
      }
      
      // Log detailed results
      console.log('Emergency restart results:', results);
      
    } catch (error) {
      if (onError) {
        onError(`Failed to initiate emergency restart: ${error.message}`);
      }
    } finally {
      setIsCancellingAll(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: '20px' }}>
      <h3>⚙️ Global Settings</h3>
      
      <div className="form-group">
        <label className="form-label">Global Output Prefix</label>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            className="form-control"
            value={localPrefix}
            onChange={handlePrefixChange}
            placeholder="S25Top100"
            style={{ flex: 1 }}
          />
          {isPrefixManuallySet && (
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={handleResetPrefix}
              style={{ whiteSpace: 'nowrap' }}
              title="Reset to auto-generated prefix"
            >
              🔄 Reset
            </button>
          )}
        </div>
        <small>
          {isPrefixManuallySet ? (
            <>
              Custom prefix set. Click "Reset" to auto-generate based on Event Filter and Top 100 Filter.
              <br />
              <strong>Auto-generated would be:</strong> {generatePrefix(localEventFilter, localTop100Filter)}
            </>
          ) : (
            <>
              Auto-generated from Event Filter and Top 100 Filter. 
              <br />
              <strong>Current:</strong> {generatePrefix(localEventFilter, localTop100Filter)}
            </>
          )}
        </small>
      </div>

      <div className="form-group">
        <label className="form-label">Event Filter</label>
        <input
          type="text"
          className="form-control"
          value={localEventFilter}
          onChange={handleEventFilterChange}
          placeholder="S25"
        />
        <small>Filter records by event (e.g., S25, W24) - applies to all operations</small>
      </div>

      <div className="form-group">
        <label className="form-label">
          <input
            type="checkbox"
            checked={localTop100Filter}
            onChange={handleTop100FilterChange}
            style={{ marginRight: '8px' }}
          />
          Top 100 Filter Only
        </label>
        <small>Only process records marked as "Top 100" - applies to all operations</small>
      </div>

      <div className="form-group">
        <label className="form-label">Airtable Base ID</label>
        <input
          type="text"
          className="form-control"
          value={localBaseId}
          onChange={handleBaseIdChange}
          placeholder="appCicrQbZaRq1Tvo"
        />
        <small>
          The Airtable base ID to connect to. Found in your Airtable URL:   https://airtable.com/appXXXXXXXXXXXXX
        </small>
      </div>

      <div className="form-group">
        <label className="form-label">Airtable Table ID</label>
        <input
          type="text"
          className="form-control"
          value={localTableId}
          onChange={handleTableIdChange}
          placeholder="tblpzAcC0vMMibdca"
        />
        <small>
          The Airtable table ID to connect to. Found in your table URL or API documentation. Default is 'Startup' table
        </small>
      </div>

      <div className="form-group">
        <label className="form-label">🚨 Emergency Stop</label>
        <button
          className="btn btn-danger emergency-stop"
          onClick={handleEmergencyRestart}
          disabled={isCancellingAll}
          style={{ 
            width: '100%',
            marginTop: '8px'
          }}
        >
          {isCancellingAll ? 'Emergency Restarting...' : '🚨 EMERGENCY RESTART'}
        </button>
        <small>
          This will kill ALL processes (including this application) and restart the entire system.
          Use this as a last resort if jobs are completely stuck or the application is unresponsive.
          A new window will open with the restarted services.
        </small>
      </div>
    </div>
  );
};

export default GlobalSettings; 