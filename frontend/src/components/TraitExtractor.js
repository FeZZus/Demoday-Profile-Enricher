import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

const TraitExtractor = ({ globalPrefix, onJobStarted, onError }) => {
  const [formData, setFormData] = useState({
    input_file: `cleaned-profile-data/${globalPrefix || 'S25Top100'}cleaned_linkedin_data.json`,
    output_file: `final-trait-extractions/${globalPrefix || 'S25Top100'}_comprehensive_traits.json`,
    max_profiles: -1,
    force_reextraction: false,
    delay_between_calls: 1.0,
  });

  const [isLoading, setIsLoading] = useState(false);

  // Update file paths when globalPrefix changes
  useEffect(() => {
    setFormData(prev => ({
      ...prev,
      input_file: `cleaned-profile-data/${globalPrefix || 'S25Top100'}cleaned_linkedin_data.json`,
      output_file: `final-trait-extractions/${globalPrefix || 'S25Top100'}_comprehensive_traits.json`,
    }));
  }, [globalPrefix]);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseFloat(value) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const config = {
        input_file: formData.input_file,
        output_file: formData.output_file,
        max_profiles: formData.max_profiles,
        force_reextraction: formData.force_reextraction,
        delay_between_calls: formData.delay_between_calls,
      };

      const result = await apiService.startTraitExtraction(config);
      
      if (onJobStarted) {
        onJobStarted(result);
      }
      
      // Reset form
      setFormData({
        input_file: `cleaned-profile-data/${globalPrefix || 'S25Top100'}cleaned_linkedin_data.json`,
        output_file: `final-trait-extractions/${globalPrefix || 'S25Top100'}_comprehensive_traits.json`,
        max_profiles: -1,
        force_reextraction: false,
        delay_between_calls: 1.0,
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
      <h2>🧠 Extract Traits from LinkedIn Profiles</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Extract comprehensive traits and insights from cleaned LinkedIn profile data using AI analysis.
        This will use your OPENAI_API_KEY environment variable.
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
            placeholder="cleaned-profile-data/S25Top100cleaned_linkedin_data.json"
          />
          <small>Path to the cleaned LinkedIn profiles JSON file - Uses global prefix</small>
        </div>

        <div className="form-group">
          <label className="form-label">Output File Path</label>
          <input
            type="text"
            className="form-control"
            name="output_file"
            value={formData.output_file}
            onChange={handleInputChange}
            placeholder="final-trait-extractions/S25Top100_comprehensive_traits.json"
          />
          <small>Path to save the extracted traits data - Uses global prefix</small>
        </div>

        <div className="form-group">
          <label className="form-label">Max Profiles to Process</label>
          <input
            type="number"
            className="form-control"
            name="max_profiles"
            value={formData.max_profiles}
            onChange={handleInputChange}
            min="-1"
            max="1000"
          />
          <small>Maximum profiles to process in this session (-1 for all remaining)</small>
        </div>

        <div className="form-group">
          <label className="form-label">Delay Between API Calls (seconds)</label>
          <input
            type="number"
            className="form-control"
            name="delay_between_calls"
            value={formData.delay_between_calls}
            onChange={handleInputChange}
            min="0.5"
            max="5.0"
            step="0.1"
          />
          <small>Delay between OpenAI API calls to avoid rate limits</small>
        </div>

        <div className="form-group">
          <label className="form-label">
            <input
              type="checkbox"
              name="force_reextraction"
              checked={formData.force_reextraction}
              onChange={handleInputChange}
              style={{ marginRight: '8px' }}
            />
            Force Re-extraction (Process All Profiles Again)
          </label>
          <small>Enable to re-extract all profiles even if already processed (useful after changing system prompt)</small>
        </div>

        <div style={{ 
          backgroundColor: '#f8f9fa', 
          padding: '16px', 
          borderRadius: '6px', 
          marginBottom: '20px',
          border: '1px solid #dee2e6'
        }}>
          <h4 style={{ margin: '0 0 12px 0', color: '#495057' }}>🧠 Trait Extraction Process:</h4>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#6c757d' }}>
            <li>Extracts estimated age from education dates</li>
            <li>Analyzes career progression and job hopping patterns</li>
            <li>Identifies notable companies and startup experience</li>
            <li>Detects accelerator programs and board positions</li>
            <li>Analyzes education-career alignment and pivots</li>
            <li>Extracts personal brand and thought leadership indicators</li>
            <li>Identifies research/academic experience</li>
            <li>Maps international work experience</li>
            <li>Provides confidence scores based on data completeness</li>
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
            <li>Make sure OPENAI_API_KEY is set in your environment</li>
            <li>Processing can take several minutes for large datasets</li>
            <li>Results are saved incrementally to prevent data loss</li>
            <li>Use force re-extraction only when changing system prompts</li>
            <li>Higher delay values reduce API rate limit issues</li>
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
              Starting Trait Extraction...
            </>
          ) : (
            '🧠 Start Trait Extraction'
          )}
        </button>
      </form>
    </div>
  );
};

export default TraitExtractor; 