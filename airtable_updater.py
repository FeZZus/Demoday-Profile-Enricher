'''
Script to update Airtable with comprehensive LinkedIn trait extraction results.

This script:
1. Loads trait extraction results from S25Top100_comprehensive_traits.json
2. Maps LinkedIn URLs to Airtable record IDs using S25Top100airtable_url_mapping.json
3. Updates the Airtable table with structured trait data

Usage:
    python airtable_updater.py
'''

import os
import json
import time
from typing import Dict, List, Any, Optional
from pyairtable import Api
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

class AirtableTraitUpdater:
    """Update Airtable records with extracted LinkedIn traits."""
    
    def __init__(self, base_id: str = 'appCicrQbZaRq1Tvo', table_id: str = 'tblIJ47Fniuu9EJat', request_timeout_seconds: float = 30.0):
        """Initialize the Airtable connection."""
        self.api_key = os.getenv('AIRTABLE_API_KEY')
        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY environment variable not set")
        
        self.api = Api(self.api_key)
        self.base_id = base_id
        self.table_id = table_id
        self.table = self.api.table(self.base_id, self.table_id)

        # Network robustness: set default request timeout and retries for all Airtable calls
        # Avoids indefinite hangs if a request stalls
        self._request_timeout_seconds = request_timeout_seconds
        try:
            session = self.api.session
            retries = Retry(
                total=5,
                backoff_factor=0.8,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "PUT", "POST", "PATCH", "DELETE", "OPTIONS"]
            )
            adapter = HTTPAdapter(max_retries=retries)
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            original_request = session.request

            def request_with_timeout(method, url, **kwargs):
                kwargs.setdefault("timeout", self._request_timeout_seconds)
                return original_request(method, url, **kwargs)

            session.request = request_with_timeout  # type: ignore[attr-defined]
            self.api.session = session
        except Exception:
            # If session tweaking fails for any reason, continue without it
            pass
        
        # Data storage
        self.url_mapping: Dict[str, str] = {}
        self.trait_data: List[Dict[str, Any]] = []
        self.update_results = {
            'successful_updates': 0,
            'failed_updates': 0,
            'missing_mappings': 0,
            'errors': []
        }
    
    def load_data(self, traits_file: str = 'final-trait-extractions/S25Top100_comprehensive_traits.json', url_mapping_file: str = 'airtable-extractions/S25Top100airtable_url_mapping.json'):
        """Load trait extraction results and URL mapping."""
        print("Loading data files...", flush=True)
        
        # Load trait extraction results
        try:
            with open(traits_file, 'r', encoding='utf-8') as f:
                self.trait_data = json.load(f)
            print(f"✓ Loaded {len(self.trait_data)} trait extraction results from {traits_file}", flush=True)
        except FileNotFoundError:
            print(f"❌ Trait extraction file not found: {traits_file}", flush=True)
            raise
        except Exception as e:
            print(f"❌ Error loading trait data from {traits_file}: {e}", flush=True)
            raise
        
        # Load URL mapping
        try:
            with open(url_mapping_file, 'r', encoding='utf-8') as f:
                self.url_mapping = json.load(f)
            print(f"✓ Loaded {len(self.url_mapping)} URL mappings from {url_mapping_file}", flush=True)
        except FileNotFoundError:
            print(f"❌ URL mapping file not found: {url_mapping_file}", flush=True)
            raise
        except Exception as e:
            print(f"❌ Error loading URL mapping from {url_mapping_file}: {e}", flush=True)
            raise
    
    def format_trait_data_for_airtable(self, traits: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format comprehensive trait data for Airtable fields.
        
        Args:
            traits: Raw trait extraction data
            
        Returns:
            Formatted data for Airtable update
        """
        formatted_data = {}

        def is_meaningful(value: Any) -> bool:
            if value is None:
                return False
            # Treat -1 and "-1" and empty strings as missing/sentinel values
            if isinstance(value, (int, float)) and value == -1:
                return False
            string_value = str(value).strip()
            if string_value in ("", "-1"):
                return False
            return True

        def sanitize_list(values: Any) -> List[str]:
            if not isinstance(values, list):
                return []
            return [str(v) for v in values if is_meaningful(v)]
        
        # Basic info
        if is_meaningful(traits.get('full_name')):
            formatted_data['AI_Full_Name'] = traits['full_name']
            print(formatted_data['AI_Full_Name'])
        age_value = traits.get('estimated_age')
        if is_meaningful(age_value):
            formatted_data['AI_Estimated_Age'] = str(age_value)
            print(formatted_data['AI_Estimated_Age'])
        if traits.get('confidence_score'):
            formatted_data['AI_Confidence_Score'] = traits['confidence_score']
        
        # Education stages
        education = traits.get('education_stages', {})
        if is_meaningful(education.get('undergraduate')):
            formatted_data['AI_Undergraduate'] = education['undergraduate']
        if is_meaningful(education.get('masters')):
            formatted_data['AI_Masters'] = education['masters']
        if is_meaningful(education.get('phd')):
            formatted_data['AI_PhD'] = education['phd']
        other_edu_list = sanitize_list(education.get('other_education', []))
        if other_edu_list:
            formatted_data['AI_Other_Education'] = ', '.join(other_edu_list)
        
        # Career insights
        career = traits.get('career_insights', {})
        if is_meaningful(career.get('total_years_experience')):
            formatted_data['AI_Total_Years_Experience'] = career['total_years_experience']
        if is_meaningful(career.get('avg_tenure_per_role')):
            formatted_data['AI_Avg_Tenure_Per_Role'] = career['avg_tenure_per_role']
        if career.get('job_hopper') is not None:
            formatted_data['AI_Job_Hopper'] = career['job_hopper']
        if is_meaningful(career.get('total_experience_count')):
            formatted_data['AI_Total_Experience_Count'] = career['total_experience_count']
        if career.get('has_leadership_experience') is not None:
            formatted_data['AI_Has_Leadership_Experience'] = career['has_leadership_experience']
        if career.get('has_previous_c_suite_experience') is not None:
            formatted_data['AI_Has_C_Suite_Experience'] = career['has_previous_c_suite_experience']
        if is_meaningful(career.get('founder_experience_count')):
            formatted_data['AI_Founder_Experience_Count'] = career['founder_experience_count']
        if is_meaningful(career.get('industry_switches')):
            formatted_data['AI_Industry_Switches'] = career['industry_switches']
        if is_meaningful(career.get('years_out_of_education')):
            formatted_data['AI_Years_Out_Of_Education'] = career['years_out_of_education']
        if is_meaningful(career.get('years_in_industry')):
            formatted_data['AI_Years_In_Industry'] = career['years_in_industry']
        if is_meaningful(career.get('career_summary')):
            formatted_data['AI_Career_Summary'] = career['career_summary']
        
        
        # Company background
        company = traits.get('company_background', {})
        notable_list = sanitize_list(company.get('notable_companies', []))
        if notable_list:
            formatted_data['AI_Notable_Companies'] = ', '.join(notable_list)
        startup_list = sanitize_list(company.get('startup_companies', []))
        if startup_list:
            formatted_data['AI_Startup_Companies'] = ', '.join(startup_list)
        
        # Accelerators and programs
        accelerators = traits.get('accelerator_and_programs', {})
        accelerators_list = sanitize_list(accelerators.get('accelerators', []))
        if accelerators_list:
            formatted_data['AI_Accelerators'] = ', '.join(accelerators_list)
        fellowship_list = sanitize_list(accelerators.get('fellowship_programs', []))
        if fellowship_list:
            formatted_data['AI_Fellowship_Programs'] = ', '.join(fellowship_list)   
        board_positions_list = sanitize_list(accelerators.get('board_positions', []))
        if board_positions_list:
            formatted_data['AI_Board_Positions'] = ', '.join(board_positions_list)
        
        # Education-career alignment
        alignment = traits.get('education_career_alignment', {})
        if is_meaningful(alignment.get('studies_field')):
            formatted_data['AI_Studies_Field'] = alignment['studies_field']
        if is_meaningful(alignment.get('current_field')):
            formatted_data['AI_Current_Field'] = alignment['current_field']
        if is_meaningful(alignment.get('pivot_description')):
            formatted_data['AI_Pivot_Description'] = alignment['pivot_description']
        
        # Personal brand
        brand = traits.get('personal_brand', {})
        headline_list = sanitize_list(brand.get('headline_keywords', []))
        if headline_list:
            formatted_data['AI_Headline_Keywords'] = ', '.join(headline_list)
        
        # Research and academic
        research = traits.get('research_and_academic', {})
        academic_roles_list = sanitize_list(research.get('academic_roles', []))
        if academic_roles_list:
            formatted_data['AI_Academic_Roles'] = ', '.join(academic_roles_list)
        
        # International experience
        international = traits.get('international_experience', {})
        countries_list = sanitize_list(international.get('countries_worked', []))
        if countries_list:
            formatted_data['AI_Countries_Worked'] = ', '.join(countries_list)
        
        return formatted_data
    
    def update_airtable_record(self, record_id: str, formatted_data: Dict[str, Any]) -> bool:
        """
        Update a single Airtable record with trait data.
        
        Args:
            record_id: Airtable record ID
            formatted_data: Formatted trait data for Airtable
            
        Returns:
            True if successful, False if failed
        """
        try:
            # Perform update; the Session has a default timeout and retries configured
            self.table.update(record_id, formatted_data)
            return True
        except requests.exceptions.Timeout:
            error_msg = f"Timeout updating record {record_id} after {self._request_timeout_seconds}s"
            print(f"  ❌ {error_msg}", flush=True)
            self.update_results['errors'].append(error_msg)
            return False
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error updating record {record_id}: {e}"
            print(f"  ❌ {error_msg}", flush=True)
            self.update_results['errors'].append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Failed to update record {record_id}: {e}"
            print(f"  ❌ {error_msg}", flush=True)
            self.update_results['errors'].append(error_msg)
            return False
    
    def process_trait_extractions(self, delay_between_updates: float = 0.5):
        """
        Process all trait extractions and update Airtable.
        
        Args:
            delay_between_updates: Delay in seconds between Airtable updates
        """
        print(f"\nProcessing {len(self.trait_data)} trait extractions...")
        print("-" * 60)
        
        for i, traits in enumerate(self.trait_data):
            linkedin_url = traits.get('linkedin_url')
            full_name = traits.get('full_name', 'Unknown')
            
            print(f"Processing {i + 1}/{len(self.trait_data)}: {full_name}", flush=True)
            
            if not linkedin_url:
                print(f"  ⚠️  No LinkedIn URL found in trait data")
                self.update_results['missing_mappings'] += 1
                continue
            
            # Find corresponding Airtable record ID
            record_id = self.url_mapping.get(linkedin_url)
            if not record_id:
                print(f"  ⚠️  No Airtable record found for URL: {linkedin_url}")
                self.update_results['missing_mappings'] += 1
                continue
            
            # Format data for Airtable
            formatted_data = self.format_trait_data_for_airtable(traits)
            
            if not formatted_data:
                print(f"  ⚠️  No valid data to update")
                continue
            
            print(f"  📝 Updating record {record_id} with {len(formatted_data)} fields...", flush=True)
            
            # Update Airtable record
            if self.update_airtable_record(record_id, formatted_data):
                print(f"  ✓ Successfully updated", flush=True)
                self.update_results['successful_updates'] += 1
            else:
                self.update_results['failed_updates'] += 1
            
            # Rate limiting
            if i < len(self.trait_data) - 1:
                time.sleep(delay_between_updates)
    
    def print_summary(self):
        """Print update summary."""
        print("\n" + "="*60)
        print("AIRTABLE UPDATE SUMMARY")
        print("="*60)
        print(f"Total trait records processed: {len(self.trait_data)}")
        print(f"Successful updates: {self.update_results['successful_updates']}")
        print(f"Failed updates: {self.update_results['failed_updates']}")
        print(f"Missing URL mappings: {self.update_results['missing_mappings']}")
        
        if self.update_results['successful_updates'] > 0:
            success_rate = (self.update_results['successful_updates'] / len(self.trait_data)) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        if self.update_results['errors']:
            print(f"\nFirst few errors:")
            for error in self.update_results['errors'][:5]:
                print(f"  - {error}")
            if len(self.update_results['errors']) > 5:
                print(f"  ... and {len(self.update_results['errors']) - 5} more")

def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update Airtable with trait extraction results')
    parser.add_argument('--base-id', default='appCicrQbZaRq1Tvo', help='Airtable base ID')
    parser.add_argument('--table-id', default='tblIJ47Fniuu9EJat', help='Airtable table ID')
    parser.add_argument('--traits-file', default='final-trait-extractions/S25Top100_comprehensive_traits.json', help='Path to traits JSON (e.g., S25All_comprehensive_traits.json)')
    parser.add_argument('--url-mapping-file', default='airtable-extractions/S25Top100airtable_url_mapping.json', help='Path to URL mapping JSON (e.g., S25Allairtable_url_mapping.json)')
    parser.add_argument('--timeout-seconds', type=float, default=30.0, help='Per-request network timeout')
    
    args = parser.parse_args()
    
    try:
        print("🚀 Starting Airtable trait update process...")
        
        updater = AirtableTraitUpdater(base_id=args.base_id, table_id=args.table_id, request_timeout_seconds=args.timeout_seconds)
        updater.load_data(traits_file=args.traits_file, url_mapping_file=args.url_mapping_file)
        updater.process_trait_extractions()
        updater.print_summary()
        
        print("\n✅ Airtable update process complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 