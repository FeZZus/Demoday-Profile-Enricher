import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../api';
import CancelJobButton from './CancelJobButton';

const JobList = ({ onJobSelected, onError }) => {
  const [extractionJobs, setExtractionJobs] = useState([]);
  const [apifyJobs, setApifyJobs] = useState([]);
  const [cleanerJobs, setCleanerJobs] = useState([]);
  const [traitJobs, setTraitJobs] = useState([]);
  const [airtableJobs, setAirtableJobs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobResults, setJobResults] = useState(null);
  const [activeTab, setActiveTab] = useState('extraction'); // 'extraction', 'apify', 'cleaner', 'traits', or 'airtable'
  const [retryCount, setRetryCount] = useState(0);
  const [runningJobs, setRunningJobs] = useState(new Set());

  const loadJobs = useCallback(async (retry = false) => {
    try {
      if (!retry) {
        setIsLoading(true);
      }
      
      // Load all types of jobs with individual error handling
      const loadJobType = async (apiCall, fallback = []) => {
        try {
          const response = await apiCall();
          return response.jobs || fallback;
        } catch (error) {
          console.warn('Failed to load job type:', error.message);
          return fallback;
        }
      };
      
      // Load jobs sequentially to reduce server load
      const extractionResponse = await loadJobType(() => apiService.listJobs());
      const apifyResponse = await loadJobType(() => apiService.listApifyJobs());
      const cleanerResponse = await loadJobType(() => apiService.listDataCleanerJobs());
      const traitResponse = await loadJobType(() => apiService.listTraitExtractorJobs());
      const airtableResponse = await loadJobType(() => apiService.listAirtableUpdaterJobs());
      
      setExtractionJobs(extractionResponse);
      setApifyJobs(apifyResponse);
      setCleanerJobs(cleanerResponse);
      setTraitJobs(traitResponse);
      setAirtableJobs(airtableResponse);
      setRetryCount(0); // Reset retry count on success
      
      // Track running jobs for more frequent updates
      const running = new Set();
      [...extractionResponse, ...apifyResponse, ...cleanerResponse, ...traitResponse, ...airtableResponse].forEach(job => {
        if (job.status === 'running') {
          running.add(job.job_id);
        }
      });
      setRunningJobs(running);
      
    } catch (error) {
      console.error('Error loading jobs:', error);
      
      if (retry && retryCount < 2) { // Reduced retry attempts
        // Retry with exponential backoff
        const delay = Math.pow(2, retryCount) * 2000; // Increased delay
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          loadJobs(true);
        }, delay);
      } else if (onError && !retry) {
        onError(`Failed to load jobs: ${error.message}`);
      }
    } finally {
      if (!retry) {
        setIsLoading(false);
      }
    }
  }, [onError, retryCount]);

  const deleteJob = useCallback(async (jobId, jobType = 'extraction') => {
    try {
      if (jobType === 'apify') {
        await apiService.deleteApifyJob(jobId);
      } else if (jobType === 'cleaner') {
        await apiService.deleteDataCleanerJob(jobId);
      } else if (jobType === 'traits') {
        await apiService.deleteTraitExtractorJob(jobId);
      } else if (jobType === 'airtable') {
        await apiService.deleteAirtableUpdaterJob(jobId);
      } else {
        await apiService.deleteJob(jobId);
      }
      await loadJobs(); // Reload jobs list
    } catch (error) {
      if (onError) {
        onError(error.message);
      }
    }
  }, [loadJobs, onError]);

  const cancelJob = useCallback(async (jobId, jobType = 'extraction') => {
    try {
      if (jobType === 'apify') {
        await apiService.cancelApifyJob(jobId);
      } else if (jobType === 'cleaner') {
        await apiService.cancelDataCleanerJob(jobId);
      } else if (jobType === 'traits') {
        await apiService.cancelTraitExtractorJob(jobId);
      } else if (jobType === 'airtable') {
        await apiService.cancelAirtableUpdaterJob(jobId);
      } else {
        await apiService.cancelJob(jobId);
      }
      await loadJobs(); // Reload jobs list
      if (onError) {
        onError(`Job ${jobId} cancelled successfully`);
      }
    } catch (error) {
      if (onError) {
        onError(error.message);
      }
    }
  }, [loadJobs, onError]);

  const getJobResults = useCallback(async (jobId, jobType = 'extraction') => {
    try {
      let results;
      if (jobType === 'apify') {
        results = await apiService.getApifyJobResults(jobId);
      } else if (jobType === 'cleaner') {
        results = await apiService.getDataCleanerJobResults(jobId);
      } else if (jobType === 'traits') {
        results = await apiService.getTraitExtractorJobResults(jobId);
      } else if (jobType === 'airtable') {
        results = await apiService.getAirtableUpdaterJobResults(jobId);
      } else {
        results = await apiService.getJobResults(jobId);
      }
      
      setJobResults(results);
      setSelectedJob(jobId);
      if (onJobSelected) {
        onJobSelected(results);
      }
    } catch (error) {
      if (onError) {
        onError(error.message);
      }
    }
  }, [onJobSelected, onError]);

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'queued':
        return 'status-queued';
      case 'running':
        return 'status-running';
      case 'completed':
        return 'status-completed';
      case 'failed':
        return 'status-failed';
      case 'cancelled':
        return 'status-cancelled';
      default:
        return 'status-queued';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const renderProgressBar = (progress) => {
    if (!progress || !progress.percentage) return null;
    
    return (
      <div style={{ marginTop: '8px' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginBottom: '4px',
          fontSize: '12px',
          color: '#666'
        }}>
          <span>{progress.message || 'Processing...'}</span>
          <span>{progress.percentage}%</span>
        </div>
        <div style={{
          width: '100%',
          height: '8px',
          backgroundColor: '#e9ecef',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          <div style={{
            width: `${progress.percentage}%`,
            height: '100%',
            backgroundColor: '#007bff',
            transition: 'width 0.3s ease'
          }} />
        </div>
        {progress.current && progress.total && (
          <div style={{ 
            fontSize: '11px', 
            color: '#999', 
            marginTop: '2px' 
          }}>
            {progress.current} / {progress.total}
          </div>
        )}
      </div>
    );
  };

  // Initial load and polling setup
  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  // Set up polling intervals
  useEffect(() => {
    // General polling every 30 seconds (reduced from 10)
    const generalInterval = setInterval(() => {
      loadJobs(true); // Reload without showing loading state
    }, 30000);
    
    // More frequent updates for running jobs - every 5 seconds (reduced from 2)
    const runningJobsInterval = setInterval(() => {
      if (runningJobs.size > 0) {
        loadJobs(true); // Reload without showing loading state
      }
    }, 5000); // Every 5 seconds for running jobs
    
    return () => {
      clearInterval(generalInterval);
      clearInterval(runningJobsInterval);
    };
  }, [loadJobs, runningJobs]);

  // Function to poll individual job status and show progress in console
  const pollJobProgress = useCallback(async (jobId, jobType = 'extraction') => {
    try {
      let status;
      if (jobType === 'apify') {
        status = await apiService.getApifyJobStatus(jobId);
      } else if (jobType === 'cleaner') {
        status = await apiService.getDataCleanerJobStatus(jobId);
      } else if (jobType === 'traits') {
        status = await apiService.getTraitExtractorJobStatus(jobId);
      } else if (jobType === 'airtable') {
        status = await apiService.getAirtableUpdaterJobStatus(jobId);
      } else {
        status = await apiService.getJobStatus(jobId);
      }

      // Display progress in console if job is running and has progress
      if (status.status === 'running' && status.progress && status.progress.message) {
        const timestamp = status.progress.timestamp ? new Date(status.progress.timestamp).toLocaleTimeString() : '';
        const progressInfo = status.progress.current && status.progress.total 
          ? ` (${status.progress.current}/${status.progress.total})`
          : '';
        const percentage = status.progress.percentage ? ` [${status.progress.percentage}%]` : '';
        
        // Format similar to backend terminal output
        console.log(`[${jobId}] ${status.progress.message}${progressInfo}${percentage} ${timestamp}`);
      }

      return status;
    } catch (error) {
      console.error(`Error polling job ${jobId}:`, error);
      return null;
    }
  }, []);

  // Enhanced progress display function that mimics backend terminal
  const displayJobProgress = useCallback((jobId, jobType, progress) => {
    if (!progress || !progress.message) return;

    const timestamp = progress.timestamp ? new Date(progress.timestamp).toLocaleTimeString() : '';
    const progressInfo = progress.current && progress.total 
      ? ` - ${progress.current}/${progress.total}`
      : '';
    const percentage = progress.percentage ? ` (${progress.percentage}%)` : '';
    
    // Format exactly like backend terminal output
    console.log(`[${jobId}] ${progress.message}${progressInfo}${percentage}`);
    
    // Add job type indicator for clarity
    if (jobType !== 'extraction') {
      console.log(`[${jobId}] Job Type: ${jobType.toUpperCase()}`);
    }
  }, []);

  // Function to start monitoring a job and display start message
  const startJobMonitoring = useCallback((jobId, jobType, config = {}) => {
    // Display job start message similar to backend
    console.log(`\n🚀 Starting ${jobType} job: ${jobId}`);
    
    if (jobType === 'extraction') {
      console.log(`📋 Filters: Event=${config.event_filter || 'S25'}, Top100=${config.top_100_filter || true}`);
      console.log(`📁 Output prefix: ${config.output_prefix || 'S25Top100'}`);
      console.log(`🔍 LinkedIn fields: ${JSON.stringify(config.linkedin_fields || ['4. CEO LinkedIn'])}`);
    } else if (jobType === 'apify') {
      console.log(`📁 URLs File: ${config.urls_file || 'airtable-extractions/S25Top100linkedin_urls_for_apify.json'}`);
      console.log(`📁 Output File: ${config.output_file || 'apify-profile-data/S25Top100linkedin_profile_data.json'}`);
      console.log(`🔢 Batch Size: ${config.batch_size || 50}`);
      console.log(`🧪 Test Mode: ${config.test_mode ? 'Yes' : 'No'}`);
    } else if (jobType === 'cleaner') {
      console.log(`📁 Input File: ${config.input_file || 'apify-profile-data/S25Top100linkedin_profile_data.json'}`);
      console.log(`📁 Output File: ${config.output_file || 'cleaned-profile-data/S25Top100cleaned_linkedin_data.json'}`);
    } else if (jobType === 'traits') {
      console.log(`📁 Input File: ${config.input_file || 'cleaned-profile-data/S25Top100cleaned_linkedin_data.json'}`);
      console.log(`📁 Output File: ${config.output_file || 'final-trait-extractions/S25Top100_comprehensive_traits.json'}`);
      console.log(`🔢 Max Profiles: ${config.max_profiles || -1}`);
      console.log(`🔄 Force Re-extraction: ${config.force_reextraction ? 'Yes' : 'No'}`);
    } else if (jobType === 'airtable') {
      console.log(`📁 Traits File: ${config.traits_file || 'final-trait-extractions/S25Top100_comprehensive_traits.json'}`);
      console.log(`📁 URL Mapping File: ${config.url_mapping_file || 'airtable-extractions/S25Top100airtable_url_mapping.json'}`);
      console.log(`⏱️ Delay: ${config.delay_between_updates || 0.5}s`);
    }
    
    console.log(`-`.repeat(60));
    
    // Start monitoring this job
    const monitorInterval = setInterval(async () => {
      const status = await pollJobProgress(jobId, jobType);
      
      // Stop monitoring if job is no longer running
      if (status && (status.status === 'completed' || status.status === 'failed')) {
        clearInterval(monitorInterval);
        
        if (status.status === 'completed') {
          console.log(`\n✅ Job ${jobId} completed successfully!`);
        } else {
          console.log(`\n❌ Job ${jobId} failed: ${status.error || 'Unknown error'}`);
        }
        console.log(`-`.repeat(60));
      }
    }, 1000); // Poll every second
    
    return monitorInterval;
  }, [pollJobProgress]);

  // Set up individual job progress polling for running jobs
  useEffect(() => {
    if (runningJobs.size === 0) return;

    const progressIntervals = new Map();

    // Set up progress polling for each running job
    runningJobs.forEach(jobId => {
      // Determine job type from job ID or check all job arrays
      let jobType = 'extraction';
      if (apifyJobs.some(job => job.job_id === jobId)) jobType = 'apify';
      else if (cleanerJobs.some(job => job.job_id === jobId)) jobType = 'cleaner';
      else if (traitJobs.some(job => job.job_id === jobId)) jobType = 'traits';
      else if (airtableJobs.some(job => job.job_id === jobId)) jobType = 'airtable';

      const interval = setInterval(() => {
        pollJobProgress(jobId, jobType);
      }, 1000); // Poll every second for detailed progress

      progressIntervals.set(jobId, interval);
    });

    // Cleanup function
    return () => {
      progressIntervals.forEach(interval => clearInterval(interval));
    };
  }, [runningJobs, apifyJobs, cleanerJobs, traitJobs, airtableJobs, pollJobProgress]);

  const renderJobItem = (job, jobType) => {
    return (
      <div key={job.job_id} className={`job-item ${job.status === 'running' ? 'running' : ''}`}>
        <div className="job-header">
          <div>
            <span className={`status-badge ${getStatusBadgeClass(job.status)}`}>
              {job.status}
            </span>
            {job.status === 'running' && (
              <span className="live-indicator">
                <span className="live-dot"></span>
                Live
              </span>
            )}
            <span className="job-id">{job.job_id}</span>
            <span style={{ fontSize: '12px', color: '#666', marginLeft: '8px' }}>
              ({jobType})
            </span>
          </div>
          <div>
            {job.status === 'completed' && (
              <button
                className="btn btn-success"
                onClick={() => getJobResults(job.job_id, jobType)}
                style={{ marginRight: '8px' }}
              >
                View Results
              </button>
            )}
            {(job.status === 'running' || job.status === 'queued') && (
              <CancelJobButton
                jobId={job.job_id}
                jobType={jobType}
                onCancel={cancelJob}
                onError={onError}
              />
            )}
            <button
              className="btn btn-danger"
              onClick={() => deleteJob(job.job_id, jobType)}
            >
              Delete
            </button>
          </div>
        </div>

        <div className="job-details">
          <div className="detail-item">
            <span className="detail-label">Started:</span>
            <span className="detail-value">{formatDate(job.started_at)}</span>
          </div>
          {job.completed_at && (
            <div className="detail-item">
              <span className="detail-label">Completed:</span>
              <span className="detail-value">{formatDate(job.completed_at)}</span>
            </div>
          )}
        </div>

        {/* Enhanced progress bar for running jobs */}
        {job.status === 'running' && job.progress && (
          <div className="progress-container">
            <div className="progress-header">
              <span className="progress-message">{job.progress.message || 'Processing...'}</span>
              <span className="progress-percentage">{job.progress.percentage}%</span>
            </div>
            <div className="progress-bar-container">
              <div 
                className="progress-bar-fill"
                style={{ width: `${job.progress.percentage}%` }}
              />
            </div>
            {job.progress.current && job.progress.total && (
              <div className="progress-stats">
                <span>{job.progress.current} / {job.progress.total}</span>
                <span>{job.progress.timestamp ? new Date(job.progress.timestamp).toLocaleTimeString() : ''}</span>
              </div>
            )}
          </div>
        )}

        {selectedJob === job.job_id && jobResults && (
          <div style={{ marginTop: '16px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
            <h4>Results for {job.job_id}</h4>
            {jobType === 'apify' ? (
              // Apify job results
              <div className="job-details">
                <div className="detail-item">
                  <span className="detail-label">Total URLs:</span>
                  <span className="detail-value">{jobResults.total_urls}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Processed Profiles:</span>
                  <span className="detail-value">{jobResults.processed_profiles}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Output File:</span>
                  <span className="detail-value">{jobResults.output_file}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Test Mode:</span>
                  <span className="detail-value">{jobResults.test_mode ? 'Yes' : 'No'}</span>
                </div>
              </div>
            ) : jobType === 'cleaner' ? (
              // Data cleaner job results
              <div className="job-details">
                <div className="detail-item">
                  <span className="detail-label">Total Profiles:</span>
                  <span className="detail-value">{jobResults.total_profiles}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Input File:</span>
                  <span className="detail-value">{jobResults.input_file}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Output File:</span>
                  <span className="detail-value">{jobResults.output_file}</span>
                </div>
              </div>
            ) : jobType === 'traits' ? (
              // Trait extractor job results
              <div className="job-details">
                <div className="detail-item">
                  <span className="detail-label">Total Profiles:</span>
                  <span className="detail-value">{jobResults.total_profiles}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Processed Profiles:</span>
                  <span className="detail-value">{jobResults.processed_profiles}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Input File:</span>
                  <span className="detail-value">{jobResults.input_file}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Output File:</span>
                  <span className="detail-value">{jobResults.output_file}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Max Profiles:</span>
                  <span className="detail-value">{jobResults.max_profiles}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Force Re-extraction:</span>
                  <span className="detail-value">{jobResults.force_reextraction ? 'Yes' : 'No'}</span>
                </div>
              </div>
            ) : jobType === 'airtable' ? (
              // Airtable updater job results
              <div className="job-details">
                <div className="detail-item">
                  <span className="detail-label">Total Traits:</span>
                  <span className="detail-value">{jobResults.total_traits}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Successful Updates:</span>
                  <span className="detail-value">{jobResults.successful_updates}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Failed Updates:</span>
                  <span className="detail-value">{jobResults.failed_updates}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Missing Mappings:</span>
                  <span className="detail-value">{jobResults.missing_mappings}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Traits File:</span>
                  <span className="detail-value">{jobResults.traits_file}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">URL Mapping File:</span>
                  <span className="detail-value">{jobResults.url_mapping_file}</span>
                </div>
              </div>
            ) : (
              // Extraction job results
              <div className="job-details">
                <div className="detail-item">
                  <span className="detail-label">Total Records:</span>
                  <span className="detail-value">{jobResults.total_records}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Valid URLs:</span>
                  <span className="detail-value">{jobResults.valid_urls}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Success Rate:</span>
                  <span className="detail-value">{jobResults.success_rate?.toFixed(1)}%</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Files Created:</span>
                  <span className="detail-value">{jobResults.files_created?.length || 0}</span>
                </div>
              </div>
            )}
            
            {jobResults.files_created && jobResults.files_created.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <strong>Files Created:</strong>
                <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
                  {jobResults.files_created.map((file, index) => (
                    <li key={index} style={{ fontFamily: 'monospace', fontSize: '14px' }}>
                      {file}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="card">
        <h2>Jobs</h2>
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <span className="loading"></span>
          <p>Loading jobs...</p>
          {retryCount > 0 && (
            <p style={{ fontSize: '14px', color: '#666' }}>
              Retrying... (Attempt {retryCount}/3)
            </p>
          )}
        </div>
      </div>
    );
  }

  const currentJobs = activeTab === 'extraction' ? extractionJobs : activeTab === 'apify' ? apifyJobs : activeTab === 'cleaner' ? cleanerJobs : activeTab === 'traits' ? traitJobs : airtableJobs;
  const totalJobs = extractionJobs.length + apifyJobs.length + cleanerJobs.length + traitJobs.length + airtableJobs.length;

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Jobs ({totalJobs})</h2>
        <button className="btn btn-secondary" onClick={() => loadJobs()}>
          Refresh
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="tabs" style={{ marginBottom: '20px' }}>
        <button
          className={`tab ${activeTab === 'extraction' ? 'active' : ''}`}
          onClick={() => setActiveTab('extraction')}
        >
          Extraction ({extractionJobs.length})
        </button>
        <button
          className={`tab ${activeTab === 'apify' ? 'active' : ''}`}
          onClick={() => setActiveTab('apify')}
        >
          Apify ({apifyJobs.length})
        </button>
        <button
          className={`tab ${activeTab === 'cleaner' ? 'active' : ''}`}
          onClick={() => setActiveTab('cleaner')}
        >
          Data Cleaner ({cleanerJobs.length})
        </button>
        <button
          className={`tab ${activeTab === 'traits' ? 'active' : ''}`}
          onClick={() => setActiveTab('traits')}
        >
          Trait Extractor ({traitJobs.length})
        </button>
        <button
          className={`tab ${activeTab === 'airtable' ? 'active' : ''}`}
          onClick={() => setActiveTab('airtable')}
        >
          Airtable Updater ({airtableJobs.length})
        </button>
      </div>

      {/* Jobs List */}
      {currentJobs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 20px', color: '#666' }}>
          <p>No {activeTab} jobs found.</p>
          <p style={{ fontSize: '14px', marginTop: '8px' }}>
            Start a job from the {activeTab} tab to see it here.
          </p>
        </div>
      ) : (
        <div>
          {currentJobs.map(job => renderJobItem(job, activeTab))}
        </div>
      )}
    </div>
  );
};

export default JobList; 