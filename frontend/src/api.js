import axios from 'axios';

// Configure axios with base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds timeout (increased from 30)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to log requests
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor to handle common errors
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
      console.error('API Connection Error: Backend server is not running');
      throw new Error('Cannot connect to API server. Please make sure the backend is running on http://localhost:8080');
    }
    
    // Handle CORS errors
    if (error.message.includes('CORS') || error.message.includes('Access-Control-Allow-Origin')) {
      console.error('CORS Error: Backend CORS not configured properly');
      throw new Error('CORS error: Backend needs to be restarted with CORS support. Please restart the backend server.');
    }
    
    // Handle other network errors
    if (error.code === 'ERR_NETWORK' || error.code === 'ERR_FAILED') {
      console.error('Network Error: Cannot reach the API server');
      throw new Error('Network error: Cannot reach the API server. Please check if the backend is running on http://localhost:8080');
    }
    
    console.error('API Response Error:', error);
    return Promise.reject(error);
  }
);

// API service functions
export const apiService = {
  // Health check
  async checkHealth() {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`Health check failed: ${error.message}`);
    }
  },

  // Terminal logs
  async getTerminalLogs() {
    try {
      const response = await api.get('/terminal-logs', { timeout: 10000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get terminal logs: ${error.message}`);
    }
  },

  async clearTerminalLogs() {
    try {
      const response = await api.delete('/terminal-logs');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to clear terminal logs: ${error.message}`);
    }
  },

  // Start extraction job
  async startExtraction(config = {}) {
    try {
      // Generate default prefix based on event filter and top 100 filter
      const generateDefaultPrefix = (eventFilter, top100Filter) => {
        const event = eventFilter || "S25";
        const suffix = top100Filter ? "Top100" : "All";
        return `${event}${suffix}`;
      };
      
      const eventFilter = config.event_filter || "S25";
      const top100Filter = config.top_100_filter !== undefined ? config.top_100_filter : true;
      const defaultPrefix = generateDefaultPrefix(eventFilter, top100Filter);
      
      const response = await api.post('/extract', {
        config: {
          linkedin_fields: config.linkedin_fields || ["4. CEO LinkedIn"],
          event_filter: eventFilter,
          top_100_filter: top100Filter,
          output_prefix: config.output_prefix || defaultPrefix,
          base_id: config.base_id || "appCicrQbZaRq1Tvo",
          table_id: config.table_id || "tblIJ47Fniuu9EJat",
        },
        job_id: config.job_id || null,
      });
      return response.data;
    } catch (error) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error(`Failed to start extraction: ${error.message}`);
    }
  },

  // Get job status
  async getJobStatus(jobId) {
    try {
      const response = await api.get(`/status/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Job '${jobId}' not found`);
      }
      throw new Error(`Failed to get job status: ${error.message}`);
    }
  },

  // Get job results
  async getJobResults(jobId) {
    try {
      const response = await api.get(`/results/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(`Job '${jobId}' is not completed yet`);
      }
      throw new Error(`Failed to get job results: ${error.message}`);
    }
  },

  // List all jobs
  async listJobs() {
    try {
      const response = await api.get('/jobs', { timeout: 10000 }); // 10 second timeout for job listing
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        throw new Error('Request timeout: Job listing took too long to respond');
      }
      throw new Error(`Failed to list jobs: ${error.message}`);
    }
  },

  // Delete job
  async deleteJob(jobId) {
    try {
      const response = await api.delete(`/jobs/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Job '${jobId}' not found`);
      }
      throw new Error(`Failed to delete job: ${error.message}`);
    }
  },

  // Cancel job
  async cancelJob(jobId) {
    try {
      const response = await api.post(`/jobs/${jobId}/cancel`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail || `Job '${jobId}' cannot be cancelled`);
      }
      throw new Error(`Failed to cancel job: ${error.message}`);
    }
  },

  // Poll job status until completion
  async pollJobStatus(job_id, onProgress = null, maxAttempts = 300) {
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        const status = await this.getJobStatus(job_id);
        
        // Call progress callback if provided
        if (onProgress && status.progress) {
          onProgress(status.progress);
        }
        
        // Check if job is complete
        if (status.status === 'completed') {
          return status;
        }
        
        if (status.status === 'failed') {
          throw new Error(status.error || 'Job failed');
        }
        
        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, 2000));
        attempts++;
        
      } catch (error) {
        throw error;
      }
    }
    
    throw new Error(`Job ${job_id} did not complete within the expected time`);
  },

  // Apify Processing Functions
  async startApifyProcessing(config = {}) {
    try {
      const response = await api.post('/apify/process', { config });
      return response.data;
    } catch (error) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error(`Failed to start Apify processing: ${error.message}`);
    }
  },

  async getApifyJobStatus(jobId) {
    try {
      const response = await api.get(`/apify/status/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Apify job '${jobId}' not found`);
      }
      throw new Error(`Failed to get Apify job status: ${error.message}`);
    }
  },

  async getApifyJobResults(jobId) {
    try {
      const response = await api.get(`/apify/results/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Apify job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(`Apify job '${jobId}' is not completed yet`);
      }
      throw new Error(`Failed to get Apify job results: ${error.message}`);
    }
  },

  // List all Apify jobs
  async listApifyJobs() {
    try {
      const response = await api.get('/apify/jobs', { timeout: 10000 }); // 10 second timeout
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        throw new Error('Request timeout: Apify job listing took too long to respond');
      }
      throw new Error(`Failed to list Apify jobs: ${error.message}`);
    }
  },

  // Delete Apify job
  async deleteApifyJob(jobId) {
    try {
      const response = await api.delete(`/apify/jobs/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Apify job '${jobId}' not found`);
      }
      throw new Error(`Failed to delete Apify job: ${error.message}`);
    }
  },

  // Cancel Apify job
  async cancelApifyJob(jobId) {
    try {
      const response = await api.post(`/apify/jobs/${jobId}/cancel`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Apify job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail || `Apify job '${jobId}' cannot be cancelled`);
      }
      throw new Error(`Failed to cancel Apify job: ${error.message}`);
    }
  },

  // Poll Apify job status with progress callback
  async pollApifyJobStatus(jobId, onProgress = null, maxAttempts = 300) {
    let attempts = 0;
    const pollInterval = 2000; // 2 seconds

    while (attempts < maxAttempts) {
      try {
        const status = await this.getApifyJobStatus(jobId);
        
        if (onProgress && status.progress) {
          onProgress(status.progress);
        }

        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }

        await new Promise(resolve => setTimeout(resolve, pollInterval));
        attempts++;
      } catch (error) {
        console.error(`Error polling Apify job ${jobId}:`, error);
        attempts++;
        if (attempts >= maxAttempts) {
          throw new Error(`Failed to poll Apify job status after ${maxAttempts} attempts`);
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }
    
    throw new Error(`Apify job ${jobId} did not complete within the expected time`);
  },

  // Data Cleaner Functions
  async startDataCleaning(config = {}) {
    try {
      const response = await api.post('/cleaner/process', {
        config: {
          input_file: config.input_file || "apify-profile-data/S25Top100linkedin_profile_data.json",
          output_file: config.output_file || "cleaned-profile-data/S25Top100cleaned_linkedin_data.json",
        },
        job_id: config.job_id || null,
      });
      return response.data;
    } catch (error) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error(`Failed to start data cleaning: ${error.message}`);
    }
  },

  async getDataCleanerJobStatus(jobId) {
    try {
      const response = await api.get(`/cleaner/status/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Data cleaner job '${jobId}' not found`);
      }
      throw new Error(`Failed to get data cleaner job status: ${error.message}`);
    }
  },

  async getDataCleanerJobResults(jobId) {
    try {
      const response = await api.get(`/cleaner/results/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Data cleaner job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(`Data cleaner job '${jobId}' is not completed yet`);
      }
      throw new Error(`Failed to get data cleaner job results: ${error.message}`);
    }
  },

  // List all data cleaner jobs
  async listDataCleanerJobs() {
    try {
      const response = await api.get('/cleaner/jobs', { timeout: 10000 }); // 10 second timeout
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        throw new Error('Request timeout: Data cleaner job listing took too long to respond');
      }
      throw new Error(`Failed to list data cleaner jobs: ${error.message}`);
    }
  },

  // Delete data cleaner job
  async deleteDataCleanerJob(jobId) {
    try {
      const response = await api.delete(`/cleaner/jobs/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Data cleaner job '${jobId}' not found`);
      }
      throw new Error(`Failed to delete data cleaner job: ${error.message}`);
    }
  },

  // Cancel data cleaner job
  async cancelDataCleanerJob(jobId) {
    try {
      const response = await api.post(`/cleaner/jobs/${jobId}/cancel`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Data cleaner job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail || `Data cleaner job '${jobId}' cannot be cancelled`);
      }
      throw new Error(`Failed to cancel data cleaner job: ${error.message}`);
    }
  },

  // Poll data cleaner job status with progress callback
  async pollDataCleanerJobStatus(jobId, onProgress = null, maxAttempts = 300) {
    let attempts = 0;
    const pollInterval = 2000; // 2 seconds

    while (attempts < maxAttempts) {
      try {
        const status = await this.getDataCleanerJobStatus(jobId);
        
        if (onProgress && status.progress) {
          onProgress(status.progress);
        }

        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }

        await new Promise(resolve => setTimeout(resolve, pollInterval));
        attempts++;
      } catch (error) {
        console.error(`Error polling data cleaner job ${jobId}:`, error);
        attempts++;
        if (attempts >= maxAttempts) {
          throw new Error(`Failed to poll data cleaner job status after ${maxAttempts} attempts`);
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }
    
    throw new Error(`Data cleaner job ${jobId} did not complete within the expected time`);
  },

  // Trait Extractor Functions
  async startTraitExtraction(config = {}) {
    try {
      const response = await api.post('/traits/process', {
        config: {
          input_file: config.input_file || "cleaned-profile-data/S25Top100cleaned_linkedin_data.json",
          output_file: config.output_file || "final-trait-extractions/S25Top100_comprehensive_traits.json",
          max_profiles: config.max_profiles || -1,
          force_reextraction: config.force_reextraction || false,
          delay_between_calls: config.delay_between_calls || 1.0,
        },
        job_id: config.job_id || null,
      });
      return response.data;
    } catch (error) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error(`Failed to start trait extraction: ${error.message}`);
    }
  },

  async getTraitExtractorJobStatus(jobId) {
    try {
      const response = await api.get(`/traits/status/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Trait extractor job '${jobId}' not found`);
      }
      throw new Error(`Failed to get trait extractor job status: ${error.message}`);
    }
  },

  async getTraitExtractorJobResults(jobId) {
    try {
      const response = await api.get(`/traits/results/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Trait extractor job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(`Trait extractor job '${jobId}' is not completed yet`);
      }
      throw new Error(`Failed to get trait extractor job results: ${error.message}`);
    }
  },

  // List all trait extractor jobs
  async listTraitExtractorJobs() {
    try {
      const response = await api.get('/traits/jobs', { timeout: 10000 }); // 10 second timeout
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        throw new Error('Request timeout: Trait extractor job listing took too long to respond');
      }
      throw new Error(`Failed to list trait extractor jobs: ${error.message}`);
    }
  },

  // Delete trait extractor job
  async deleteTraitExtractorJob(jobId) {
    try {
      const response = await api.delete(`/traits/jobs/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Trait extractor job '${jobId}' not found`);
      }
      throw new Error(`Failed to delete trait extractor job: ${error.message}`);
    }
  },

  // Cancel trait extractor job
  async cancelTraitExtractorJob(jobId) {
    try {
      const response = await api.post(`/traits/jobs/${jobId}/cancel`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Trait extractor job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail || `Trait extractor job '${jobId}' cannot be cancelled`);
      }
      throw new Error(`Failed to cancel trait extractor job: ${error.message}`);
    }
  },

  // Poll trait extractor job status with progress callback
  async pollTraitExtractorJobStatus(jobId, onProgress = null, maxAttempts = 300) {
    let attempts = 0;
    const pollInterval = 2000; // 2 seconds

    while (attempts < maxAttempts) {
      try {
        const status = await this.getTraitExtractorJobStatus(jobId);
        
        if (onProgress && status.progress) {
          onProgress(status.progress);
        }

        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }

        await new Promise(resolve => setTimeout(resolve, pollInterval));
        attempts++;
      } catch (error) {
        console.error(`Error polling trait extractor job ${jobId}:`, error);
        attempts++;
        if (attempts >= maxAttempts) {
          throw new Error(`Failed to poll trait extractor job status after ${maxAttempts} attempts`);
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }
    
    throw new Error(`Trait extractor job ${jobId} did not complete within the expected time`);
  },

  // Airtable Updater Functions
  async startAirtableUpdate(config = {}) {
    try {
      const response = await api.post('/airtable/update', {
        config: {
          traits_file: config.traits_file || "final-trait-extractions/S25Top100_comprehensive_traits.json",
          url_mapping_file: config.url_mapping_file || "airtable-extractions/S25Top100airtable_url_mapping.json",
          delay_between_updates: config.delay_between_updates || 0.5,
          base_id: config.base_id || "appCicrQbZaRq1Tvo",
          table_id: config.table_id || "tblIJ47Fniuu9EJat",
        },
        job_id: config.job_id || null,
      });
      return response.data;
    } catch (error) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error(`Failed to start Airtable update: ${error.message}`);
    }
  },

  async getAirtableUpdaterJobStatus(jobId) {
    try {
      const response = await api.get(`/airtable/status/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Airtable updater job '${jobId}' not found`);
      }
      throw new Error(`Failed to get Airtable updater job status: ${error.message}`);
    }
  },

  async getAirtableUpdaterJobResults(jobId) {
    try {
      const response = await api.get(`/airtable/results/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Airtable updater job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(`Airtable updater job '${jobId}' is not completed yet`);
      }
      throw new Error(`Failed to get Airtable updater job results: ${error.message}`);
    }
  },

  // List all Airtable updater jobs
  async listAirtableUpdaterJobs() {
    try {
      const response = await api.get('/airtable/jobs', { timeout: 10000 }); // 10 second timeout
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        throw new Error('Request timeout: Airtable updater job listing took too long to respond');
      }
      throw new Error(`Failed to list Airtable updater jobs: ${error.message}`);
    }
  },

  // Delete Airtable updater job
  async deleteAirtableUpdaterJob(jobId) {
    try {
      const response = await api.delete(`/airtable/jobs/${jobId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Airtable updater job '${jobId}' not found`);
      }
      throw new Error(`Failed to delete Airtable updater job: ${error.message}`);
    }
  },

  // Cancel Airtable updater job
  async cancelAirtableUpdaterJob(jobId) {
    try {
      const response = await api.post(`/airtable/jobs/${jobId}/cancel`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Airtable updater job '${jobId}' not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail || `Airtable updater job '${jobId}' cannot be cancelled`);
      }
      throw new Error(`Failed to cancel Airtable updater job: ${error.message}`);
    }
  },

  // Poll Airtable updater job status with progress callback
  async pollAirtableUpdaterJobStatus(jobId, onProgress = null, maxAttempts = 300) {
    let attempts = 0;
    const pollInterval = 2000; // 2 seconds

    while (attempts < maxAttempts) {
      try {
        const status = await this.getAirtableUpdaterJobStatus(jobId);
        
        if (onProgress && status.progress) {
          onProgress(status.progress);
        }

        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }

        await new Promise(resolve => setTimeout(resolve, pollInterval));
        attempts++;
      } catch (error) {
        console.error(`Error polling Airtable updater job ${jobId}:`, error);
        attempts++;
        if (attempts >= maxAttempts) {
          throw new Error(`Failed to poll Airtable updater job status after ${maxAttempts} attempts`);
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }
    
    throw new Error(`Airtable updater job ${jobId} did not complete within the expected time`);
  },

  // Emergency restart - kills all processes and restarts services
  async emergencyRestart() {
    try {
      const response = await api.post('/emergency-restart', {}, { timeout: 15000 }); // 15 second timeout

      return response.data;
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        throw new Error('Emergency restart request timed out. The restart may have been initiated.');
      }
      throw new Error(`Failed to initiate emergency restart: ${error.message}`);
    }
  },

  // Cancel all running jobs across all job types
  async cancelAllRunningJobs() {
    try {
      // Use the new backend endpoint that kills job processes only
      const response = await api.post('/cancel-all-jobs', {}, { timeout: 10000 }); // 10 second timeout

      return response.data;
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        throw new Error('Cancel all jobs request timed out. The operation may have partially completed.');
      }
      throw new Error(`Failed to cancel all running jobs: ${error.message}`);
    }
  },
};

export default apiService; 