# React Frontend for Airtable LinkedIn URL Extractor

A modern React web application that provides a user-friendly interface for the Airtable LinkedIn URL Extractor API.

## Features

- 🚀 **Start Extractions**: Configure and start LinkedIn URL extraction jobs
- 📊 **Monitor Progress**: Real-time job status and progress tracking
- 📋 **Job Management**: View, manage, and delete extraction jobs
- 🏥 **Health Monitoring**: API health status and system monitoring
- 💬 **Notifications**: Success and error messages with auto-dismiss
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Quick Start

### Prerequisites

- Node.js (version 14 or higher)
- npm or yarn
- The FastAPI backend running on `http://localhost:8080`
TO DO THIS, ACTIVATE THE VENV, AND THEN RUN "python start_api.py" IN CMD

### Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm start
   ```

4. **Open your browser:**
   Navigate to `http://localhost:3000`

## Usage

### Starting an Extraction

1. Click on the **"Start Extraction"** tab
2. Configure your extraction parameters:
   - **LinkedIn Fields**: Comma-separated list of Airtable field names
   - **Event Filter**: Filter by event (e.g., "S25", "W24")
   - **Top 100 Filter**: Check to only process "Top 100" records
   - **Output Prefix**: Prefix for output files
   - **Custom Job ID**: Optional custom identifier
3. Click **"Start Extraction"**
4. The app will automatically switch to the Jobs tab to show progress

### Monitoring Jobs

1. Click on the **"View Jobs"** tab
2. See all extraction jobs with their current status
3. Click **"View Results"** for completed jobs to see detailed results
4. Use **"Delete"** to remove jobs from memory

### API Health

1. Click on the **"API Health"** tab
2. Monitor the API server status
3. View active jobs and system statistics

## Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
# API Base URL (default: http://localhost:8080)
REACT_APP_API_URL=http://localhost:8080

# Development settings
REACT_APP_DEBUG=true
```

### API Connection

The frontend connects to the FastAPI backend. Make sure:

1. The backend is running on the correct port (default: 8080)
2. CORS is properly configured (the backend should allow requests from `http://localhost:3000`)
3. The API endpoints are accessible

## Project Structure

```
frontend/
├── public/
│   └── index.html          # Main HTML file
├── src/
│   ├── components/
│   │   ├── ExtractionForm.js    # Form to start extractions
│   │   ├── JobList.js           # Job management component
│   │   └── HealthStatus.js      # API health monitoring
│   ├── api.js                   # API service functions
│   ├── App.js                   # Main application component
│   ├── App.css                  # Application styles
│   ├── index.js                 # React entry point
│   └── index.css                # Global styles
├── package.json                 # Dependencies and scripts
└── README.md                   # This file
```

## Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App (not recommended)

## API Integration

The frontend communicates with the FastAPI backend through the following endpoints:

- `GET /health` - Check API health
- `POST /extract` - Start extraction job
- `GET /status/{job_id}` - Get job status
- `GET /results/{job_id}` - Get job results
- `GET /jobs` - List all jobs
- `DELETE /jobs/{job_id}` - Delete job

## Troubleshooting

### Common Issues

1. **"Cannot connect to API"**
   - Ensure the FastAPI backend is running on port 8080
   - Check if the backend URL is correct in `.env`
   - Verify CORS settings in the backend

2. **"Module not found" errors**
   - Run `npm install` to install dependencies
   - Clear node_modules and reinstall: `rm -rf node_modules && npm install`

3. **Build errors**
   - Check for syntax errors in React components
   - Ensure all imports are correct
   - Verify environment variables are set correctly

### Development Tips

- Use the browser's developer tools to debug API calls
- Check the Network tab to see request/response details
- Use the Console tab to view error messages
- The React Developer Tools extension is helpful for debugging

## Deployment

### Production Build

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Serve the build folder:**
   ```bash
   npx serve -s build
   ```

### Environment Configuration

For production deployment, set the correct API URL:

```env
REACT_APP_API_URL=https://your-api-domain.com
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the Onstage Profile Enricher system. 