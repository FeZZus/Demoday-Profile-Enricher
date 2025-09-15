'''
Step 4: After cleaning up all the profile data, throw it all into chatgpt and get meaningful insights from it

Note:
 - atm saving to s25top100 file
 - just testing on 2 files atm 
 - NEED TO GET THE JSON FILES TO HAVE THE CORRECT LINKED IN URL AS WELL TO LINK IT BACK TO THE AIRTABLE

Progress Tracking Features:
 - Tracks which profiles have already been processed
 - Can resume extraction from where it left off
 - Option to force re-extraction when system prompt changes
 - Saves progress incrementally to avoid losing work

'''

import json
import os
import time
from typing import Dict, List, Any, Optional, Set
from openai import OpenAI
from dataclasses import dataclass
import dotenv

dotenv.load_dotenv()

def main():
    # CONFIGURATION
    NUMBER_PROFILES = -1        # Number of profiles to process in this session
    FORCE_REEXTRACTION = False  # Set to True when you want to re-extract all profiles (e.g., after changing system prompt)
    
    # USAGE EXAMPLES:
    # 1. First run: Extract 30 profiles
    #    NUMBER_PROFILES = 30, FORCE_REEXTRACTION = False
    # 
    # 2. Continue from where you left off: Extract next 30 profiles  
    #    NUMBER_PROFILES = 30, FORCE_REEXTRACTION = False
    #
    # 3. Re-extract all profiles (e.g., after changing system prompt):
    #    NUMBER_PROFILES = -1, FORCE_REEXTRACTION = True
    #
    # 4. Extract all remaining profiles:
    #    NUMBER_PROFILES = -1, FORCE_REEXTRACTION = False
    #
    # 5. Check progress without processing:
    #    Uncomment the progress check section below
    
    """Example usage of the LinkedInTraitExtractor with progress tracking."""
    # Initialize extractor
    extractor = LinkedInTraitExtractor()
    
    # Optional: Check progress before starting
    # extractor.check_progress(
    #     'cleaned-profile-data/S25Top100cleaned_linkedin_data.json',
    #     'final-trait-extractions/S25Top100_comprehensive_traits.json'
    # )
    
    # Load cleaned profiles
    with open('cleaned-profile-data/S25Top100cleaned_linkedin_data.json', 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    
    print(f"Loaded {len(profiles)} cleaned profiles")
    
    # Extract traits with progress tracking
    results = extractor.extract_traits_from_profiles(
        profiles, 
        max_profiles=NUMBER_PROFILES,
        force_reextraction=FORCE_REEXTRACTION,
        output_file='final-trait-extractions/S25Top100_comprehensive_traits.json'
    )
    
    print(f"Processed {len(results)} profiles successfully")


def demonstrate_progress_tracking():
    """Demonstrate the new progress tracking functionality."""
    print("🧪 DEMONSTRATING PROGRESS TRACKING")
    print("=" * 50)
    
    extractor = LinkedInTraitExtractor()
    
    # Example 1: Check progress without processing
    print("\n1. Checking progress...")
    progress_stats = extractor.check_progress(
        'cleaned-profile-data/S25Top100cleaned_linkedin_data.json',
        'final-trait-extractions/S25Top100_comprehensive_traits.json'
    )
    
    # Example 2: Process a few profiles with progress tracking
    print("\n2. Processing 5 profiles with progress tracking...")
    with open('cleaned-profile-data/S25Top100cleaned_linkedin_data.json', 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    
    results = extractor.extract_traits_from_profiles(
        profiles, 
        max_profiles=5,
        force_reextraction=False,
        output_file='final-trait-extractions/S25Top100_comprehensive_traits.json'
    )
    
    # Example 3: Check progress again
    print("\n3. Checking progress after processing...")
    progress_stats_after = extractor.check_progress(
        'cleaned-profile-data/S25Top100cleaned_linkedin_data.json',
        'final-trait-extractions/S25Top100_comprehensive_traits.json'
    )
    
    # Example 4: Force re-extraction
    print("\n4. Force re-extraction of 2 profiles...")
    results_force = extractor.extract_traits_from_profiles(
        profiles, 
        max_profiles=2,
        force_reextraction=True,
        output_file='final-trait-extractions/S25Top100_comprehensive_traits.json'
    )
    
    print("\n✅ Progress tracking demonstration completed!")


@dataclass
class ExtractedTraits:
    """Data class to hold comprehensive extracted traits from a LinkedIn profile."""
    full_name: str
    linkedin_url: str
    estimated_age: Optional[str]
    education_stages: Dict[str, Any]
    career_insights: Dict[str, Any]
    company_background: Dict[str, Any]
    accelerator_and_programs: Dict[str, Any]
    education_career_alignment: Dict[str, Any]
    personal_brand: Dict[str, Any]
    research_and_academic: Dict[str, Any]
    international_experience: Dict[str, Any]
    confidence_score: Optional[str] = None

class LinkedInTraitExtractor:
    """
    Extracts specific traits from LinkedIn profiles using OpenAI's API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the trait extractor.
        
        Args:
            api_key: OpenAI API key. If None, will look for OPENAI_API_KEY environment variable.
        """
        self.client = OpenAI(
            api_key=api_key or os.getenv('OPENAI_API_KEY')
        )
        
        
    def create_extraction_prompt(self, profile_data: Dict[str, Any]) -> str:
        """Create a simplified prompt with just the profile data."""
        return json.dumps(profile_data, indent=2)
    
    def get_system_prompt(self) -> str:
        """Get the comprehensive system prompt with all extraction guidelines."""
        return """You are an expert at extracting structured information from LinkedIn profiles. 

Your task is to extract comprehensive traits from LinkedIn profile data and return ONLY a valid JSON object with the specified fields.

REQUIRED JSON FORMAT:
{
    "full_name": "Full name from profile",
    "linkedin_url": "LinkedIn URL from profile",
    "estimated_age": "A single estimated age based on graduation years (e.g. '30')",
    "education_stages": {
        "undergraduate": "University - Degree - Field - Year of Graduation (e.g., 'Stanford University - BS - Computer Science - 2016')",
        "masters": "University - Degree - Field or null - Year of Graduation or null",
        "phd": "University - Degree - Field or null - Year of Graduation or null",
        "other_education": ["Any other certifications, bootcamps, etc."]
    },
    "career_insights": {
        "avg_tenure_per_role": 2.1,
        "job_hopper": true/false,
        "total_experience_count": 5,
        "has_leadership_experience": true/false,
        "has_previous_c_suite_experience": true/false,
        "founder_experience_count": 2,
        "industry_switches": 1,
        "years_out_of_education": 8,
        "years_in_industry": 6,
        "career_summary": "CEO at StartupCo for 3 yrs; VP Product at TechCorp for 2 yrs 6 mos; Senior Engineer at BigTech for 4 yrs"
    },
    "company_background": {
        "notable_companies": ["FAANG, unicorns, top-tier companies"],
        "startup_companies": ["Early-stage/startup companies"]
    },
    "accelerator_and_programs": {
        "accelerators": ["Y Combinator, Techstars, etc."],
        "fellowship_programs": ["On Deck, EF, etc."],
        "board_positions": ["Any board positions"]
    },
    "education_career_alignment": {
        "studies_field": "Primary field of study",
        "current_field": "Current industry/role focus", 
        "pivot_description": "Description of career change if applicable"
    },
    "personal_brand": {
        "headline_keywords": ["Key terms from headline"]
    },
    "research_and_academic": {
        "academic_roles": ["Professor, Researcher, etc."],
    },
    "international_experience": {
        "countries_worked": ["List of countries/regions"]
    },
    "confidence_score": "High/Medium/Low based on data completeness and clarity"
}

EXTRACTION GUIDELINES:

1. LINKEDIN URL: Extract the linkedinUrl from the profile data exactly as provided.

2. ESTIMATED AGE: Calculate from graduation years using 2025 as the current year. Most people begin their bachelor's degree at age 18. If no start date is provided for bachelor's, assume it was a 4-year degree (graduating at age 22). If no education dates are present at all, estimate from their EARLIEST work experience, assuming they were 18 at that time. Examples: Bachelor's graduated 2018 = age 29 (2025-2018+22), Earliest work experience 2015 = age 28 (2025-2015+18). Format as a single value.

3. EDUCATION STAGES: Extract all education levels separately. Format as "University - Degree - Field - Year of Graduation". Mark missing stages as null.

4. SENIORITY LEVELS:
   - Entry: Intern, Junior, Associate, Analyst
   - Mid: Senior, Lead, Principal, Manager
   - Senior: Director, VP, Head of
   - Executive: SVP, EVP, President
   - C-Suite: CEO, CTO, COO, CMO, etc.

5. CAREER INSIGHTS: 
   - Job hopper: avg tenure < 2 years
   - Number of jobs: total number of roles they've had from profile
   - Industry switches: count distinct industries
   - Years out of education: Calculate total years since last education completion (undergraduate, masters, or PhD graduation). Use 2025 as current year. If no education dates, estimate from earliest work experience (assuming they were 18 at that time)
   - Years in industry: Calculate years of experience in their current/primary industry (excluding startup/founder roles). Use 2025 as current year
   - Career summary: Format as "Title at Company for Duration; Title at Company for Duration" (chronological order, most recent first)

6. COMPANY BACKGROUND: Spot notable companies or startup companies worked in. Quantify the number of startups they've worked in by the number of startup or 'founder' related roles in their work expereince section

7. EDUCATION-CAREER ALIGNMENT: Compare field of study with current work. Identify pivots and unusual career paths.

8. PERSONAL BRAND: Analyze headline and about section for entrepreneurial identity, thought leadership, mission-driven language.

9. RESEARCH/ACADEMIC: Look for PhD, research roles, peer reviewer positions, academic publications.

10. INTERNATIONAL EXPERIENCE: Extract countries/regions from work locations and company descriptions.

NOTABLE COMPANIES INCLUDE:
Meta, Facebook, Google, Alphabet, Apple, Amazon, Microsoft, Tesla, Stripe, Figma, Notion, OpenAI, Anthropic, Netflix, Nvidia, Intel, AMD, Oracle, IBM, Salesforce, Adobe, Uber, Lyft, Snap, Twitter, X Corp, Spotify, Airbnb, Shopify, Square, Block, PayPal, Dropbox, Slack, Cloudflare, Zoom, Palantir, Snowflake, Atlassian, Twilio, Coinbase, Reddit, SpaceX, ByteDance, TikTok, Discord, Databricks, Canva, Instacart, Klarna, Revolut, N26, Checkout.com, GitLab, Nubank, Celonis, Getir, Gorillas, Rappi, Flink, Miro, ClickUp, Postman, Loom, DeepL, Lemonade, Brex, Robinhood, Remote, Deel, Rippling, Scale AI, Samsara, Perplexity, Hugging Face, Character AI, Cohere, Runway, Adept AI, Grok, DeepMind, Quora, Linear, Glovo, Bunq, Zeco, Tink, Mollie, Bitpanda, Wefox, Ledger, Vinted, Tado, Back Market, Oviva, Sennder, Sorare, Tier Mobility, Voi, Sknups, TrueLayer, Habito, Gousto, Factorial, Railway, Jobandtalent, Paysend, Ormatek, Frichti, and many more unicorns and top-tier tech companies.

ACCELERATOR PROGRAMS INCLUDE:
Y Combinator, YC, Techstars, Antler, Entrepreneur First, EF, On Deck, Sequoia Scout, Greylock, A16Z, Andreessen Horowitz, Onstage, General Catalyst, Accel, Founders Fund, First Round, Index Ventures, Bessemer Venture Partners, Lightspeed, Neo, South Park Commons, Initialized Capital, Craft Ventures, Social Capital, 8VC, Atomic, Village Global, Pear VC, UpWest Labs, Fifty Years, Nascent, Prelude Ventures, Acrew Capital, Homebrew, Shrug Capital, F.inc, Founders Inc, Signal Fire, Boost VC, Founder Collective, Seedcamp, Station F, Backed VC, LocalGlobe, Kindred Capital, Crane Venture Partners, Balderton Capital, Hoxton Ventures, Point Nine, Speedinvest, Pentech, Tech Nation, Startup Wise Guys, European Innovation Council, Rockstart, Founders Factory, La Famille, Startupbootcamp, Bethnal Green Ventures, Future Positive Capital, Alchemist Accelerator, StartupYard, Berkeley SkyDeck, MassChallenge, and many more accelerators and incubators.


STARTUP INDICATORS: 
- Small team size mentions
- "Stealth mode" companies  
- Early employee numbers (#1-50)
- Pre-seed, seed, Series A mentions
- Equity compensation mentions
- "Building from scratch" language

LEADERSHIP INDICATORS:
- Team size management
- Budget responsibility  
- P&L ownership
- "Led team of X"
- Hiring/firing authority
- Strategic planning role

AGE CALCULATION METHODOLOGY:
- Current year: 2025
- Standard bachelor's degree: 4 years (age 18-22)
- If bachelor's graduation year provided: Age = 2025 - graduation_year + 22
- If no education dates but work experience exists: Age = 2025 - earliest_work_year + 18
- If only master's/PhD graduation: Use that graduation year + appropriate age (typically 24 for master's, 28 for PhD)
- If no dates at all: Use earliest work experience year + 18

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting. Be thorough in your analysis but conservative in your claims. IF YOU ARE EVER UNSURE, JUST PUT IN A VALUE OF "-1" FOR STRINGS, AND -1 FOR NUMBERS"""
    
    def extract_traits_from_profile(self, profile_data: Dict[str, Any], max_retries: int = 2) -> Optional[ExtractedTraits]:
        """
        Extract traits from a single profile using OpenAI API.
        
        Args:
            profile_data: Cleaned LinkedIn profile data
            max_retries: Maximum number of API call retries
            
        Returns:
            ExtractedTraits object or None if extraction fails
        """
        prompt = self.create_extraction_prompt(profile_data)
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Using gpt-4o-mini for cost efficiency
                    messages=[
                        {
                            "role": "system", 
                            "content": self.get_system_prompt()
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Low temperature for consistent extraction # basically will be more accurate to the data given. 
                    max_tokens=4000
                )
                
                # Parse the response
                content = response.choices[0].message.content.strip()
                
                # Try to extract JSON from response
                try:
                    # Remove potential markdown formatting
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.startswith('```'):
                        content = content[3:]
                    if content.endswith('```'):
                        content = content[:-3]
                    
                    traits_data = json.loads(content.strip())
                    
                    # Validate and create ExtractedTraits object
                    return ExtractedTraits(
                        full_name=traits_data.get('full_name', profile_data.get('fullName', 'Unknown')),
                        linkedin_url=traits_data.get('linkedin_url', profile_data.get('linkedinUrl', 'not found')),
                        estimated_age=traits_data.get('estimated_age'),
                        education_stages=traits_data.get('education_stages', {}),
                        career_insights=traits_data.get('career_insights', {}),
                        company_background=traits_data.get('company_background', {}),
                        accelerator_and_programs=traits_data.get('accelerator_and_programs', {}),
                        education_career_alignment=traits_data.get('education_career_alignment', {}),
                        personal_brand=traits_data.get('personal_brand', {}),
                        research_and_academic=traits_data.get('research_and_academic', {}),
                        international_experience=traits_data.get('international_experience', {}),
                        confidence_score=traits_data.get('confidence_score', 'Low')
                    )
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error on attempt {attempt + 1}: {e}")
                    print(f"Response content: {content}")
                    if attempt == max_retries - 1:
                        return None
                    continue
                    
            except Exception as e:
                print(f"API call error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
        
        return None
    
    def load_progress(self, progress_file: str) -> List[str]:
        """Load progress tracking file"""
        try:
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as file:
                    progress = json.load(file)
                return progress.get('processed_urls', [])
        except Exception as e:
            print(f"Error loading progress: {e}")
        return []

    def save_progress(self, progress_file: str, processed_urls: List[str]):
        """Save progress tracking file"""
        try:
            os.makedirs(os.path.dirname(progress_file), exist_ok=True)
            progress_data = {
                'processed_urls': processed_urls,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(progress_file, 'w', encoding='utf-8') as file:
                json.dump(progress_data, file, indent=2)
        except Exception as e:
            print(f"Error saving progress: {e}")

    def load_existing_results(self, output_file: str) -> List[ExtractedTraits]:
        """Load existing results from file if it exists"""
        try:
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as file:
                    existing_data = json.load(file)
                existing_results = [
                    ExtractedTraits(
                        full_name=item['full_name'],
                        linkedin_url=item['linkedin_url'],
                        estimated_age=item.get('estimated_age'),
                        education_stages=item.get('education_stages', {}),
                        career_insights=item.get('career_insights', {}),
                        company_background=item.get('company_background', {}),
                        accelerator_and_programs=item.get('accelerator_and_programs', {}),
                        education_career_alignment=item.get('education_career_alignment', {}),
                        personal_brand=item.get('personal_brand', {}),
                        research_and_academic=item.get('research_and_academic', {}),
                        international_experience=item.get('international_experience', {}),
                        confidence_score=item.get('confidence_score', 'Low')
                    ) for item in existing_data
                ]
                print(f"Loaded {len(existing_results)} existing results from {output_file}")
                return existing_results
        except Exception as e:
            print(f"Error loading existing results: {e}")
        return []

    def append_results_to_file(self, new_results: List[ExtractedTraits], output_file: str) -> int:
        """Append new results to existing file"""
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            existing_results = self.load_existing_results(output_file)
            existing_results.extend(new_results)
            self.save_results(existing_results, output_file)
            return len(existing_results)
        except Exception as e:
            print(f"Error appending results: {e}")
            return 0

    def get_remaining_profiles(self, all_profiles: List[Dict[str, Any]], processed_urls: List[str]) -> List[Dict[str, Any]]:
        """Get profiles that haven't been processed yet"""
        processed_set = set(processed_urls)
        remaining = [profile for profile in all_profiles 
                    if profile.get('linkedinUrl', '').strip() 
                    and profile.get('linkedinUrl', '').strip() not in processed_set]
        return remaining

    def extract_traits_from_profiles(
        self, 
        profiles: List[Dict[str, Any]], 
        delay_between_calls: float = 1.0,
        max_profiles: int = -1,
        force_reextraction: bool = False,
        progress_file: str = None,
        output_file: str = None
    ) -> List[ExtractedTraits]:
        """
        Extract traits from multiple profiles with rate limiting and progress tracking.
        
        Args:
            profiles: List of cleaned LinkedIn profile data
            delay_between_calls: Delay in seconds between API calls
            max_profiles: Maximum number of profiles to process in this session. -1 for all.
            force_reextraction: If True, re-extract all profiles even if already processed.
            progress_file: File to save progress tracking data
            output_file: File to save final results
            
        Returns:
            List of ExtractedTraits objects
        """
        # Set up progress tracking
        if progress_file is None and output_file:
            progress_file = output_file.replace('.json', '_progress.json')
        
        # Load existing progress
        processed_urls = self.load_progress(progress_file) if progress_file else []
        
        # Load existing results if they exist
        existing_results = []
        if output_file and os.path.exists(output_file) and not force_reextraction:
            existing_results = self.load_existing_results(output_file)
        
        # Get remaining profiles to process
        remaining_profiles = self.get_remaining_profiles(profiles, processed_urls)
        
        if not remaining_profiles and not force_reextraction:
            print("✅ All profiles have already been processed!")
            return existing_results
        
        print(f"📊 Progress Status:")
        print(f"  Total profiles: {len(profiles)}")
        print(f"  Already processed: {len(processed_urls)}")
        print(f"  Remaining to process: {len(remaining_profiles)}")
        
        if len(processed_urls) > 0 and not force_reextraction:
            print(f"🔄 RESUMING from {len(processed_urls)} completed profiles")
        
        # Track new results from this session
        new_results = []
        profiles_processed_this_session = 0
        
        # Determine how many profiles to process in this session
        if max_profiles != -1:
            remaining_profiles = remaining_profiles[:max_profiles]
        
        print(f"Starting extraction session. Target: {len(remaining_profiles)} profiles")
        
        for i, profile in enumerate(remaining_profiles):
            profile_url = profile.get('linkedinUrl', '').strip()
            
            # Skip if no URL
            if not profile_url:
                print(f"Skipping profile {i + 1}: No LinkedIn URL found")
                continue
            
            print(f"Processing profile {i + 1}/{len(remaining_profiles)}: {profile.get('fullName', 'Unknown')}")
            
            traits = self.extract_traits_from_profile(profile)
            if traits:
                new_results.append(traits)
                processed_urls.append(profile_url)
                profiles_processed_this_session += 1
                print(f"✓ Successfully extracted traits")
                
                # Save progress incrementally
                if progress_file:
                    self.save_progress(progress_file, processed_urls)
                
                # Save results incrementally
                if output_file:
                    total_saved = self.append_results_to_file([traits], output_file)
                    print(f"Progress saved: {total_saved} total profiles processed")
            else:
                print(f"✗ Failed to extract traits")
            
            # Rate limiting
            if i < len(remaining_profiles) - 1:
                time.sleep(delay_between_calls)
        
        # Final summary
        all_results = existing_results + new_results
        
        print(f"\n=== SESSION SUMMARY ===")
        print(f"New profiles processed this session: {len(new_results)}")
        print(f"Total profiles in results file: {len(all_results)}")
        print(f"Remaining unprocessed profiles: {len(self.get_remaining_profiles(profiles, processed_urls))}")
        
        return all_results
    
    def save_results(self, results: List[ExtractedTraits], output_file: str):
        """Save comprehensive extraction results to JSON file."""
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            output_data = []
            
            for traits in results:
                output_data.append({
                    'full_name': traits.full_name,
                    'linkedin_url': traits.linkedin_url,
                    'estimated_age': traits.estimated_age,
                    'education_stages': traits.education_stages,
                    'career_insights': traits.career_insights,
                    'company_background': traits.company_background,
                    'accelerator_and_programs': traits.accelerator_and_programs,
                    'education_career_alignment': traits.education_career_alignment,
                    'personal_brand': traits.personal_brand,
                    'research_and_academic': traits.research_and_academic,
                    'international_experience': traits.international_experience,
                    'confidence_score': traits.confidence_score
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"Results saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")

    def check_progress(self, input_profiles_file: str, output_file: str) -> Dict[str, Any]:
        """
        Check extraction progress and return summary statistics.
        
        Args:
            input_profiles_file: Path to the cleaned profiles JSON file
            output_file: Path to the results file
            
        Returns:
            Dictionary with progress statistics
        """
        # Load input profiles
        with open(input_profiles_file, 'r', encoding='utf-8') as f:
            all_profiles = json.load(f)
        
        # Load progress tracking file
        progress_file = output_file.replace('.json', '_progress.json')
        processed_urls = self.load_progress(progress_file)
        
        # Load existing results if they exist
        existing_results = self.load_existing_results(output_file)
        
        # Calculate statistics
        total_profiles = len(all_profiles)
        profiles_with_urls = [p for p in all_profiles if p.get('linkedinUrl', '').strip()]
        valid_profiles = len(profiles_with_urls)
        processed_count = len(processed_urls)
        remaining_count = valid_profiles - processed_count
        
        progress_stats = {
            'total_profiles': total_profiles,
            'valid_profiles_with_urls': valid_profiles,
            'processed_profiles': processed_count,
            'remaining_profiles': remaining_count,
            'completion_percentage': round((processed_count / valid_profiles) * 100, 1) if valid_profiles > 0 else 0,
            'processed_urls': processed_urls,
            'results_file_exists': os.path.exists(output_file),
            'progress_file_exists': os.path.exists(progress_file),
            'existing_results_count': len(existing_results)
        }
        
        print(f"\n=== EXTRACTION PROGRESS ===")
        print(f"Total profiles in file: {total_profiles}")
        print(f"Profiles with valid URLs: {valid_profiles}")
        print(f"Already processed: {processed_count}")
        print(f"Remaining to process: {remaining_count}")
        print(f"Completion: {progress_stats['completion_percentage']}%")
        print(f"Results file exists: {progress_stats['results_file_exists']}")
        print(f"Progress file exists: {progress_stats['progress_file_exists']}")
        print(f"Existing results count: {progress_stats['existing_results_count']}")
        
        return progress_stats


if __name__ == "__main__":
    # Uncomment one of the following options:
    
    # Option 1: Run the main extraction
    main()
    
    # Option 2: Demonstrate progress tracking
    # demonstrate_progress_tracking()
    
    # Option 3: Just check progress without processing
    # extractor = LinkedInTraitExtractor()
    # extractor.check_progress(
    #     'cleaned-profile-data/S25Top100cleaned_linkedin_data.json',
    #     'final-trait-extractions/S25Top100_comprehensive_traits.json'
    # ) 


''' 
Notable compaies and stuff - can be reused later

 self.faang_companies = {
            'facebook', 'meta', 'apple', 'amazon', 'netflix', 'google', 'alphabet',
            'microsoft', 'tesla', 'nvidia', 'intel', 'amd', 'oracle', 'ibm',
            'salesforce', 'adobe', 'uber', 'lyft', 'snap', 'twitter', 'x corp', 'spotify',
            'airbnb', 'shopify', 'square', 'block', 'paypal', 'dropbox', 'slack', 'cloudflare',
            'zoom', 'palantir', 'snowflake', 'atlassian', 'twilio', 'coinbase', 'reddit'
        }

        self.unicorn_startups = {
            # Global
            'stripe', 'spacex', 'bytedance', 'tiktok', 'figma', 'notion', 'discord',
            'databricks', 'canva', 'instacart', 'klarna', 'revolut', 'nubank', 'checkout.com',
            'gitlab', 'celonis', 'getir', 'gorillas', 'rappi', 'flink', 'miro', 'clickup',
            'postman', 'loom', 'deepl', 'lemonade', 'brex', 'robinhood', 'remote', 'deal',
            'rippling', 'scale ai', 'samsara', 'openai', 'anthropic', 'perplexity', 'hugging face',
            'character ai', 'cohere', 'runway', 'adept ai', 'grok', 'deepmind', 'quora', 'linear',

            # Europe (focus)
            'revolut', 'klarna', 'getir', 'gorillas', 'flink', 'glovo', 'bunq', 'n26', 'zeco', 'tink',
            'mollie', 'bitpanda', 'wefox', 'ledger', 'vinted', 'tado', 'back market', 'oviva',
            'sennder', 'sorare', 'tier mobility', 'voi', 'sknups', 'truelayer', 'habito',
            'gousto', 'factorial', 'railway', 'jobandtalent', 'paysend', 'ormatek', 'frichti'
        }

        self.accelerator_programs = {
            # Global + US-focused
            'y combinator', 'yc', 'techstars', 'antler', 'entrepreneur first', 'ef',
            'on deck', 'sequoia scout', 'greylock', 'a16z', 'andreessen horowitz',
            'general catalyst', 'accel', 'founders fund', 'first round', 'index ventures',
            'bessemer venture partners', 'lightspeed', 'neo', 'south park commons',
            'initialized capital', 'craft ventures', 'social capital', '8vc', 'atomic',
            'village global', 'pear vc', 'upwest labs', 'fifty years', 'nascent',
            'prelude ventures', 'acrew capital', 'homebrew', 'shrug capital', 'f.inc', 'founders inc',
            'signal fire', 'boost vc', 'founder collective',

            # Europe-focused
            'seedcamp', 'station f', 'backed vc', 'localglobe', 'kindred capital',
            'crane venture partners', 'balderton capital', 'hoxton ventures', 'point nine',
            'speedinvest', 'pentech', 'entrepreneur first', 'tech nation', 'startup wise guys',
            'european innovation council', 'rockstart', 'founders factory', 'la famille',
            'startupbootcamp', 'bethnal green ventures', 'future positive capital',
            'alchemist accelerator', 'startupyard', 'berkeley skydeck', 'masschallenge'
        }


'''