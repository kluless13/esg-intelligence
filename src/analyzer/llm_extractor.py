"""
ESG data extraction using Claude API.

This module uses Anthropic's Claude to extract structured ESG metrics
from sustainability and annual reports.
"""

import json
import logging
from typing import Dict, Optional
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System prompt for Claude
SYSTEM_PROMPT = """You are an ESG data extraction specialist analyzing Australian company sustainability reports.
Extract specific metrics and commitments. Be precise - only extract data explicitly stated.
If data is not found, use null. Pay attention to the financial year context.

Return ONLY valid JSON with no additional text or formatting."""

# Extraction prompt template
EXTRACTION_PROMPT_TEMPLATE = """Company: {company_name}
Financial Year: {financial_year}
Document Type: {document_type}

Extract ESG metrics from this sustainability/annual report text.
Return ONLY a valid JSON object with these fields:

{{
    "data_year": <int, the financial year this data is for, e.g. 2024>,

    "scope1_emissions": <number in tonnes CO2e or null>,
    "scope2_emissions": <number in tonnes CO2e, market-based preferred, or null>,
    "scope3_emissions": <number in tonnes CO2e or null>,
    "total_emissions": <number or null>,
    "emissions_baseline_year": <int or null>,

    "net_zero_target_year": <int or null>,
    "emissions_reduction_target_pct": <number 0-100 or null>,
    "emissions_reduction_target_year": <int or null>,

    "renewable_energy_pct_current": <number 0-100 or null>,
    "renewable_energy_target_pct": <number 0-100 or null>,
    "renewable_energy_target_year": <int or null>,
    "energy_consumption_mwh": <number or null>,

    "sbti_status": <"committed"|"validated"|"targets_set"|"none"|null>,
    "re100_member": <true|false|null>,
    "tcfd_aligned": <true|false|null>,
    "climate_active_certified": <true|false|null>,

    "has_ppa": <true|false|null>,
    "ppa_details": <string description or null>,
    "renewable_procurement_mentioned": <true|false|null>,

    "confidence_score": <0.0-1.0, how confident you are in this extraction>,
    "extraction_notes": <string with any caveats or important context>
}}

Document text (may be truncated):
{document_text}"""


def truncate_document(text: str, max_chars: int = 100000) -> str:
    """
    Intelligently truncate long documents to fit in context window.

    Strategy:
    1. If text < max_chars, return as-is
    2. If text > max_chars:
       - Keep first 50k chars (summary and key metrics)
       - Search for sections with ESG keywords and include them
       - Keep last 10k chars (often has data tables)

    Args:
        text: Full document text
        max_chars: Maximum characters to return

    Returns:
        Truncated text with most relevant content
    """
    if len(text) <= max_chars:
        return text

    logger.info(f"Truncating document from {len(text):,} to ~{max_chars:,} chars")

    # Keep first 50k chars
    start_text = text[:50000]

    # Keep last 10k chars (often has tables)
    end_text = text[-10000:]

    # Search for ESG-relevant sections in the middle
    keywords = ['emissions', 'renewable', 'target', 'scope 1', 'scope 2', 'scope 3',
                'climate', 'carbon', 'energy', 'sustainability', 'esg']

    middle_sections = []
    remaining_chars = max_chars - len(start_text) - len(end_text)

    if remaining_chars > 1000:
        # Find paragraphs with ESG keywords
        middle_text = text[50000:-10000]
        paragraphs = middle_text.split('\n\n')

        for para in paragraphs:
            if any(keyword in para.lower() for keyword in keywords):
                if len('\n\n'.join(middle_sections + [para])) < remaining_chars:
                    middle_sections.append(para)

    # Combine sections
    truncated = start_text
    if middle_sections:
        truncated += "\n\n[... middle sections with ESG content ...]\n\n"
        truncated += '\n\n'.join(middle_sections)
    truncated += "\n\n[... end of document ...]\n\n"
    truncated += end_text

    return truncated


