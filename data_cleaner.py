'''
Step 3:
 - After extracting apify data, we clean it up just to care about the things we need
 - Change the input json file name
'''

import json
import re
from typing import Dict, List, Any

class LinkedInDataProcessor:
    """
    Processes LinkedIn profile data to remove irrelevant sections and clean up
    the data for trait extraction via OpenAI API.
    """
    
    def __init__(self):
        # Fields to completely remove
        # Just aint used anymore -- > just a list of other stuff that cna be included if wanted
        self.fields_to_remove = {
            
            'profilePic', 'profilePicHighQuality', 'profilePicAllDimensions',
            'interests', 'languages', 'recommendations', 'updates',
            'connections', 'followers', 'email', 'mobileNumber', 
            'addressWithCountry', 'addressWithoutCountry',
            'publicIdentifier', 'openConnection', 'urn', 
            'licenseAndCertificates', 'honorsAndAwards', 'patents',
            'courses', 'testScores', 'organizations', 'volunteerCauses',
            'verifications', 'promos', 'highlights', 'publications'
            'companyName', 
    'companyIndustry',
    'currentJobDuration'
        }
        
        # Media/link patterns to remove from text fields
        self.media_patterns = [
            # s? is optional s, [^\s]+ --> + means any number, ^ means not, \s is whitespace. i.e. followed by any number of non-whitespace stuff to match the remaining url 
            r'https?://[^\s]+',  # URLs
            r'urn:li:[^\s]+',    # LinkedIn URNs
            r'"type":\s*"mediaComponent"[^}]*}',  # Media components
            r'"thumbnail":\s*"[^"]*"',  # Thumbnails
        ]
    
    def clean_text_content(self, text: str) -> str:
        """Remove URLs and media links from text content."""
        # if its just all BS, then return as it is
        if not isinstance(text, str):
            return text


        cleaned = text
        # iterate through the patterns and for any matches in cleaned, replace it with empty space
        for pattern in self.media_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def process_experience_item(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and process a single experience item."""
        cleaned = {}
        
        # Keep essential fields
        if 'title' in experience:
            cleaned['title'] = self.clean_text_content(experience['title'])
        if 'subtitle' in experience:
            cleaned['subtitle'] = self.clean_text_content(experience['subtitle'])
        if 'caption' in experience:
            cleaned['caption'] = experience['caption']
        if 'metadata' in experience:
            cleaned['metadata'] = experience['metadata']
        
        # Process subComponents to extract descriptions while removing media
        # sub componensts in the expereince section are each particular expereince
        
        # Experience 
            # List of sub expereicnes for each thing i.e. Startup 1, Startup 2, Startup 3
                # Each experience has a description key with a dictionary
                    # Within that dictionary theres a type key, a a text key. the type key tells us if theres a text components. the text key gives us the actual description 
        if 'subComponents' in experience:
            descriptions = []
            for sub in experience['subComponents']:
                if 'description' in sub:
                    # each sub comp has a description, 
                    for desc_item in sub['description']:
                        if isinstance(desc_item, dict) and desc_item.get('type') == 'textComponent':
                            text = desc_item.get('text', '')
                            if text:
                                descriptions.append(self.clean_text_content(text))
            
            # If after all the checks theres the relevant bit, then just add it to the cleaned section
            if descriptions:
                cleaned['description'] = ' '.join(descriptions)
        
        '''
        You pass in a whole expereince which is a dictionary. 
        If theres a brekadown, then go through the sub components. 
        Eahc sub component is a dictionary
        Extract the title, and description from them if theres that data provided. 
        Each particular roel appeneded into roles, and them moved into the main expeir 

        '''



        # Handle breakdown experiences (multiple roles at same company)
        # Breakdown is a boolean telling us if theres a brekadown or not 
        if experience.get('breakdown') and 'subComponents' in experience:
            cleaned['breakdown'] = True
            roles = []
            # again each experience section has sub sections 
            for sub in experience['subComponents']:
                # Sub is each sub component 
                if 'title' in sub:
                    role = {
                        'title': self.clean_text_content(sub['title']),
                        'caption': sub.get('caption', ''),
                        'metadata': sub.get('metadata', '')
                    }
                    if 'description' in sub:
                        descriptions = []
                        
                        # description is a list of dicitionaries. can be many dictionaries within the description
                        for desc_item in sub['description']:

                            # Descirption has keys 'type' (i.e. could be a text component) and 'text' (the actual text)
                            if isinstance(desc_item, dict) and desc_item.get('type') == 'textComponent':
                                text = desc_item.get('text', '')
                                if text:
                                    descriptions.append(self.clean_text_content(text))
                        if descriptions:
                            role['description'] = ' '.join(descriptions)
                    roles.append(role)
            cleaned['roles'] = roles
        
        return cleaned
    
    def process_education_item(self, education: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and process a single education item.
        
        Education items are list of dictionaries, each one is passed into this function
        
        """

        cleaned = {}
        
        # Keep essential fields
        for field in ['title', 'subtitle', 'caption']:
            # loop to create cleaned dictionary with 3 keys
            if field in education:
                cleaned[field] = self.clean_text_content(education[field])


        return cleaned
    
    def process_single_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single LinkedIn profile.
        
        Gathers all meaningful data. 

        """
        cleaned_profile = {}
        
        # Keep basic identifying information
        for field in ['fullName', 'headline']:
            if field in profile:
                cleaned_profile[field] = self.clean_text_content(profile[field])
        
        if 'linkedinUrl' in profile:
            cleaned_profile['linkedinUrl'] = profile['linkedinUrl']

        # Clean about section
        if 'about' in profile:
            cleaned_profile['about'] = self.clean_text_content(profile['about'])
        
        # Process experiences
        if 'experiences' in profile:
            cleaned_experiences = []
            for exp in profile['experiences']:
                cleaned_exp = self.process_experience_item(exp)
                if cleaned_exp:  # Only add if there's meaningful content
                    cleaned_experiences.append(cleaned_exp)
            cleaned_profile['experiences'] = cleaned_experiences
        
        # Process education
        if 'educations' in profile:
            cleaned_educations = []
            for edu in profile['educations']:
                cleaned_edu = self.process_education_item(edu)
                if cleaned_edu:
                    cleaned_educations.append(cleaned_edu)
            cleaned_profile['educations'] = cleaned_educations
        
        # Keep skills but clean them
        if 'skills' in profile:
            cleaned_skills = []
            for skill in profile['skills']:
                if 'title' in skill:
                    cleaned_skills.append(skill['title'])
            cleaned_profile['skills'] = cleaned_skills
        
        # Keep company information from current job
        for field in ['jobTitle', 'companyName', 'companyIndustry', 'currentJobDuration']:
            if field in profile:
                cleaned_profile[field] = profile[field]
        
        return cleaned_profile
    
    def process_profiles(self, profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of LinkedIn profiles."""
        return [self.process_single_profile(profile) for profile in profiles]
    
    def load_and_process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load JSON file and process all profiles."""
        with open(file_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        
        return self.process_profiles(profiles)

def main():
    """Example usage of the LinkedInDataProcessor."""
    processor = LinkedInDataProcessor()
    
    # Process the file
    filename = f'apify-profile-data\\S25Top100linkedin_profile_data.json'
    decision = str(input(f"Cleaning up file: {filename} \n y/n"))

    if decision == "y":
        cleaned_profiles = processor.load_and_process_file(filename)

        filename = f'cleaned-profile-data\\S25Top100cleaned_linkedin_data.json'
        # Save cleaned data
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cleaned_profiles, f, indent=2, ensure_ascii=False)
        
        print(f"Processed {len(cleaned_profiles)} profiles")
        print("Cleaned data saved to:", filename)

if __name__ == "__main__":
    main() 