#!/usr/bin/python3

"""
Test script for AllSky Camera Image Processing
============================================

Simplified version of process.py for testing image processing functions.
Processes a single FITS file with basic enhancements and saves as JPG.
"""

import lib
import os
from astropy.io import fits
from PIL import Image, ImageEnhance, ImageOps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
INPUT_FITS = "2024-12-07_20-05.fit"  # Replace with your test file name
INPUT_FITS = "2024-12-07_23-00.fit"  # Replace with your test file name
FITS_DIR = "/fits"
OUTPUT_DIR = "/snap"

def process_fits():
    """Process single FITS file with basic enhancements."""
    
    # Load web config (same as original script)
    web = lib.getWebConfig()
    
    # Construct full input path
    input_path = os.path.join(FITS_DIR, INPUT_FITS)
    
    logger.info(f"Processing file: {input_path}")
    
    try:
        # Open FITS file
        with fits.open(input_path) as fit:
            hdu = fit[0]
            
            # Convert FITS data to PIL Image
            if 'ccd' in web and 'bits' in web['ccd']:
                data = hdu.data if web['ccd']['bits'] == 8 else (hdu.data / 256).astype('uint8')
            else:
                data = (hdu.data / 256).astype('uint8')
            
            img = Image.fromarray(data)
            
            # Apply gamma correction if configured
            if 'gamma' in web['processing']:
                gamma_value = float(web['processing']['gamma'])
                logger.info(f'Applying gamma correction: {gamma_value}')
                img = ImageEnhance.Brightness(img).enhance(gamma_value)
            
            # Apply auto contrast if configured
            if 'autoContrast' in web['processing']:
                cutoff = float(web['processing']['autoContrast'])
                logger.info(f'Applying auto contrast with cutoff: {cutoff}')
                img = ImageOps.autocontrast(img, cutoff=cutoff)
            
            # Save output
            output_filename = os.path.splitext(INPUT_FITS)[0] + '.jpg'
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            img.save(output_path)
            logger.info(f'Saved processed image to: {output_path}')
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise

if __name__ == "__main__":
    process_fits() 