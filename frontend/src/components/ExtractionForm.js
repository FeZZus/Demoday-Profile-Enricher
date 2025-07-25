import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

const ExtractionForm = ({ globalPrefix, globalEventFilter, globalTop100Filter, onJobStarted, onError }) => {
  const [formData, setFormData] = useState({
    linkedin_fields: ["4. CEO LinkedIn"],
    event_filter: globalEventFilter || "S25",
    top_100_filter: globalTop100Filter !== undefined ? globalTop100Filter : true,
    output_prefix: globalPrefix || "S25Top100",
    job_id: "",
  });

  const [isLoading, setIsLoading] = useState(false);

  // Update form data when global settings change
  useEffect(() => {
    setFormData(prev => ({
      ...prev,
      output_prefix: globalPrefix || "S25Top100",
      event_filter: globalEventFilter || "S25",
      top_100_filter: globalTop100Filter !== undefined ? globalTop100Filter : true
    }));
  }, [globalPrefix, globalEventFilter, globalTop100Filter]);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Prepare config for API
      const config = {
        linkedin_fields: formData.linkedin_fields,
        event_filter: formData.event_filter,
        top_100_filter: formData.top_100_filter,
        output_prefix: formData.output_prefix,
        job_id: formData.job_id || null,
      };

      const response = await apiService.startExtraction(config);
      
      if (onJobStarted) {
        onJobStarted(response);
      }
      
      // Reset form
      setFormData({
        linkedin_fields: ["4. CEO LinkedIn"],
        event_filter: "S25",
        top_100_filter: true,
        output_prefix: globalPrefix || "S25Top100",
        job_id: "",
      });

    } catch (error) {
      if (onError) {
        onError(error.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Start LinkedIn URL Extraction</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">LinkedIn Fields</label>
          <input
            type="text"
            className="form-control"
            name="linkedin_fields"
            value={formData.linkedin_fields.join(', ')}
            onChange={(e) => setFormData(prev => ({
              ...prev,
              linkedin_fields: e.target.value.split(',').map(field => field.trim())
            }))}
            placeholder="4. CEO LinkedIn, Alternative LinkedIn Field"
          />
          <small>Comma-separated list of Airtable field names</small>
        </div>

        <div className="form-group">
          <label className="form-label">Output Prefix</label>
          <input
            type="text"
            className="form-control"
            name="output_prefix"
            value={formData.output_prefix}
            onChange={handleInputChange}
            placeholder="S25Top100"
          />
          <small>Prefix for output files (e.g., S25Top100, MyExtraction) - Uses global prefix by default</small>
        </div>

        <div className="form-group">
          <label className="form-label">Custom Job ID (Optional)</label>
          <input
            type="text"
            className="form-control"
            name="job_id"
            value={formData.job_id}
            onChange={handleInputChange}
            placeholder="my_custom_job_123"
          />
          <small>Leave empty to auto-generate a job ID</small>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <span className="loading" style={{ marginRight: '8px' }}></span>
              Starting Extraction...
            </>
          ) : (
            'Start Extraction'
          )}
        </button>
      </form>
    </div>
  );
};

export default ExtractionForm; 