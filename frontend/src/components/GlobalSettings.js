import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

const GlobalSettings = ({ globalPrefix, onPrefixChange, globalEventFilter, onEventFilterChange, globalTop100Filter, onTop100FilterChange, onError }) => {
  const [localPrefix, setLocalPrefix] = useState(globalPrefix || 'S25Top100');
  const [localEventFilter, setLocalEventFilter] = useState(globalEventFilter || 'S25');
  const [localTop100Filter, setLocalTop100Filter] = useState(globalTop100Filter !== undefined ? globalTop100Filter : true);

  useEffect(() => {
    setLocalPrefix(globalPrefix || 'S25Top100');
  }, [globalPrefix]);

  useEffect(() => {
    setLocalEventFilter(globalEventFilter || 'S25');
  }, [globalEventFilter]);

  useEffect(() => {
    setLocalTop100Filter(globalTop100Filter !== undefined ? globalTop100Filter : true);
  }, [globalTop100Filter]);

  const handlePrefixChange = (e) => {
    const newPrefix = e.target.value;
    setLocalPrefix(newPrefix);
    if (onPrefixChange) {
      onPrefixChange(newPrefix);
    }
  };

  const handleEventFilterChange = (e) => {
    const newEventFilter = e.target.value;
    setLocalEventFilter(newEventFilter);
    if (onEventFilterChange) {
      onEventFilterChange(newEventFilter);
    }
  };

  const handleTop100FilterChange = (e) => {
    const newTop100Filter = e.target.checked;
    setLocalTop100Filter(newTop100Filter);
    if (onTop100FilterChange) {
      onTop100FilterChange(newTop100Filter);
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
        <input
          type="text"
          className="form-control"
          value={localPrefix}
          onChange={handlePrefixChange}
          placeholder="S25Top100"
        />
        <small>
          This prefix will be used for all input and output files across all sections. 
          Examples: S25Top100, MyProject, TestRun
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