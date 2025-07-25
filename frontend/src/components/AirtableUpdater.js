import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

const AirtableUpdater = ({ globalPrefix, onJobStarted, onError }) => {
  const [formData, setFormData] = useState({
    traits_file: `final-trait-extractions/${globalPrefix || 'S25Top100'}_comprehensive_traits.json`,
    url_mapping_file: `airtable-extractions/${globalPrefix || 'S25Top100'}airtable_url_mapping.json`,
    delay_between_updates: 0.5,
  });

  const [isLoading, setIsLoading] = useState(false);

  // Update file paths when globalPrefix changes
  useEffect(() => {
    setFormData(prev => ({
      ...prev,
      traits_file: `final-trait-extractions/${globalPrefix || 'S25Top100'}_comprehensive_traits.json`,
      url_mapping_file: `airtable-extractions/${globalPrefix || 'S25Top100'}airtable_url_mapping.json`,
    }));
  }, [globalPrefix]);

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const config = {
        traits_file: formData.traits_file,
        url_mapping_file: formData.url_mapping_file,
        delay_between_updates: formData.delay_between_updates,
      };

      const result = await apiService.startAirtableUpdate(config);
      
      if (onJobStarted) {
        onJobStarted(result);
      }
      
      // Reset form
      setFormData({
        traits_file: `final-trait-extractions/${globalPrefix || 'S25Top100'}_comprehensive_traits.json`,
        url_mapping_file: `airtable-extractions/${globalPrefix || 'S25Top100'}airtable_url_mapping.json`,
        delay_between_updates: 0.5,
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
      <h2>📊 Update Airtable with Extracted Traits</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Update Airtable records with comprehensive trait extraction results by mapping LinkedIn URLs to Airtable record IDs.
        This will use your AIRTABLE_API_KEY environment variable.
      </p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Traits File Path</label>
          <input
            type="text"
            className="form-control"
            name="traits_file"
            value={formData.traits_file}
            onChange={handleInputChange}
            placeholder="final-trait-extractions/S25Top100_comprehensive_traits.json"
          />
          <small>Path to the trait extraction results JSON file - Uses global prefix</small>
        </div>

        <div className="form-group">
          <label className="form-label">URL Mapping File Path</label>
          <input
            type="text"
            className="form-control"
            name="url_mapping_file"
            value={formData.url_mapping_file}
            onChange={handleInputChange}
            placeholder="airtable-extractions/S25Top100airtable_url_mapping.json"
          />
          <small>Path to the URL mapping JSON file that links LinkedIn URLs to Airtable record IDs - Uses global prefix</small>
        </div>

        <div className="form-group">
          <label className="form-label">Delay Between Updates (seconds)</label>
          <input
            type="number"
            className="form-control"
            name="delay_between_updates"
            value={formData.delay_between_updates}
            onChange={handleInputChange}
            min="0.1"
            max="2.0"
            step="0.1"
          />
          <small>Delay between Airtable API calls to avoid rate limits</small>
        </div>

        <div style={{ 
          backgroundColor: '#f8f9fa', 
          padding: '16px', 
          borderRadius: '6px', 
          marginBottom: '20px',
          border: '1px solid #dee2e6'
        }}>
          <h4 style={{ margin: '0 0 12px 0', color: '#495057' }}>📊 Airtable Update Process:</h4>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#6c757d' }}>
            <li>Loads trait extraction results from JSON file</li>
            <li>Maps LinkedIn URLs to Airtable record IDs</li>
            <li>Formats trait data for Airtable fields</li>
            <li>Updates each Airtable record with extracted traits</li>
            <li>Provides detailed success/failure statistics</li>
            <li>Handles missing mappings and errors gracefully</li>
          </ul>
        </div>

        <div style={{ 
          backgroundColor: '#d1ecf1', 
          padding: '16px', 
          borderRadius: '6px', 
          marginBottom: '20px',
          border: '1px solid #bee5eb'
        }}>
          <h4 style={{ margin: '0 0 12px 0', color: '#0c5460' }}>📋 Airtable Fields Updated:</h4>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#0c5460' }}>
            <li>AI_Full_Name, AI_Estimated_Age, AI_Confidence_Score</li>
            <li>AI_Undergraduate, AI_Masters, AI_PhD, AI_Other_Education</li>
            <li>AI_Total_Years_Experience, AI_Avg_Tenure_Per_Role, AI_Job_Hopper</li>
            <li>AI_Total_Experience_Count, AI_Has_Leadership_Experience</li>
            <li>AI_Has_C_Suite_Experience, AI_Founder_Experience_Count</li>
            <li>AI_Industry_Switches, AI_Career_Summary</li>
            <li>AI_Notable_Companies, AI_Startup_Companies</li>
            <li>AI_Accelerators, AI_Fellowship_Programs, AI_Board_Positions</li>
            <li>AI_Studies_Field, AI_Current_Field, AI_Pivot_Description</li>
            <li>AI_Headline_Keywords, AI_Academic_Roles, AI_Countries_Worked</li>
          </ul>
        </div>

        <div style={{ 
          backgroundColor: '#fff3cd', 
          padding: '16px', 
          borderRadius: '6px', 
          marginBottom: '20px',
          border: '1px solid #ffeaa7'
        }}>
          <h4 style={{ margin: '0 0 12px 0', color: '#856404' }}>⚠️ Important Notes:</h4>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#856404' }}>
            <li>Make sure AIRTABLE_API_KEY is set in your environment</li>
            <li>Ensure trait extraction has been completed first</li>
            <li>URL mapping file must exist from extraction process</li>
            <li>Updates are performed incrementally with rate limiting</li>
            <li>Missing mappings will be reported but won't stop the process</li>
            <li>Check job results for detailed success/failure statistics</li>
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
              Starting Airtable Update...
            </>
          ) : (
            '📊 Start Airtable Update'
          )}
        </button>
      </form>
    </div>
  );
};

export default AirtableUpdater; 