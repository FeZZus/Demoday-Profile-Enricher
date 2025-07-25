#!/usr/bin/env python3
"""
Main entry point for the Airtable LinkedIn URL Extractor API

This file imports the FastAPI app from airtable_api.py to make it available
for uvicorn to run with: python -m uvicorn main:app
"""

from airtable_api import app

# Export the app for uvicorn
__all__ = ["app"] 