# LinkedIn Profile Enricher

A Python tool that processes LinkedIn profile data to extract key professional traits using OpenAI's API. This tool cleans raw LinkedIn profile data and extracts structured information about education, work experience, startup involvement, and notable career achievements.

## Features

- **Data Cleaning**: Removes irrelevant sections like profile pictures, interests, recommendations, and media links
- **Trait Extraction**: Uses OpenAI's API to extract structured professional information
- **Rate Limiting**: Built-in API call throttling to respect OpenAI's rate limits
- **Batch Processing**: Process multiple profiles efficiently
- **Confidence Scoring**: Provides confidence levels for extracted data
- **Detailed Reporting**: Summary statistics and detailed results

## Extracted Traits

The tool extracts the following information from each LinkedIn profile:

- **University + Degree**: Educational background
- **Most Recent 2 Roles**: Job titles and companies
- **Startup Experience**: Whether the person has startup experience (Yes/No)
- **Founder Status**: Whether the person was previously a founder (Yes/No)
- **Notable Companies**: FAANG, unicorns, or top-tier companies
- **Accelerators/Programs**: Y Combinator, Techstars, On Deck, etc.

## Installation

1. **Clone or download the project files**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up OpenAI API Key**:
   - Get an API key from [OpenAI](https://platform.openai.com/api-keys)
   - Option 1: Set environment variable
     ```bash
     export OPENAI_API_KEY="your-api-key-here"
     ```
   - Option 2: Pass directly via command line (see usage below)

## Usage

### Basic Usage

```bash
python main.py --input dataset_Linkedin-Profile-Scraper_2025-07-16_23-43-11-086.json
```

### Advanced Usage

```bash
# Specify output file and API key
python main.py --input dataset.json --output results.json --api-key sk-your-key-here

# Process with custom rate limiting (2 second delays)
python main.py --input dataset.json --delay 2.0

# Process only first 5 profiles (for testing)
python main.py --input dataset.json --max-profiles 5

# Save cleaned data and enable verbose output
python main.py --input dataset.json --save-cleaned --verbose
```

### Command Line Arguments

- `--input, -i`: Path to input LinkedIn dataset JSON file (required)
- `--output, -o`: Path to output file (default: extracted_traits.json)
- `--api-key`: OpenAI API key (or use OPENAI_API_KEY env var)
- `--delay`: Delay between API calls in seconds (default: 1.0)
- `--save-cleaned`: Save cleaned profile data to file
- `--max-profiles`: Limit number of profiles to process
- `--verbose, -v`: Enable detailed output

## File Structure

```
linkedin-profile-enricher/
├── main.py                    # Main entry point
├── data_processor.py          # Data cleaning and processing
├── trait_extractor.py         # OpenAI API integration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── dataset_*.json            # Input LinkedIn data
```

## Input Format

The tool expects a JSON file containing an array of LinkedIn profile objects. Each profile should have the following structure:

```json
[
  {
    "firstName": "John",
    "lastName": "Doe",
    "fullName": "John Doe",
    "headline": "Software Engineer at Company",
    "about": "Bio text...",
    "experiences": [...],
    "educations": [...],
    "skills": [...],
    ...
  }
]
```

## Output Format

The tool generates a JSON file with extracted traits:

```json
[
  {
    "full_name": "John Doe",
    "university_degree": "Stanford University - BS Computer Science",
    "recent_roles": [
      {"title": "Senior Software Engineer", "company": "Tech Corp"},
      {"title": "Software Engineer", "company": "StartupXYZ"}
    ],
    "has_startup_experience": true,
    "was_founder": false,
    "notable_companies": ["Google", "Meta"],
    "accelerators_programs": ["Y Combinator"],
    "confidence_score": "High"
  }
]
```

## Data Processing

### What Gets Removed

The data processor removes the following to reduce noise:
- Profile pictures and media URLs
- Interests and languages sections  
- Recommendations and endorsements
- LinkedIn post updates
- Contact information (email, phone)
- Address information
- Media components in experience descriptions
- Various metadata and IDs

### What Gets Kept

The following information is preserved for trait extraction:
- Basic profile information (name, headline)
- About/bio section
- Work experiences with titles, companies, and descriptions
- Education history
- Skills list
- Current job information

## API Usage and Costs

- Uses OpenAI's `gpt-4o-mini` model for cost efficiency
- Typical cost: ~$0.01-0.02 per profile
- Built-in rate limiting (1 second delay by default)
- Retry logic with exponential backoff
- Processes 2 profiles from your dataset = ~$0.02-0.04

## Error Handling

The tool includes robust error handling:
- API key validation
- JSON parsing errors
- Rate limit handling
- Network error recovery
- Malformed response handling

## Example Processing Flow

1. **Load Data**: Read LinkedIn profile JSON file
2. **Clean Data**: Remove irrelevant sections and media links
3. **Extract Traits**: Use OpenAI API to extract structured information
4. **Save Results**: Output clean JSON with extracted traits
5. **Generate Summary**: Display processing statistics

## Limitations

- Requires OpenAI API access (paid service)
- Quality depends on completeness of input LinkedIn data
- Rate limited by OpenAI API constraints
- Results depend on AI model performance

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure OpenAI API key is set correctly
2. **Rate Limiting**: Increase `--delay` if hitting rate limits
3. **JSON Errors**: Check input file format
4. **Memory Issues**: Process in smaller batches using `--max-profiles`

### Debug Mode

Enable verbose output for debugging:
```bash
python main.py --input dataset.json --verbose
```

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the tool.

## License

This project is open source. Use responsibly and in accordance with OpenAI's usage policies. 