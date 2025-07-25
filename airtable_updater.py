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

# Load environment variables
load_dotenv()

class AirtableTraitUpdater:
    """Update Airtable records with extracted LinkedIn traits."""
    
    def __init__(self):
        """Initialize the Airtable connection."""
        self.api_key = os.getenv('AIRTABLE_API_KEY')
        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY environment variable not set")
        
        self.api = Api(self.api_key)
        self.base_id = 'appCicrQbZaRq1Tvo'
        self.table_id = 'tblIJ47Fniuu9EJat'
        self.table = self.api.table(self.base_id, self.table_id)
        
        # Data storage
        self.url_mapping: Dict[str, str] = {}
        self.trait_data: List[Dict[str, Any]] = []
        self.update_results = {
            'successful_updates': 0,
            'failed_updates': 0,
            'missing_mappings': 0,
            'errors': []
        }
    
    def load_data(self):
        """Load trait extraction results and URL mapping."""
        print("Loading data files...")
        
        # Load trait extraction results
        try:
            with open('final-trait-extractions/S25Top100_comprehensive_traits.json', 'r', encoding='utf-8') as f:
                self.trait_data = json.load(f)
            print(f"✓ Loaded {len(self.trait_data)} trait extraction results")
        except FileNotFoundError:
            print("❌ Trait extraction file not found: final-trait-extractions/S25Top100_comprehensive_traits.json")
            raise
        except Exception as e:
            print(f"❌ Error loading trait data: {e}")
            raise
        
        # Load URL mapping
        try:
            with open('airtable-extractions/S25Top100airtable_url_mapping.json', 'r', encoding='utf-8') as f:
                self.url_mapping = json.load(f)
            print(f"✓ Loaded {len(self.url_mapping)} URL mappings")
        except FileNotFoundError:
            print("❌ URL mapping file not found: airtable-extractions/S25Top100airtable_url_mapping.json")
            raise
        except Exception as e:
            print(f"❌ Error loading URL mapping: {e}")
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
        
        # Basic info
        if traits.get('full_name'):
            formatted_data['AI_Full_Name'] = traits['full_name']
            
            print(formatted_data['AI_Full_Name'])
        if traits.get('estimated_age'):
            formatted_data['AI_Estimated_Age'] = traits['estimated_age']
            print(formatted_data['AI_Estimated_Age'])
        if traits.get('confidence_score'):
            formatted_data['AI_Confidence_Score'] = traits['confidence_score']
        
        # Education stages
        education = traits.get('education_stages', {})
        if education.get('undergraduate'):
            formatted_data['AI_Undergraduate'] = education['undergraduate']
        if education.get('masters'):
            formatted_data['AI_Masters'] = education['masters']
        if education.get('phd'):
            formatted_data['AI_PhD'] = education['phd']
        if education.get('other_education'):
            formatted_data['AI_Other_Education'] = ', '.join(education['other_education'])
        
        # Career insights
        career = traits.get('career_insights', {})
        if career.get('total_years_experience'):
            formatted_data['AI_Total_Years_Experience'] = career['total_years_experience']
        if career.get('avg_tenure_per_role'):
            formatted_data['AI_Avg_Tenure_Per_Role'] = career['avg_tenure_per_role']
        if career.get('job_hopper') is not None:
            formatted_data['AI_Job_Hopper'] = career['job_hopper']
        if career.get('total_experience_count'):
            formatted_data['AI_Total_Experience_Count'] = career['total_experience_count']
        if career.get('has_leadership_experience') is not None:
            formatted_data['AI_Has_Leadership_Experience'] = career['has_leadership_experience']
        if career.get('has_previous_c_suite_experience') is not None:
            formatted_data['AI_Has_C_Suite_Experience'] = career['has_previous_c_suite_experience']
        if career.get('founder_experience_count'):
            formatted_data['AI_Founder_Experience_Count'] = career['founder_experience_count']
        if career.get('industry_switches'):
            formatted_data['AI_Industry_Switches'] = career['industry_switches']
        if career.get('career_summary'):
            formatted_data['AI_Career_Summary'] = career['career_summary']
        
        
        # Company background
        company = traits.get('company_background', {})
        if company.get('notable_companies'):
            formatted_data['AI_Notable_Companies'] = ', '.join(company['notable_companies'])
        if company.get('startup_companies'):
            formatted_data['AI_Startup_Companies'] = ', '.join(company['startup_companies'])
        
        # Accelerators and programs
        accelerators = traits.get('accelerator_and_programs', {})
        if accelerators.get('accelerators'):
            formatted_data['AI_Accelerators'] = ', '.join(accelerators['accelerators'])
        if accelerators.get('fellowship_programs'):
            formatted_data['AI_Fellowship_Programs'] = ', '.join(accelerators['fellowship_programs'])   
        if accelerators.get('board_positions'):
            formatted_data['AI_Board_Positions'] = ', '.join(accelerators['board_positions'])
        
        # Education-career alignment
        alignment = traits.get('education_career_alignment', {})
        if alignment.get('studies_field'):
            formatted_data['AI_Studies_Field'] = alignment['studies_field']
        if alignment.get('current_field'):
            formatted_data['AI_Current_Field'] = alignment['current_field']
        if alignment.get('pivot_description'):
            formatted_data['AI_Pivot_Description'] = alignment['pivot_description']
        
        # Personal brand
        brand = traits.get('personal_brand', {})
        if brand.get('headline_keywords'):
            formatted_data['AI_Headline_Keywords'] = ', '.join(brand['headline_keywords'])
        
        # Research and academic
        research = traits.get('research_and_academic', {})
        if research.get('academic_roles'):
            formatted_data['AI_Academic_Roles'] = ', '.join(research['academic_roles'])
        
        # International experience
        international = traits.get('international_experience', {})
        if international.get('countries_worked'):
            formatted_data['AI_Countries_Worked'] = ', '.join(international['countries_worked'])
        
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
            self.table.update(record_id, formatted_data)
            return True
        except Exception as e:
            error_msg = f"Failed to update record {record_id}: {e}"
            print(f"  ❌ {error_msg}")
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
            
            print(f"Processing {i + 1}/{len(self.trait_data)}: {full_name}")
            
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
            
            print(f"  📝 Updating record {record_id} with {len(formatted_data)} fields...")
            
            # Update Airtable record
            if self.update_airtable_record(record_id, formatted_data):
                print(f"  ✓ Successfully updated")
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
    try:
        print("🚀 Starting Airtable trait update process...")
        
        updater = AirtableTraitUpdater()
        updater.load_data()
        updater.process_trait_extractions()
        updater.print_summary()
        
        print("\n✅ Airtable update process complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 