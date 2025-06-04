"""
Utility functions for the lecture notes API
"""
import os
import logging
import tempfile
import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)

async def download_file(url, suffix):
    """
    Download a file from a URL and save it to a temporary file
    Returns the path to the temporary file
    """
    try:
        logger.info(f"Downloading file from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name
            logger.info(f"File saved at: {temp_path}")
            return temp_path
    except requests.RequestException as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download file: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