def extract_esg_data(
    company_name: str,
    financial_year: str,
    document_type: str,
    document_text: str,
    model: str = "claude-sonnet-4-20250514"
) -> Dict:
    """
    Extract ESG data from document text using Claude API.

    Args:
        company_name: Company name
        financial_year: Financial year (e.g., "FY2024")
        document_type: Type of document (e.g., "annual_report")
        document_text: Full document text
        model: Claude model to use

    Returns:
        Dict with:
            - extracted_data: Dict of ESG metrics
            - raw_response: Raw LLM response text
            - success: bool
            - error: str if failed
            - tokens_used: Dict with input/output token counts
    """
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_key_here":
        return {
            "success": False,
            "error": "Anthropic API key not configured. Please add your API key to .env file.",
            "extracted_data": None,
            "raw_response": None,
            "tokens_used": {"input": 0, "output": 0}
        }

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Truncate document if needed
        truncated_text = truncate_document(document_text)

        # Format the prompt
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            company_name=company_name,
            financial_year=financial_year,
            document_type=document_type,
            document_text=truncated_text
        )

        logger.info(f"Calling Claude API for {company_name} {financial_year}")
        logger.info(f"Input text length: {len(truncated_text):,} chars")

        # Call Claude API
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract response text
        response_text = response.content[0].text

        # Parse JSON response
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}")

            # Try to extract JSON from response if it has extra text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
            else:
                raise

        # Get token usage
        tokens_used = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }

        logger.info(f"✓ Extraction successful. Tokens: {tokens_used['input']:,} in, {tokens_used['output']:,} out")

        return {
            "success": True,
            "error": None,
            "extracted_data": extracted_data,
            "raw_response": response_text,
            "tokens_used": tokens_used
        }

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_data": None,
            "raw_response": None,
            "tokens_used": {"input": 0, "output": 0}
        }


def estimate_cost(num_documents: int, avg_chars_per_doc: int = 30000) -> Dict:
    """
    Estimate cost of processing documents with Claude.

    Claude Sonnet pricing (as of 2024):
    - Input: $3 per million tokens
    - Output: $15 per million tokens

    Rough estimate: 1 token ≈ 4 characters

    Args:
        num_documents: Number of documents to process
        avg_chars_per_doc: Average characters per document

    Returns:
        Dict with estimated tokens and cost
    """
    # Estimate tokens (chars / 4)
    chars_per_doc = min(avg_chars_per_doc, 100000)  # Max after truncation
    prompt_chars = chars_per_doc + 500  # Add prompt overhead

    input_tokens_per_doc = prompt_chars // 4
    output_tokens_per_doc = 400  # Estimated JSON response

    total_input_tokens = input_tokens_per_doc * num_documents
    total_output_tokens = output_tokens_per_doc * num_documents

    # Calculate cost
    input_cost = (total_input_tokens / 1_000_000) * 3.0
    output_cost = (total_output_tokens / 1_000_000) * 15.0
    total_cost = input_cost + output_cost

    return {
        "num_documents": num_documents,
        "estimated_input_tokens": total_input_tokens,
        "estimated_output_tokens": total_output_tokens,
        "estimated_total_tokens": total_input_tokens + total_output_tokens,
        "estimated_cost_usd": total_cost,
        "input_cost": input_cost,
        "output_cost": output_cost
    }


if __name__ == "__main__":
    # Test the extraction
    test_text = """
    Xero Limited FY2024 Annual Report

    Climate and Emissions

    Our total Scope 1 and 2 emissions for FY2024 were 619 tCO2e, a decrease from
    the previous year. We have set science-based targets aligned with limiting
    global warming to 1.5°C.

    Targets:
    - Net zero by 2040
    - 60% reduction in Scope 1 and 2 emissions by 2034 (baseline FY2022)
    - We are committed to the Science Based Targets initiative (SBTi)
    - TCFD aligned reporting since 2023

    Renewable Energy:
    We currently source 45% of our energy from renewable sources and aim to
    reach 100% renewable energy by 2030.

    Energy consumption: 3,450 MWh
    """

    result = extract_esg_data(
        company_name="Xero Limited",
        financial_year="FY2024",
        document_type="annual_report",
        document_text=test_text
    )

    if result['success']:
        print("✓ Extraction successful!")
        print(json.dumps(result['extracted_data'], indent=2))
        print(f"\nTokens used: {result['tokens_used']}")
    else:
        print(f"✗ Error: {result['error']}")
