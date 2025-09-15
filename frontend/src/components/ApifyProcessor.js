import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

const ApifyProcessor = ({ globalPrefix, onJobStarted, onError }) => {
  const [formData, setFormData] = useState({
    urls_file: `airtable-extractions/${globalPrefix || 'S25Top100'}linkedin_urls_for_apify.json`,
    output_file: `apify-profile-data/${globalPrefix || 'S25Top100'}linkedin_profile_data.json`,
    batch_size: 50,
    test_mode: true,
    test_num_urls: 10,
    force_restart: false,
  });

  const [isLoading, setIsLoading] = useState(false);

  // Update file paths when globalPrefix changes
  useEffect(() => {
    setFormData(prev => ({
      ...prev,
      urls_file: `airtable-extractions/${globalPrefix || 'S25Top100'}linkedin_urls_for_apify.json`,
      output_file: `apify-profile-data/${globalPrefix || 'S25Top100'}linkedin_profile_data.json`,
    }));
  }, [globalPrefix]);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const config = {
        urls_file: formData.urls_file,
        output_file: formData.output_file,
        batch_size: formData.batch_size,
        test_mode: formData.test_mode,
        test_num_urls: formData.test_num_urls,
        force_restart: formData.force_restart,
      };

      const result = await apiService.startApifyProcessing(config);
      
      if (onJobStarted) {
        onJobStarted(result);
      }
      
      // Reset form
      setFormData({
        urls_file: `airtable-extractions/${globalPrefix || 'S25Top100'}linkedin_urls_for_apify.json`,
        output_file: `apify-profile-data/${globalPrefix || 'S25Top100'}linkedin_profile_data.json`,
        batch_size: 50,
        test_mode: true,
        test_num_urls: 10,
        force_restart: false,
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
      <h2>🚀 Process LinkedIn Profiles with Apify</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Process LinkedIn URLs through Apify to extract profile data. 
        This will use your APIFY_API_KEY environment variable.
      </p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">URLs File Path</label>
          <input
            type="text"
            className="form-control"
            name="urls_file"
            value={formData.urls_file}
            onChange={handleInputChange}
            placeholder="airtable-extractions/S25Top100linkedin_urls_for_apify.json"
          />
          <small>Path to the JSON file containing LinkedIn URLs - Uses global prefix</small>
        </div>

        <div className="form-group">
          <label className="form-label">Output File Path</label>
          <input
            type="text"
            className="form-control"
            name="output_file"
            value={formData.output_file}
            onChange={handleInputChange}
            placeholder="apify-profile-data/S25Top100linkedin_profile_data.json"
          />
          <small>Path to save the processed profile data - Uses global prefix</small>
        </div>

        <div className="form-group">
          <label className="form-label">Batch Size</label>
          <input
            type="number"
            className="form-control"
            name="batch_size"
            value={formData.batch_size}
            onChange={handleInputChange}
            min="1"
            max="100"
          />
          <small>Number of URLs to process in each batch (1-100)</small>
        </div>

        <div className="form-group">
          <label className="form-label">
            <input
              type="checkbox"
              name="test_mode"
              checked={formData.test_mode}
              onChange={handleInputChange}
              style={{ marginRight: '8px' }}
            />
            Test Mode (Process Limited URLs)
          </label>
          <small>Enable to process only a few URLs for testing</small>
        </div>

        {formData.test_mode && (
          <div className="form-group">
            <label className="form-label">Test URLs Count</label>
            <input
              type="number"
              className="form-control"
              name="test_num_urls"
              value={formData.test_num_urls}
              onChange={handleInputChange}
              min="1"
              max="100"
            />
            <small>Number of URLs to process in test mode</small>
          </div>
        )}

        <div className="form-group">
          <label className="form-label">
            <input
              type="checkbox"
              name="force_restart"
              checked={formData.force_restart}
              onChange={handleInputChange}
              style={{ marginRight: '8px' }}
            />
            Force Restart (Clear Progress)
          </label>
          <small>Clear existing progress and start from the beginning</small>
        </div>

        <div style={{ 
          backgroundColor: '#f8f9fa', 
          padding: '16px', 
          borderRadius: '6px', 
          marginBottom: '20px',
          border: '1px solid #dee2e6'
        }}>
          <h4 style={{ margin: '0 0 12px 0', color: '#495057' }}>⚠️ Important Notes:</h4>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#6c757d' }}>
            <li>Make sure APIFY_API_KEY is set in your environment</li>
            <li>Test mode is recommended for first-time use</li>
            <li>Processing can take several minutes for large datasets</li>
            <li>Results are saved incrementally to prevent data loss</li>
          </ul>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <span className="loading" style={{ marginRight: '8px' }}></span>
              Starting Apify Processing...
            </>
          ) : (
            '🚀 Start Apify Processing'
          )}
        </button>
      </form>
    </div>
  );
};

export default ApifyProcessor; 