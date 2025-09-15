"""

DONT GET THIS AT ALL: https://chatgpt.com/c/6880147d-11c4-8012-ad88-f3d9c4474745


FastAPI Backend for Airtable LinkedIn URL Extraction

This API provides endpoints to:
- Trigger LinkedIn URL extraction from Airtable
- Check extraction status and progress
- Retrieve extraction results
- Configure extraction parameters

Usage:
    uvicorn airtable_api:app --reload --host 0.0.0.0 --port 8000
"""

import os
import json
import asyncio
import signal
import subprocess
import psutil
import threading
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from airtable_extractor import AirtableLinkedInExtractor
from apify_requester import process_linkedin_profiles_with_resume, load_linkedin_urls, load_progress, save_progress, get_remaining_urls
import os
from data_cleaner import LinkedInDataProcessor
from trait_extractor import LinkedInTraitExtractor
from airtable_updater import AirtableTraitUpdater
from pyairtable import Api

# Initialize FastAPI app
app = FastAPI(
    title="Airtable LinkedIn URL Extractor API",
    description="API for extracting LinkedIn URLs from Airtable records and processing them through Apify",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for tracking extraction jobs
extraction_jobs: Dict[str, Dict[str, Any]] = {}
apify_jobs: Dict[str, Dict[str, Any]] = {}
data_cleaner_jobs: Dict[str, Dict[str, Any]] = {}
trait_extractor_jobs: Dict[str, Dict[str, Any]] = {}
airtable_updater_jobs: Dict[str, Dict[str, Any]] = {}

# Global state for tracking cancellation requests
cancellation_requests: Dict[str, bool] = {}

# Global state for tracking running processes
running_processes: Dict[str, List[int]] = {}  # job_id -> list of process IDs
process_lock = threading.Lock()

# Terminal logs storage
terminal_logs: List[Dict[str, Any]] = []
MAX_LOGS = 1000  # Keep last 1000 log entries

def add_terminal_log(level: str, message: str):
    """Add a log entry to the terminal logs."""
    log_entry = {
        "id": len(terminal_logs) + 1,
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message
    }
    terminal_logs.append(log_entry)
    
    # Keep only the last MAX_LOGS entries
    if len(terminal_logs) > MAX_LOGS:
        terminal_logs.pop(0)

# Pydantic models for request/response validation
# We use these in the post/get requests to tell the api what format the data is being sent in
class ExtractionConfig(BaseModel):
    """Configuration for LinkedIn URL extraction."""
    linkedin_fields: List[str] = Field(
        default=["4. CEO LinkedIn"],
        description="List of Airtable field names to check for LinkedIn URLs"
    )
    event_filter: Optional[str] = Field(
        default="S25",
        description="Event filter (e.g., 'S25')"
    )
    # THIS IS YAAAAAP
    top_100_filter: Optional[bool] = Field(
        default=True,
        description="Filter for Top 100 records only"
    )
    output_prefix: str = Field(
        default="test",
        description="Prefix for output filenames"
    )
    base_id: str = Field(
        default="appCicrQbZaRq1Tvo",
        description="Airtable base ID to connect to"
    )
    table_id: str = Field(
        default="tblIJ47Fniuu9EJat",
        description="Airtable table ID to connect to"
    )

# Whenever a client sends an endpoint with data as {"config": ..., "job_id": ..}, fast api:
    # Parses it into a Extraction request instance,
    # The config field in itself is the ExtractionConfif Data model 
        # Config must exist, but if not provided its default to extraction config (Field(default_factory=ExtractionConfig))
        # job_id doesn't have to exist, and if no value is provided, then it's set to None (Field(default = None))
        # job id is optional. 

# the = ... is just the default value if nothing is provided
class ExtractionRequest(BaseModel):
    """model for starting whenever an airtable extraciton is asked for."""
    config: ExtractionConfig = Field(default_factory=ExtractionConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class ExtractionStatus(BaseModel):
    """Status model for extraction jobs."""
    job_id: str
    status: str  # "running", "completed", "failed", "not_found"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ExtractionResults(BaseModel):
    """Results model for completed extractions."""
    job_id: str
    total_records: int
    valid_urls: int
    invalid_urls: int
    missing_urls: int
    success_rate: float
    files_created: List[str]
    url_to_record_mapping: Dict[str, str]
    urls_for_apify: List[str]

class ApifyConfig(BaseModel):
    """Configuration for Apify LinkedIn profile processing."""
    urls_file: str = Field(
        default="airtable-extractions/S25Top100linkedin_urls_for_apify.json",
        description="Path to the JSON file containing LinkedIn URLs"
    )
    output_file: str = Field(
        default="apify-profile-data/S25Top100linkedin_profile_data.json",
        description="Path to save the processed profile data"
    )
    batch_size: int = Field(
        default=20,
        description="Number of URLs to process in each batch"
    )
    test_mode: bool = Field(
        default=False,
        description="Run in test mode with limited URLs"
    )
    test_num_urls: int = Field(
        default=10,
        description="Number of URLs to process in test mode"
    )
    force_restart: bool = Field(
        default=False,
        description="Force restart processing from beginning, ignoring existing progress"
    )

class ApifyRequest(BaseModel):
    """Request model for starting an Apify processing job."""
    config: ApifyConfig = Field(default_factory=ApifyConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class ApifyStatus(BaseModel):
    """Status model for Apify processing jobs."""
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class DataCleanerConfig(BaseModel):
    """Configuration for data cleaning jobs."""
    input_file: str = Field(
        default="apify-profile-data/S25Top100linkedin_profile_data.json",
        description="Path to the input JSON file with raw profile data"
    )
    output_file: str = Field(
        default="cleaned-profile-data/S25Top100cleaned_linkedin_data.json",
        description="Path to save the cleaned profile data"
    )

class DataCleanerRequest(BaseModel):
    """Request model for starting a data cleaning job."""
    config: DataCleanerConfig = Field(default_factory=DataCleanerConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class DataCleanerStatus(BaseModel):
    """Status model for data cleaning jobs."""
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TraitExtractorConfig(BaseModel):
    """Configuration for trait extraction jobs."""
    input_file: str = Field(
        default="cleaned-profile-data/S25Top100cleaned_linkedin_data.json",
        description="Path to the cleaned LinkedIn profiles JSON file"
    )
    output_file: str = Field(
        default="final-trait-extractions/S25Top100_comprehensive_traits.json",
        description="Path to save the extracted traits data"
    )
    max_profiles: int = Field(
        default=-1,
        description="Maximum number of profiles to process (-1 for all)"
    )
    force_reextraction: bool = Field(
        default=False,
        description="Force re-extraction of all profiles even if already processed"
    )
    delay_between_calls: float = Field(
        default=1.0,
        description="Delay between OpenAI API calls in seconds"
    )

class TraitExtractorRequest(BaseModel):
    """Request model for starting a trait extraction job."""
    config: TraitExtractorConfig = Field(default_factory=TraitExtractorConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class TraitExtractorStatus(BaseModel):
    """Status model for trait extraction jobs."""
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AirtableUpdaterConfig(BaseModel):
    """Configuration for Airtable update jobs."""
    traits_file: str = Field(
        default="final-trait-extractions/S25Top100_comprehensive_traits.json",
        description="Path to the trait extraction results JSON file"
    )
    url_mapping_file: str = Field(
        default="airtable-extractions/S25Top100airtable_url_mapping.json",
        description="Path to the URL mapping JSON file"
    )
    delay_between_updates: float = Field(
        default=0.5,
        description="Delay between Airtable API calls in seconds"
    )
    base_id: str = Field(
        default="appCicrQbZaRq1Tvo",
        description="Airtable base ID to connect to"
    )
    table_id: str = Field(
        default="tblIJ47Fniuu9EJat",
        description="Airtable table ID to connect to"
    )

class AirtableUpdaterRequest(BaseModel):
    """Request model for starting an Airtable update job."""
    config: AirtableUpdaterConfig = Field(default_factory=AirtableUpdaterConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class AirtableUpdaterStatus(BaseModel):
    """Status model for Airtable update jobs."""
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Enhanced API extractor with better progress tracking
class APIAirtableLinkedInExtractor(AirtableLinkedInExtractor):
    """Enhanced extractor with progress tracking for API use."""
    
    def __init__(self, job_id: str, progress_callback=None, base_id: str = "appCicrQbZaRq1Tvo", table_id: str = "tblIJ47Fniuu9EJat"):
        # Initialize the parent class with custom base_id and table_id
        self.api_key = os.getenv('AIRTABLE_API_KEY')
        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY environment variable not set")
        
        self.api = Api(self.api_key)
        self.base_id = base_id
        self.table_id = table_id
        self.table = self.api.table(self.base_id, self.table_id)
        
        # Initialize other attributes from parent class
        self.url_to_record_mapping: Dict[str, str] = {}
        self.valid_urls: List[str] = []
        self.invalid_urls: List[str] = []
        self.missing_urls: List[str] = {}  # record_id -> reason
        
        # API-specific attributes
        self.job_id = job_id
        self.progress_callback = progress_callback
        self.total_processed = 0
        
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update extraction progress with terminal output."""
        # Handle None total value
        if total is None:
            total = current  # Use current as total when no estimate is available
        
        progress_data = {
            "current": current,
            "total": total,
            "percentage": round((current / total) * 100, 1) if total > 0 else 0,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Terminal output for real-time tracking
        print(f"[{self.job_id}] {message} - {current}/{total} ({progress_data['percentage']}%)")
        
        if self.progress_callback:
            self.progress_callback(self.job_id, progress_data)
    
    def extract_linkedin_urls_with_filters(
        self, 
        linkedin_fields: List[str] = None,
        event_filter: str = "S25",
        top_100_filter: bool = True,
        output_prefix: str = "S25Top100"
    ) -> Dict[str, Any]:
        """Enhanced extraction with custom filters and progress tracking."""
        
        if linkedin_fields is None:
            linkedin_fields = ["4. CEO LinkedIn"]
        
        print(f"\n🚀 Starting extraction for job {self.job_id}")
        print(f"📋 Filters: Event={event_filter}, Top100={top_100_filter}")
        print(f"📁 Output prefix: {output_prefix}")
        print(f"🔍 LinkedIn fields: {linkedin_fields}")
        print("-" * 60)
        
        total_records = 0
        processed_pages = 0
        
        try:
            # Single pass: process records and track progress
            print(f"📊 Processing records with filters...")
            
            for records in self.table.iterate(page_size=100):
                processed_pages += 1
                
                for record in records:
                    record_id = record['id']
                    fields = record.get('fields', {})
                    
                    # Apply filters
                    matches_filter = True
                    
                    # Check Event filter
                    if event_filter and ('Event' not in fields or fields['Event'].strip() != event_filter):
                        matches_filter = False
                    
                    # Check Top 100 filter
                    if top_100_filter and ('Top 100' not in fields or not fields['Top 100']):
                        matches_filter = False
                    
                    if not matches_filter:
                        continue
                    
                    total_records += 1
                    self.total_processed += 1
                    
                    # Update progress every 10 records
                    if total_records % 10 == 0:
                        self.update_progress(
                            total_records, 
                            None,  # No estimate needed
                            f"Processing record {total_records}"
                        )
                    
                    linkedin_url = None
                    found_field = None
                    
                    # Check each potential LinkedIn field
                    for field_name in linkedin_fields:
                        if field_name in fields and fields[field_name]:
                            url_candidate = fields[field_name]
                            
                            if isinstance(url_candidate, list):
                                url_candidate = url_candidate[0] if url_candidate else None
                            
                            if isinstance(url_candidate, str) and 'linkedin.com/in' in url_candidate.lower():
                                linkedin_url = self.extract_first_valid_linkedin_url(url_candidate)
                                if linkedin_url:
                                    found_field = field_name
                                    break
                    
                    # Process the found URL
                    if linkedin_url:
                        if linkedin_url not in self.url_to_record_mapping:
                            self.url_to_record_mapping[linkedin_url] = record_id
                            self.valid_urls.append(linkedin_url)
                        else:
                            print(f"Duplicate URL: {linkedin_url}")
                    else:
                        self.missing_urls[record_id] = "No valid LinkedIn URL found in any field"
            
            # Final progress update
            self.update_progress(
                total_records, 
                total_records,
                "Extraction completed, saving results..."
            )
            
            # Save results with custom prefix
            self.save_results_with_prefix(output_prefix)
            
            return {
                'total_records': total_records,
                'valid_urls': len(self.valid_urls),
                'invalid_urls': len(self.invalid_urls),
                'missing_urls': len(self.missing_urls),
                'success_rate': (len(self.valid_urls) / total_records * 100) if total_records > 0 else 0,
                'url_to_record_mapping': self.url_to_record_mapping,
                'urls_for_apify': self.valid_urls,
                'files_created': [
                    f'airtable-extractions/{output_prefix}airtable_url_mapping.json',
                    f'airtable-extractions/{output_prefix}linkedin_urls_for_apify.json',
                    f'airtable-extractions/{output_prefix}airtable_extraction_results.json'
                ]
            }
            
        except Exception as e:
            print(f"Error during extraction: {e}")
            raise
    
    # Just saves the 3 files after processing
    def save_results_with_prefix(self, prefix: str):
        """Save results with custom filename prefix."""
        # Ensure directory exists
        Path('airtable-extractions').mkdir(exist_ok=True)
        
        # Save URL to record mapping
        with open(f'airtable-extractions/{prefix}airtable_url_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(self.url_to_record_mapping, f, indent=2, ensure_ascii=False)
        
        # Save URLs for Apify
        with open(f'airtable-extractions/{prefix}linkedin_urls_for_apify.json', 'w', encoding='utf-8') as f:
            json.dump(self.valid_urls, f, indent=2, ensure_ascii=False)
        
        # Save comprehensive results
        results = {
            'extraction_summary': {
                'total_valid_urls': len(self.valid_urls),
                'total_invalid_urls': len(self.invalid_urls),
                'total_missing_urls': len(self.missing_urls)
            },
            'url_to_record_mapping': self.url_to_record_mapping,
            'valid_urls': self.valid_urls,
            'invalid_urls': self.invalid_urls,
            'missing_url_records': self.missing_urls
        }
        
        with open(f'airtable-extractions/{prefix}airtable_extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

# Helper functions
def generate_job_id() -> str:
    """Generate a unique job ID."""
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

def update_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update job progress and add to terminal logs."""
    if job_id in extraction_jobs:
        extraction_jobs[job_id]["progress"] = progress_data
        
        # Add progress message to terminal logs
        if "message" in progress_data:
            add_terminal_log("INFO", f"[{job_id}] {progress_data['message']}")
            
            # Add progress details if available
            if "current" in progress_data and "total" in progress_data:
                percentage = int((progress_data["current"] / progress_data["total"]) * 100)
                add_terminal_log("INFO", f"[{job_id}] Progress: {progress_data['current']}/{progress_data['total']} ({percentage}%)")
    elif job_id in apify_jobs:
        apify_jobs[job_id]["progress"] = progress_data
    elif job_id in data_cleaner_jobs:
        data_cleaner_jobs[job_id]["progress"] = progress_data
    elif job_id in trait_extractor_jobs:
        trait_extractor_jobs[job_id]["progress"] = progress_data
    elif job_id in airtable_updater_jobs:
        airtable_updater_jobs[job_id]["progress"] = progress_data

def update_apify_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update Apify job progress in global state with terminal output."""
    if 'message' in progress_data:
        print(f"[{job_id}] {progress_data['message']}")
        if 'processed' in progress_data and 'total' in progress_data:
            percentage = progress_data.get('percentage', 0)
            print(f"[{job_id}] Apify Progress: {progress_data['processed']}/{progress_data['total']} ({percentage}%)")
    
    if job_id in apify_jobs:
        apify_jobs[job_id]["progress"] = progress_data

def update_data_cleaner_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update data cleaner job progress in global state with terminal output."""
    if 'message' in progress_data:
        print(f"[{job_id}] {progress_data['message']}")
        if 'processed' in progress_data and 'total' in progress_data:
            percentage = progress_data.get('percentage', 0)
            print(f"[{job_id}] Data Cleaner Progress: {progress_data['processed']}/{progress_data['total']} ({percentage}%)")
    
    if job_id in data_cleaner_jobs:
        data_cleaner_jobs[job_id]["progress"] = progress_data

def update_trait_extractor_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update trait extractor job progress in global state with terminal output."""
    if 'message' in progress_data:
        print(f"[{job_id}] {progress_data['message']}")
        if 'processed' in progress_data and 'total' in progress_data:
            percentage = progress_data.get('percentage', 0)
            print(f"[{job_id}] Trait Extractor Progress: {progress_data['processed']}/{progress_data['total']} ({percentage}%)")
    
    if job_id in trait_extractor_jobs:
        trait_extractor_jobs[job_id]["progress"] = progress_data

def update_airtable_updater_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update Airtable updater job progress in global state with terminal output."""
    if 'message' in progress_data:
        print(f"[{job_id}] {progress_data['message']}")
        if 'processed' in progress_data and 'total' in progress_data:
            percentage = progress_data.get('percentage', 0)
            print(f"[{job_id}] Airtable Updater Progress: {progress_data['processed']}/{progress_data['total']} ({percentage}%)")
    
    if job_id in airtable_updater_jobs:
        airtable_updater_jobs[job_id]["progress"] = progress_data

def check_cancellation(job_id: str) -> bool:
    """Check if a job has been requested to be cancelled."""
    return job_id in cancellation_requests and cancellation_requests[job_id]

def add_process_to_job(job_id: str, process_id: int):
    """Add a process ID to a job's tracking list."""
    with process_lock:
        if job_id not in running_processes:
            running_processes[job_id] = []
        running_processes[job_id].append(process_id)

def remove_process_from_job(job_id: str, process_id: int):
    """Remove a process ID from a job's tracking list."""
    with process_lock:
        if job_id in running_processes and process_id in running_processes[job_id]:
            running_processes[job_id].remove(process_id)

def kill_job_processes(job_id: str) -> Dict[str, Any]:
    """Forcefully terminate all processes associated with a job."""
    results = {
        "job_id": job_id,
        "processes_found": 0,
        "processes_killed": 0,
        "errors": []
    }
    
    with process_lock:
        if job_id not in running_processes:
            return results
        
        process_ids = running_processes[job_id].copy()
        running_processes[job_id] = []  # Clear the list
    
    results["processes_found"] = len(process_ids)
    
    for pid in process_ids:
        try:
            # Try to get the process
            process = psutil.Process(pid)
            
            # Kill the process and all its children
            children = process.children(recursive=True)
            
            # Kill children first
            for child in children:
                try:
                    child.terminate()
                    child.wait(timeout=3)  # Wait up to 3 seconds
                except psutil.TimeoutExpired:
                    try:
                        child.kill()  # Force kill if terminate doesn't work
                    except psutil.NoSuchProcess:
                        pass  # Process already dead
                except psutil.NoSuchProcess:
                    pass  # Process already dead
            
            # Kill the main process
            try:
                process.terminate()
                process.wait(timeout=3)  # Wait up to 3 seconds
            except psutil.TimeoutExpired:
                try:
                    process.kill()  # Force kill if terminate doesn't work
                except psutil.NoSuchProcess:
                    pass  # Process already dead
            except psutil.NoSuchProcess:
                pass  # Process already dead
            
            results["processes_killed"] += 1
            add_terminal_log("INFO", f"🛑 Killed process {pid} for job {job_id}")
            
        except psutil.NoSuchProcess:
            # Process already dead
            pass
        except Exception as e:
            error_msg = f"Error killing process {pid}: {str(e)}"
            results["errors"].append(error_msg)
            add_terminal_log("ERROR", error_msg)
    
    return results

def kill_all_python_processes() -> Dict[str, Any]:
    """Forcefully terminate all Python processes except the current one."""
    results = {
        "processes_found": 0,
        "processes_killed": 0,
        "errors": []
    }
    
    current_pid = os.getpid()
    
    try:
        # Find all Python processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    pid = proc.info['pid']
                    
                    # Skip the current process
                    if pid == current_pid:
                        continue
                    
                    results["processes_found"] += 1
                    
                    # Kill the process and all its children
                    children = proc.children(recursive=True)
                    
                    # Kill children first
                    for child in children:
                        try:
                            child.terminate()
                            child.wait(timeout=2)  # Wait up to 2 seconds
                        except psutil.TimeoutExpired:
                            try:
                                child.kill()  # Force kill if terminate doesn't work
                            except psutil.NoSuchProcess:
                                pass  # Process already dead
                        except psutil.NoSuchProcess:
                            pass  # Process already dead
                    
                    # Kill the main process
                    try:
                        proc.terminate()
                        proc.wait(timeout=2)  # Wait up to 2 seconds
                    except psutil.TimeoutExpired:
                        try:
                            proc.kill()  # Force kill if terminate doesn't work
                        except psutil.NoSuchProcess:
                            pass  # Process already dead
                    except psutil.NoSuchProcess:
                        pass  # Process already dead
                    
                    results["processes_killed"] += 1
                    add_terminal_log("INFO", f"🛑 Killed Python process {pid}")
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass  # Process already dead or access denied
            except Exception as e:
                error_msg = f"Error killing process {proc.info.get('pid', 'unknown')}: {str(e)}"
                results["errors"].append(error_msg)
                add_terminal_log("ERROR", error_msg)
    
    except Exception as e:
        error_msg = f"Error in kill_all_python_processes: {str(e)}"
        results["errors"].append(error_msg)
        add_terminal_log("ERROR", error_msg)
    
    return results

async def run_extraction_job(job_id: str, config: ExtractionConfig):
    """Run extraction job in background."""
    try:
        # Update job status to running
        extraction_jobs[job_id]["status"] = "running"
        add_terminal_log("INFO", f"🚀 Starting extraction for job {job_id}")
        add_terminal_log("INFO", f"📋 Filters: Event={config.event_filter}, Top100={config.top_100_filter}")
        add_terminal_log("INFO", f"📁 Output prefix: {config.output_prefix}")
        add_terminal_log("INFO", f"🔍 LinkedIn fields: {config.linkedin_fields}")
        add_terminal_log("INFO", "-" * 60)
        
        # Check for cancellation before starting
        if check_cancellation(job_id):
            extraction_jobs[job_id]["status"] = "cancelled"
            extraction_jobs[job_id]["completed_at"] = datetime.now()
            add_terminal_log("INFO", f"⏹️ Extraction cancelled for job {job_id}")
            return
        
        # Create extractor with progress callback and custom base/table IDs
        extractor = APIAirtableLinkedInExtractor(
            job_id, 
            update_job_progress, 
            base_id=config.base_id, 
            table_id=config.table_id
        )
        
        # Track the current process
        current_pid = os.getpid()
        add_process_to_job(job_id, current_pid)
        
        try:
            # Run extraction in thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,  # Use default executor (thread pool)
                extractor.extract_linkedin_urls_with_filters,
                config.linkedin_fields,
                config.event_filter,
                config.top_100_filter,
                config.output_prefix
            )
            
            # Check for cancellation after extraction
            if check_cancellation(job_id):
                extraction_jobs[job_id]["status"] = "cancelled"
                extraction_jobs[job_id]["completed_at"] = datetime.now()
                add_terminal_log("INFO", f"⏹️ Extraction cancelled for job {job_id}")
                return
                
        finally:
            # Remove process from tracking
            remove_process_from_job(job_id, current_pid)
        
        # Save results with prefix in thread pool
        await loop.run_in_executor(
            None,
            extractor.save_results_with_prefix,
            config.output_prefix
        )
        
        # Update job status to completed
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["completed_at"] = datetime.now()
        extraction_jobs[job_id]["results"] = results
        
        add_terminal_log("INFO", f"✅ Extraction completed successfully for job {job_id}")
        add_terminal_log("INFO", f"📊 Results: {results['valid_urls']} valid URLs, {results['invalid_urls']} invalid URLs")
        
    except Exception as e:
        # Update job status to failed
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["completed_at"] = datetime.now()
        extraction_jobs[job_id]["error"] = str(e)
        
        add_terminal_log("ERROR", f"❌ Extraction failed for job {job_id}: {str(e)}")
        print(f"Extraction job {job_id} failed: {e}")

async def run_apify_job(job_id: str, config: ApifyConfig):
    """Background task to run Apify processing job with resume capability."""
    try:
        # Update job status
        apify_jobs[job_id]["status"] = "running"
        
        # Get API token from environment
        api_token = os.getenv('APIFY_API_KEY')
        if not api_token:
            raise Exception("APIFY_API_KEY environment variable not set")
        
        # Load URLs from file
        urls = load_linkedin_urls(config.urls_file)
        if not urls:
            raise Exception(f"No URLs found in {config.urls_file}")
        
        # Set up progress tracking
        progress_file = config.output_file.replace('.json', '_progress.json')
        
        # Clear progress if force_restart is enabled
        if config.force_restart:
            if os.path.exists(progress_file):
                os.remove(progress_file)
                add_terminal_log("INFO", f"🗑️ Cleared progress file for job {job_id} (force restart enabled)")
        
        processed_urls = load_progress(progress_file)
        remaining_urls = get_remaining_urls(urls, processed_urls)
        
        # Update progress with initial stats
        update_apify_job_progress(job_id, {
            "message": f"Loaded {len(urls)} URLs from {config.urls_file}",
            "total_urls": len(urls),
            "processed_urls": len(processed_urls),
            "remaining_urls": len(remaining_urls),
            "percentage": (len(processed_urls) / len(urls) * 100) if urls else 0,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check if all URLs are already processed
        if not remaining_urls:
            add_terminal_log("INFO", f"✅ All URLs have already been processed for job {job_id}")
            apify_jobs[job_id].update({
                "status": "completed",
                "completed_at": datetime.now(),
                "results": {
                    "total_urls": len(urls),
                    "processed_profiles": len(processed_urls),
                    "output_file": config.output_file,
                    "test_mode": config.test_mode,
                    "resumed": True
                }
            })
            return
        
        # Log resume information
        if len(processed_urls) > 0:
            add_terminal_log("INFO", f"🔄 RESUMING Apify job {job_id} from {len(processed_urls)} completed profiles")
            add_terminal_log("INFO", f"📊 Progress: {len(processed_urls)}/{len(urls)} processed ({len(remaining_urls)} remaining)")
        else:
            add_terminal_log("INFO", f"🚀 STARTING new Apify job {job_id} for {len(urls)} URLs")
        
        # Process URLs through Apify in thread pool
        loop = asyncio.get_event_loop()
        if config.test_mode:
            # Test mode - process limited URLs
            test_urls = urls[:config.test_num_urls]
            remaining_test_urls = get_remaining_urls(test_urls, processed_urls)
            if not remaining_test_urls:
                add_terminal_log("INFO", f"✅ All test URLs already processed for job {job_id}")
                apify_jobs[job_id].update({
                    "status": "completed",
                    "completed_at": datetime.now(),
                    "results": {
                        "total_urls": len(test_urls),
                        "processed_profiles": len(processed_urls),
                        "output_file": config.output_file,
                        "test_mode": config.test_mode,
                        "resumed": True
                    }
                })
                return
            
            results = await loop.run_in_executor(
                None,
                process_linkedin_profiles_with_resume,
                api_token, 
                remaining_test_urls, 
                config.output_file, 
                config.batch_size
            )
        else:
            # Full processing mode
            results = await loop.run_in_executor(
                None,
                process_linkedin_profiles_with_resume,
                api_token, 
                remaining_urls, 
                config.output_file, 
                config.batch_size
            )
        
        # Update job with results
        apify_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "results": {
                "total_urls": len(urls),
                "processed_profiles": len(results) if results else 0,
                "output_file": config.output_file,
                "test_mode": config.test_mode,
                "resumed": len(processed_urls) > 0
            }
        })
        
        add_terminal_log("INFO", f"✅ Apify job {job_id} completed successfully")
        
    except Exception as e:
        # Update job with error
        apify_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })
        
        add_terminal_log("ERROR", f"❌ Apify job {job_id} failed: {str(e)}")

async def run_data_cleaner_job(job_id: str, config: DataCleanerConfig):
    """Background task to run data cleaning job."""
    try:
        # Update job status
        data_cleaner_jobs[job_id]["status"] = "running"
        
        # Update progress
        update_data_cleaner_job_progress(job_id, {
            "message": f"Starting data cleaning for {config.input_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize data processor
        processor = LinkedInDataProcessor()
        
        # Update progress
        update_data_cleaner_job_progress(job_id, {
            "message": f"Loading profiles from {config.input_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Load and process profiles in thread pool
        loop = asyncio.get_event_loop()
        cleaned_profiles = await loop.run_in_executor(
            None,
            processor.load_and_process_file,
            config.input_file
        )
        
        # Update progress
        update_data_cleaner_job_progress(job_id, {
            "message": f"Processed {len(cleaned_profiles)} profiles, saving to {config.output_file}",
            "total_profiles": len(cleaned_profiles),
            "timestamp": datetime.now().isoformat()
        })
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(config.output_file), exist_ok=True)
        
        # Save cleaned data
        with open(config.output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_profiles, f, indent=2, ensure_ascii=False)
        
        # Update job with results
        data_cleaner_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "results": {
                "total_profiles": len(cleaned_profiles),
                "input_file": config.input_file,
                "output_file": config.output_file
            }
        })
        
    except Exception as e:
        # Update job with error
        data_cleaner_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })

async def run_trait_extractor_job(job_id: str, config: TraitExtractorConfig):
    """Background task to run trait extraction job."""
    try:
        # Update job status
        trait_extractor_jobs[job_id]["status"] = "running"
        
        # Update progress
        update_trait_extractor_job_progress(job_id, {
            "message": f"Starting trait extraction for {config.input_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize trait extractor
        extractor = LinkedInTraitExtractor()
        
        # Update progress
        update_trait_extractor_job_progress(job_id, {
            "message": f"Loading profiles from {config.input_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Load profiles
        with open(config.input_file, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        
        update_trait_extractor_job_progress(job_id, {
            "message": f"Loaded {len(profiles)} profiles, starting extraction",
            "total_profiles": len(profiles),
            "processed_profiles": 0,
            "timestamp": datetime.now().isoformat()
        })
        
        # Extract traits with progress tracking in thread pool
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            extractor.extract_traits_from_profiles,
            profiles,
            config.delay_between_calls,
            config.max_profiles,
            config.force_reextraction,
            None,  # progress_file - let the method auto-generate it
            config.output_file
        )
        
        # Update job with results
        trait_extractor_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "results": {
                "total_profiles": len(profiles),
                "processed_profiles": len(results),
                "input_file": config.input_file,
                "output_file": config.output_file,
                "max_profiles": config.max_profiles,
                "force_reextraction": config.force_reextraction
            }
        })
        
    except Exception as e:
        # Update job with error
        trait_extractor_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })

async def run_airtable_updater_job(job_id: str, config: AirtableUpdaterConfig):
    """Background task to run Airtable update job."""
    try:
        # Update job status
        airtable_updater_jobs[job_id]["status"] = "running"
        
        # Update progress
        update_airtable_updater_job_progress(job_id, {
            "message": f"Starting Airtable update for {config.traits_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize Airtable updater with custom base_id and table_id
        updater = AirtableTraitUpdater(base_id=config.base_id, table_id=config.table_id)
        
        # Update progress
        update_airtable_updater_job_progress(job_id, {
            "message": f"Loading trait data from {config.traits_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Load data (we'll override the file paths)
        try:
            with open(config.traits_file, 'r', encoding='utf-8') as f:
                updater.trait_data = json.load(f)
            print(f"✓ Loaded {len(updater.trait_data)} trait extraction results")
            
            with open(config.url_mapping_file, 'r', encoding='utf-8') as f:
                updater.url_mapping = json.load(f)
            print(f"✓ Loaded {len(updater.url_mapping)} URL mappings")
            
        except FileNotFoundError as e:
            raise Exception(f"File not found: {e}")
        except Exception as e:
            raise Exception(f"Error loading data: {e}")
        
        update_airtable_updater_job_progress(job_id, {
            "message": f"Loaded {len(updater.trait_data)} traits and {len(updater.url_mapping)} mappings, starting updates",
            "total_traits": len(updater.trait_data),
            "total_mappings": len(updater.url_mapping),
            "processed_updates": 0,
            "timestamp": datetime.now().isoformat()
        })
        
        # Process trait extractions and update Airtable in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            updater.process_trait_extractions,
            config.delay_between_updates
        )
        
        # Update job with results
        airtable_updater_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "results": {
                "total_traits": len(updater.trait_data),
                "successful_updates": updater.update_results['successful_updates'],
                "failed_updates": updater.update_results['failed_updates'],
                "missing_mappings": updater.update_results['missing_mappings'],
                "traits_file": config.traits_file,
                "url_mapping_file": config.url_mapping_file
            }
        })
        
    except Exception as e:
        # Update job with error
        airtable_updater_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Airtable LinkedIn URL Extractor API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "jobs": "/jobs",
            "extract": "/extract",
            "apify": "/apify/process",
            "cleaner": "/cleaner/process",
            "traits": "/traits/process",
            "airtable": "/airtable/update"
        }
    }

@app.get("/test")
async def test_endpoint():
    """Simple test endpoint to check if the API is responsive."""
    return {
        "status": "ok",
        "message": "API is responsive",
        "timestamp": datetime.now().isoformat()
    }


'''
This actually calls the funciotn to extract all the linked in data

'''
@app.post("/extract", response_model=Dict[str, str])
async def start_extraction(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks
):
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in extraction_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        extraction_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_extraction_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Extraction job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start extraction job: {str(e)}"
        )


