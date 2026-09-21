"""Test the GeoChat bounding box visualizer locally."""

import os
from PIL import Image
import numpy as np

from app.models.geochat.parser import annotate_image

def main():
    print("Generating a test image (256x256)...")
    # Create a simple grey image
    img_array = np.full((256, 256, 3), 128, dtype=np.uint8)
    img = Image.fromarray(img_array)
    
    test_img_path = "scratch/test_bbox_input.png"
    os.makedirs("scratch", exist_ok=True)
    img.save(test_img_path)
    
    # Simulate GeoChat text containing coordinates (0-100 scale)
    # Box 1: [ymin=25, xmin=25, ymax=75, xmax=75] -> Center box covering 50% width/height
    # Box 2: [ymin=0, xmin=80, ymax=20, xmax=100] -> Top right corner
    mock_response = "The main factory is located at [25, 25, 75, 75]. There is also a small road at [0, 80, 20, 100]."
    
    print(f"Mock GeoChat Response: '{mock_response}'")
    
    # Run the parser
    out_path = annotate_image(test_img_path, mock_response)
    
    if out_path:
        print(f"SUCCESS! Annotated image saved to: {out_path}")
        print("Please check the image to verify the boxes are drawn correctly.")
    else:
        print("FAILED to parse boxes or draw image.")


if __name__ == "__main__":
    main()
