import numpy as np
from PIL import Image
import os

def create_test_image(filepath="test_sarmae_input.png"):
    # Generate a 224x224 grayscale image with some speckle noise (similar to SAR)
    np.random.seed(42)
    base = np.ones((224, 224)) * 100
    noise = np.random.normal(0, 40, (224, 224))
    img_data = np.clip(base + noise, 0, 255).astype(np.uint8)

    # Draw a bright artifact in the middle (e.g. a ship or building)
    img_data[100:120, 110:115] = 255
    img_data[102:118, 108:117] = 200

    img = Image.fromarray(img_data, mode='L')
    img.save(filepath)
    print(f"Test image successfully created at {os.path.abspath(filepath)}")

if __name__ == "__main__":
    create_test_image()
