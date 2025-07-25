import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../api';

const HealthStatus = ({ onError }) => {
  const [health, setHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkHealth = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await apiService.checkHealth();
      setHealth(response);
    } catch (error) {
      setHealth({ status: 'unhealthy', error: error.message });
      if (onError) {
        onError(error.message);
      }
    } finally {
      setIsLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    checkHealth();
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return '#28a745';
      case 'unhealthy':
        return '#dc3545';
      default:
        return '#ffc107';
    }
  };

  if (isLoading) {
    return (
      <div className="card">
        <h2>API Health Status</h2>
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <span className="loading"></span>
          <p>Checking API health...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>API Health Status</h2>
      {health ? (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
            <div
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor: getStatusColor(health.status),
                marginRight: '8px'
              }}
            ></div>
            <span style={{ fontWeight: 'bold', textTransform: 'uppercase' }}>
              {health.status}
            </span>
          </div>

          <div className="job-details">
            <div className="detail-item">
              <span className="detail-label">Active Jobs:</span>
              <span className="detail-value">{health.active_jobs || 0}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Total Jobs:</span>
              <span className="detail-value">{health.total_jobs || 0}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Last Check:</span>
              <span className="detail-value">
                {health.timestamp ? new Date(health.timestamp).toLocaleString() : 'N/A'}
              </span>
            </div>
          </div>

          {health.error && (
            <div className="error-message">
              <strong>Error:</strong> {health.error}
            </div>
          )}

          <button className="btn btn-secondary" onClick={checkHealth}>
            Refresh Health Check
          </button>
        </div>
      ) : (
        <p>Unable to check API health</p>
      )}
    </div>
  );
};

export default HealthStatus; 