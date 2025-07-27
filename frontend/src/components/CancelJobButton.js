import React, { useState } from 'react';
import { apiService } from '../api';

const CancelJobButton = ({ jobId, jobType, onCancel, onError, disabled = false }) => {
  const [isCancelling, setIsCancelling] = useState(false);

  const handleCancel = async () => {
    if (!window.confirm(`Are you sure you want to cancel job ${jobId}? This action cannot be undone.`)) {
      return;
    }

    setIsCancelling(true);
    try {
      let response;
      
      switch (jobType) {
        case 'apify':
          response = await apiService.cancelApifyJob(jobId);
          break;
        case 'cleaner':
          response = await apiService.cancelDataCleanerJob(jobId);
          break;
        case 'traits':
          response = await apiService.cancelTraitExtractorJob(jobId);
          break;
        case 'airtable':
          response = await apiService.cancelAirtableUpdaterJob(jobId);
          break;
        default:
          response = await apiService.cancelJob(jobId);
          break;
      }

      if (onCancel) {
        onCancel(jobId, response);
      }
    } catch (error) {
      if (onError) {
        onError(`Failed to cancel job: ${error.message}`);
      }
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <button
      className="btn btn-warning"
      onClick={handleCancel}
      disabled={disabled || isCancelling}
      style={{ 
        marginRight: '8px',
        backgroundColor: '#ffc107',
        borderColor: '#ffc107',
        color: '#212529'
      }}
    >
      {isCancelling ? 'Cancelling...' : 'Cancel'}
    </button>
  );
};

export default CancelJobButton; 