import React, { useState, useEffect, useRef } from 'react';
import { apiService } from '../api';

const TerminalLogs = () => {
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const logsEndRef = useRef(null);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  const fetchLogs = async () => {
    try {
      setIsLoading(true);
      // This would be a new endpoint we need to add to the backend
      const response = await apiService.getTerminalLogs();
      if (response.logs) {
        setLogs(response.logs);
        setIsConnected(true);
      }
    } catch (error) {
      console.warn('Could not fetch terminal logs:', error.message);
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  // Poll for new logs every 2 seconds
  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  const formatLog = (log) => {
    const timestamp = new Date(log.timestamp).toLocaleTimeString();
    let className = 'log-line';
    
    if (log.level === 'ERROR') className += ' error';
    else if (log.level === 'WARNING') className += ' warning';
    else if (log.level === 'INFO') className += ' info';
    
    return (
      <div key={log.id} className={className}>
        <span className="timestamp">[{timestamp}]</span>
        <span className="level">[{log.level}]</span>
        <span className="message">{log.message}</span>
      </div>
    );
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Terminal Logs</h2>
        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            fontSize: '14px',
            color: isConnected ? '#28a745' : '#dc3545'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isConnected ? '#28a745' : '#dc3545'
            }}></div>
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
          <button className="btn btn-secondary" onClick={fetchLogs} disabled={isLoading}>
            {isLoading ? 'Loading...' : 'Refresh'}
          </button>
          <button className="btn btn-outline-danger" onClick={clearLogs}>
            Clear
          </button>
        </div>
      </div>

      <div className="terminal-container">
        <div className="terminal-header">
          <span>Backend Terminal Output</span>
        </div>
        <div className="terminal-content">
          {logs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
              <p>No logs available</p>
              <p style={{ fontSize: '14px', marginTop: '8px' }}>
                Start a job to see real-time terminal output here.
              </p>
            </div>
          ) : (
            <div className="logs-container">
              {logs.map(formatLog)}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .terminal-container {
          border: 1px solid #ddd;
          border-radius: 4px;
          overflow: hidden;
        }
        
        .terminal-header {
          background-color: #f8f9fa;
          padding: 8px 12px;
          border-bottom: 1px solid #ddd;
          font-family: 'Courier New', monospace;
          font-size: 14px;
          color: #666;
        }
        
        .terminal-content {
          background-color: #1e1e1e;
          color: #f8f8f2;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          line-height: 1.4;
          max-height: 400px;
          overflow-y: auto;
        }
        
        .logs-container {
          padding: 12px;
        }
        
        .log-line {
          margin-bottom: 2px;
          word-wrap: break-word;
        }
        
        .log-line .timestamp {
          color: #888;
          margin-right: 8px;
        }
        
        .log-line .level {
          color: #ffd700;
          margin-right: 8px;
          font-weight: bold;
        }
        
        .log-line.error .level {
          color: #ff6b6b;
        }
        
        .log-line.warning .level {
          color: #ffa500;
        }
        
        .log-line.info .level {
          color: #87ceeb;
        }
        
        .log-line .message {
          color: #f8f8f2;
        }
      `}</style>
    </div>
  );
};

export default TerminalLogs; 