@app.get("/status/{job_id}", response_model=ExtractionStatus)
async def get_job_status(job_id: str):
    """Get the status of an extraction job."""
    if job_id not in extraction_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    
    job_data = extraction_jobs[job_id]
    return ExtractionStatus(**job_data)

@app.get("/results/{job_id}")
async def get_job_results(job_id: str):
    """Get the results of a completed extraction job."""
    if job_id not in extraction_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    
    job_data = extraction_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/jobs")
async def list_jobs():
    """List all extraction jobs."""
    return {
        "total_jobs": len(extraction_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in extraction_jobs.items()
        ]
    }

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from memory."""
    if job_id not in extraction_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    
    del extraction_jobs[job_id]
    return {"message": f"Job '{job_id}' deleted successfully"}

@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    if job_id not in extraction_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    
    job_data = extraction_jobs[job_id]
    if job_data["status"] not in ["queued", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' cannot be cancelled. Current status: {job_data['status']}"
        )
    
    # Mark job for cancellation
    cancellation_requests[job_id] = True
    job_data["status"] = "cancelled"
    job_data["completed_at"] = datetime.now().isoformat()
    
    # Kill all processes associated with this job
    kill_results = kill_job_processes(job_id)
    
    add_terminal_log("INFO", f"Job '{job_id}' cancelled by user")
    add_terminal_log("INFO", f"Killed {kill_results['processes_killed']} processes for job {job_id}")
    
    return {
        "message": f"Job '{job_id}' cancelled successfully",
        "processes_killed": kill_results['processes_killed'],
        "processes_found": kill_results['processes_found']
    }

@app.post("/cancel-all-jobs")
async def cancel_all_jobs():
    """Cancel all running jobs and kill job processes only."""
    try:
        # Mark all running jobs for cancellation
        cancelled_jobs = 0
        total_processes_killed = 0
        
        # Cancel extraction jobs and kill their processes
        for job_id, job_data in extraction_jobs.items():
            if job_data["status"] in ["queued", "running"]:
                cancellation_requests[job_id] = True
                job_data["status"] = "cancelled"
                job_data["completed_at"] = datetime.now().isoformat()
                cancelled_jobs += 1
                
                # Kill processes for this specific job
                kill_results = kill_job_processes(job_id)
                total_processes_killed += kill_results['processes_killed']
        
        # Cancel apify jobs and kill their processes
        for job_id, job_data in apify_jobs.items():
            if job_data["status"] in ["queued", "running"]:
                cancellation_requests[job_id] = True
                job_data["status"] = "cancelled"
                job_data["completed_at"] = datetime.now().isoformat()
                cancelled_jobs += 1
                
                # Kill processes for this specific job
                kill_results = kill_job_processes(job_id)
                total_processes_killed += kill_results['processes_killed']
        
        # Cancel data cleaner jobs and kill their processes
        for job_id, job_data in data_cleaner_jobs.items():
            if job_data["status"] in ["queued", "running"]:
                cancellation_requests[job_id] = True
                job_data["status"] = "cancelled"
                job_data["completed_at"] = datetime.now().isoformat()
                cancelled_jobs += 1
                
                # Kill processes for this specific job
                kill_results = kill_job_processes(job_id)
                total_processes_killed += kill_results['processes_killed']
        
        # Cancel trait extractor jobs and kill their processes
        for job_id, job_data in trait_extractor_jobs.items():
            if job_data["status"] in ["queued", "running"]:
                cancellation_requests[job_id] = True
                job_data["status"] = "cancelled"
                job_data["completed_at"] = datetime.now().isoformat()
                cancelled_jobs += 1
                
                # Kill processes for this specific job
                kill_results = kill_job_processes(job_id)
                total_processes_killed += kill_results['processes_killed']
        
        # Cancel airtable updater jobs and kill their processes
        for job_id, job_data in airtable_updater_jobs.items():
            if job_data["status"] in ["queued", "running"]:
                cancellation_requests[job_id] = True
                job_data["status"] = "cancelled"
                job_data["completed_at"] = datetime.now().isoformat()
                cancelled_jobs += 1
                
                # Kill processes for this specific job
                kill_results = kill_job_processes(job_id)
                total_processes_killed += kill_results['processes_killed']
        
        add_terminal_log("INFO", f"Emergency stop: Cancelled {cancelled_jobs} jobs")
        add_terminal_log("INFO", f"Emergency stop: Killed {total_processes_killed} job processes")
        
        return {
            "message": "All jobs cancelled and job processes killed",
            "jobs_cancelled": cancelled_jobs,
            "processes_killed": total_processes_killed
        }
        
    except Exception as e:
        add_terminal_log("ERROR", f"Error in cancel_all_jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel all jobs: {str(e)}"
        )

@app.post("/emergency-restart")
async def emergency_restart():
    """Emergency restart - kills all processes and restarts services."""
    try:
        add_terminal_log("INFO", "🚨 Emergency restart initiated")
        
        # Get the directory of the current script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        batch_file = os.path.join(current_dir, "emergency_restart_services.bat")
        
        if not os.path.exists(batch_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergency restart batch file not found"
            )
        
        # Execute the batch file in a new process
        # Use subprocess.Popen to start it without waiting
        subprocess.Popen([batch_file], 
                        cwd=current_dir,
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
        
        add_terminal_log("INFO", "🔄 Emergency restart batch file executed")
        
        return {
            "message": "Emergency restart initiated",
            "status": "restarting",
            "note": "Services will restart in a new window. Please wait for them to come back online."
        }
        
    except Exception as e:
        add_terminal_log("ERROR", f"Error in emergency restart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate emergency restart: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in extraction_jobs.values() if j["status"] == "running"]),
        "total_jobs": len(extraction_jobs),
        "active_apify_jobs": len([j for j in apify_jobs.values() if j["status"] == "running"]),
        "total_apify_jobs": len(apify_jobs),
        "active_cleaner_jobs": len([j for j in data_cleaner_jobs.values() if j["status"] == "running"]),
        "total_cleaner_jobs": len(data_cleaner_jobs),
        "active_trait_jobs": len([j for j in trait_extractor_jobs.values() if j["status"] == "running"]),
        "total_trait_jobs": len(trait_extractor_jobs),
        "active_airtable_updater_jobs": len([j for j in airtable_updater_jobs.values() if j["status"] == "running"]),
        "total_airtable_updater_jobs": len(airtable_updater_jobs)
    }

@app.get("/terminal-logs")
async def get_terminal_logs():
    """Get terminal logs for display in frontend."""
    return {
        "logs": terminal_logs,
        "total_logs": len(terminal_logs),
        "max_logs": MAX_LOGS
    }

@app.delete("/terminal-logs")
async def clear_terminal_logs():
    """Clear all terminal logs."""
    global terminal_logs
    terminal_logs.clear()
    return {"message": "Terminal logs cleared successfully"}

def clear_apify_progress(output_file: str):
    """Clear progress for a specific Apify job."""
    progress_file = output_file.replace('.json', '_progress.json')
    if os.path.exists(progress_file):
        os.remove(progress_file)
        add_terminal_log("INFO", f"🗑️ Cleared progress file: {progress_file}")
        return {"message": f"Progress cleared for {output_file}"}
    else:
        add_terminal_log("INFO", f"ℹ️ No progress file to clear: {progress_file}")
        return {"message": f"No progress file found for {output_file}"}

@app.post("/apify/clear-progress")
async def clear_apify_progress_endpoint(output_file: str):
    """Clear progress for a specific Apify job."""
    return clear_apify_progress(output_file)

# Apify Processing Endpoints
@app.post("/apify/process", response_model=Dict[str, str])
async def start_apify_processing(
    request: ApifyRequest,
    background_tasks: BackgroundTasks
):
    """Start a new Apify LinkedIn profile processing job."""
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in apify_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        apify_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_apify_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Apify processing job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Apify processing job: {str(e)}"
        )

@app.get("/apify/status/{job_id}", response_model=ApifyStatus)
async def get_apify_job_status(job_id: str):
    """Get the status of an Apify processing job."""
    if job_id not in apify_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Apify job '{job_id}' not found"
        )
    
    job_data = apify_jobs[job_id]
    return ApifyStatus(**job_data)

@app.get("/apify/results/{job_id}")
async def get_apify_job_results(job_id: str):
    """Get the results of a completed Apify processing job."""
    if job_id not in apify_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Apify job '{job_id}' not found"
        )
    
    job_data = apify_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Apify job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/apify/jobs")
async def list_apify_jobs():
    """List all Apify processing jobs."""
    return {
        "total_jobs": len(apify_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in apify_jobs.items()
        ]
    }

@app.delete("/apify/jobs/{job_id}")
async def delete_apify_job(job_id: str):
    """Delete an Apify job from memory."""
    if job_id not in apify_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Apify job '{job_id}' not found"
        )
    
    del apify_jobs[job_id]
    return {"message": f"Apify job '{job_id}' deleted successfully"}

@app.post("/apify/jobs/{job_id}/cancel")
async def cancel_apify_job(job_id: str):
    """Cancel a running Apify job."""
    if job_id not in apify_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Apify job '{job_id}' not found"
        )
    
    job_data = apify_jobs[job_id]
    if job_data["status"] not in ["queued", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Apify job '{job_id}' cannot be cancelled. Current status: {job_data['status']}"
        )
    
    # Mark job for cancellation
    cancellation_requests[job_id] = True
    job_data["status"] = "cancelled"
    job_data["completed_at"] = datetime.now().isoformat()
    
    add_terminal_log("info", f"Apify job '{job_id}' cancelled by user")
    
    return {"message": f"Apify job '{job_id}' cancelled successfully"}

# Data Cleaner Endpoints
@app.post("/cleaner/process", response_model=Dict[str, str])
async def start_data_cleaning(
    request: DataCleanerRequest,
    background_tasks: BackgroundTasks
):
    """Start a new data cleaning job."""
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in data_cleaner_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data cleaner job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        data_cleaner_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_data_cleaner_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Data cleaning job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start data cleaning job: {str(e)}"
        )

@app.get("/cleaner/status/{job_id}", response_model=DataCleanerStatus)
async def get_data_cleaner_job_status(job_id: str):
    """Get the status of a data cleaning job."""
    if job_id not in data_cleaner_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data cleaner job '{job_id}' not found"
        )
    
    job_data = data_cleaner_jobs[job_id]
    return DataCleanerStatus(**job_data)

@app.get("/cleaner/results/{job_id}")
async def get_data_cleaner_job_results(job_id: str):
    """Get the results of a completed data cleaning job."""
    if job_id not in data_cleaner_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data cleaner job '{job_id}' not found"
        )
    
    job_data = data_cleaner_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data cleaner job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/cleaner/jobs")
async def list_data_cleaner_jobs():
    """List all data cleaning jobs."""
    return {
        "total_jobs": len(data_cleaner_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in data_cleaner_jobs.items()
        ]
    }

@app.delete("/cleaner/jobs/{job_id}")
async def delete_data_cleaner_job(job_id: str):
    """Delete a data cleaner job from memory."""
    if job_id not in data_cleaner_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data cleaner job '{job_id}' not found"
        )
    
    del data_cleaner_jobs[job_id]
    return {"message": f"Data cleaner job '{job_id}' deleted successfully"}

@app.post("/cleaner/jobs/{job_id}/cancel")
async def cancel_data_cleaner_job(job_id: str):
    """Cancel a running data cleaner job."""
    if job_id not in data_cleaner_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data cleaner job '{job_id}' not found"
        )
    
    job_data = data_cleaner_jobs[job_id]
    if job_data["status"] not in ["queued", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data cleaner job '{job_id}' cannot be cancelled. Current status: {job_data['status']}"
        )
    
    # Mark job for cancellation
    cancellation_requests[job_id] = True
    job_data["status"] = "cancelled"
    job_data["completed_at"] = datetime.now().isoformat()
    
    add_terminal_log("info", f"Data cleaner job '{job_id}' cancelled by user")
    
    return {"message": f"Data cleaner job '{job_id}' cancelled successfully"}

# Trait Extractor Endpoints
@app.post("/traits/process", response_model=Dict[str, str])
async def start_trait_extraction(
    request: TraitExtractorRequest,
    background_tasks: BackgroundTasks
):
    """Start a new trait extraction job."""
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in trait_extractor_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Trait extractor job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        trait_extractor_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_trait_extractor_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Trait extraction job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start trait extraction job: {str(e)}"
        )

@app.get("/traits/status/{job_id}", response_model=TraitExtractorStatus)
async def get_trait_extractor_job_status(job_id: str):
    """Get the status of a trait extraction job."""
    if job_id not in trait_extractor_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trait extractor job '{job_id}' not found"
        )
    
    job_data = trait_extractor_jobs[job_id]
    return TraitExtractorStatus(**job_data)

@app.get("/traits/results/{job_id}")
async def get_trait_extractor_job_results(job_id: str):
    """Get the results of a completed trait extraction job."""
    if job_id not in trait_extractor_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trait extractor job '{job_id}' not found"
        )
    
    job_data = trait_extractor_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trait extractor job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/traits/jobs")
async def list_trait_extractor_jobs():
    """List all trait extraction jobs."""
    return {
        "total_jobs": len(trait_extractor_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in trait_extractor_jobs.items()
        ]
    }

@app.delete("/traits/jobs/{job_id}")
async def delete_trait_extractor_job(job_id: str):
    """Delete a trait extractor job from memory."""
    if job_id not in trait_extractor_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trait extractor job '{job_id}' not found"
        )
    
    del trait_extractor_jobs[job_id]
    return {"message": f"Trait extractor job '{job_id}' deleted successfully"}

@app.post("/traits/jobs/{job_id}/cancel")
async def cancel_trait_extractor_job(job_id: str):
    """Cancel a running trait extractor job."""
    if job_id not in trait_extractor_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trait extractor job '{job_id}' not found"
        )
    
    job_data = trait_extractor_jobs[job_id]
    if job_data["status"] not in ["queued", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trait extractor job '{job_id}' cannot be cancelled. Current status: {job_data['status']}"
        )
    
    # Mark job for cancellation
    cancellation_requests[job_id] = True
    job_data["status"] = "cancelled"
    job_data["completed_at"] = datetime.now().isoformat()
    
    add_terminal_log("info", f"Trait extractor job '{job_id}' cancelled by user")
    
    return {"message": f"Trait extractor job '{job_id}' cancelled successfully"}

# Airtable Updater Endpoints
@app.post("/airtable/update", response_model=Dict[str, str])
async def start_airtable_update(
    request: AirtableUpdaterRequest,
    background_tasks: BackgroundTasks
):
    """Start a new Airtable update job."""
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in airtable_updater_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Airtable updater job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        airtable_updater_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_airtable_updater_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Airtable update job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Airtable update job: {str(e)}"
        )

@app.get("/airtable/status/{job_id}", response_model=AirtableUpdaterStatus)
async def get_airtable_updater_job_status(job_id: str):
    """Get the status of an Airtable update job."""
    if job_id not in airtable_updater_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airtable updater job '{job_id}' not found"
        )
    
    job_data = airtable_updater_jobs[job_id]
    return AirtableUpdaterStatus(**job_data)

@app.get("/airtable/results/{job_id}")
async def get_airtable_updater_job_results(job_id: str):
    """Get the results of a completed Airtable update job."""
    if job_id not in airtable_updater_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airtable updater job '{job_id}' not found"
        )
    
    job_data = airtable_updater_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Airtable updater job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/airtable/jobs")
async def list_airtable_updater_jobs():
    """List all Airtable update jobs."""
    return {
        "total_jobs": len(airtable_updater_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in airtable_updater_jobs.items()
        ]
    }

@app.delete("/airtable/jobs/{job_id}")
async def delete_airtable_updater_job(job_id: str):
    """Delete an Airtable updater job from memory."""
    if job_id not in airtable_updater_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airtable updater job '{job_id}' not found"
        )
    
    del airtable_updater_jobs[job_id]
    return {"message": f"Airtable updater job '{job_id}' deleted successfully"}

@app.post("/airtable/jobs/{job_id}/cancel")
async def cancel_airtable_updater_job(job_id: str):
    """Cancel a running Airtable updater job."""
    if job_id not in airtable_updater_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airtable updater job '{job_id}' not found"
        )
    
    job_data = airtable_updater_jobs[job_id]
    if job_data["status"] not in ["queued", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Airtable updater job '{job_id}' cannot be cancelled. Current status: {job_data['status']}"
        )
    
    # Mark job for cancellation
    cancellation_requests[job_id] = True
    job_data["status"] = "cancelled"
    job_data["completed_at"] = datetime.now().isoformat()
    
    add_terminal_log("info", f"Airtable updater job '{job_id}' cancelled by user")
    
    return {"message": f"Airtable updater job '{job_id}' cancelled successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 