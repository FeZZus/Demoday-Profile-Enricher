import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

const DataCleaner = ({ globalPrefix, onJobStarted, onError }) => {
  const [formData, setFormData] = useState({
    input_file: `apify-profile-data/${globalPrefix || 'S25Top100'}linkedin_profile_data.json`,
    output_file: `cleaned-profile-data/${globalPrefix || 'S25Top100'}cleaned_linkedin_data.json`,
  });

  const [isLoading, setIsLoading] = useState(false);

  // Update file paths when globalPrefix changes
  useEffect(() => {
    setFormData(prev => ({
      ...prev,
      input_file: `apify-profile-data/${globalPrefix || 'S25Top100'}linkedin_profile_data.json`,
      output_file: `cleaned-profile-data/${globalPrefix || 'S25Top100'}cleaned_linkedin_data.json`,
    }));
  }, [globalPrefix]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const config = {
        input_file: formData.input_file,
        output_file: formData.output_file,
      };

      const result = await apiService.startDataCleaning(config);
      
      if (onJobStarted) {
        onJobStarted(result);
      }
      
      // Reset form
      setFormData({
        input_file: `apify-profile-data/${globalPrefix || 'S25Top100'}linkedin_profile_data.json`,
        output_file: `cleaned-profile-data/${globalPrefix || 'S25Top100'}cleaned_linkedin_data.json`,
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
      <h2>🧹 Clean LinkedIn Profile Data</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Clean and process LinkedIn profile data by removing irrelevant fields, 
        cleaning text content, and organizing the data for trait extraction.
      </p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Input File Path</label>
          <input
            type="text"
            className="form-control"
            name="input_file"
            value={formData.input_file}
            onChange={handleInputChange}
            placeholder="apify-profile-data/S25Top100linkedin_profile_data.json"
          />
          <small>Path to the JSON file containing raw LinkedIn profile data from Apify - Uses global prefix</small>
        </div>

        <div className="form-group">
          <label className="form-label">Output File Path</label>
          <input
            type="text"
            className="form-control"
            name="output_file"
            value={formData.output_file}
            onChange={handleInputChange}
            placeholder="cleaned-profile-data/S25Top100cleaned_linkedin_data.json"
          />
          <small>Path to save the cleaned profile data - Uses global prefix</small>
        </div>

        <div style={{ 
          backgroundColor: '#f8f9fa', 
          padding: '16px', 
          borderRadius: '6px', 
          marginBottom: '20px',
          border: '1px solid #dee2e6'
        }}>
          <h4 style={{ margin: '0 0 12px 0', color: '#495057' }}>🧹 Cleaning Process:</h4>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#6c757d' }}>
            <li>Removes irrelevant fields (profile pics, media links, etc.)</li>
            <li>Cleans text content by removing URLs and media components</li>
            <li>Extracts and organizes experience descriptions</li>
            <li>Processes education and skills data</li>
            <li>Maintains essential profile information</li>
            <li>Optimizes data structure for trait extraction</li>
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
              Starting Data Cleaning...
            </>
          ) : (
            '🧹 Start Data Cleaning'
          )}
        </button>
      </form>
    </div>
  );
};

export default DataCleaner; 