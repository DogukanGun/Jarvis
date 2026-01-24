#!/usr/bin/env python3
"""
Simple script to generate an image and save it in the test folder.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.graphs.image_prompt_graph.nodes import generate_node
from app.graphs.image_prompt_graph.state import ImagePromptGraphState
from app.schemas.messages import TaskType, OutputFormat
from PIL import Image
import shutil


def generate_and_save_image():
    """Generate an image and save it to the test folder."""
    
    print("Generating image and saving to test folder...")
    
    # Create test state
    test_state: ImagePromptGraphState = {
        "request": {
            "job_id": "saved-test-image",
            "task": TaskType.IMAGE_FROM_PROMPT,
            "prompt": "a beautiful landscape with mountains and trees during daytime",
            "output": {
                "format": OutputFormat.PNG,
                "width": 512,  # Higher resolution
                "height": 512
            },
            "meta": {
                "guidance_scale": 7.5,
                "num_inference_steps": 20,  # Good balance of quality/speed
                "seed": 42
            }
        },
        "job_id": "saved-test-image"
    }
    
    try:
        # Run the generate node
        result = generate_node(test_state)
        
        if result["generation_success"] and result["output_path"]:
            # Source path (temporary file)
            temp_path = result["output_path"]
            
            # Destination path (in test folder)
            test_folder = Path(__file__).parent
            output_filename = "generated_image_test.png"
            output_path = test_folder / output_filename
            
            # Copy the generated image to the test folder
            shutil.copy2(temp_path, output_path)
            
            print(f"Image successfully generated and saved to: {output_path}")
            print(f"File size: {os.path.getsize(output_path)} bytes")
            
            # Verify the image can be opened
            image = Image.open(output_path)
            print(f"Image dimensions: {image.size}")
            
            # Clean up the temporary file
            os.remove(temp_path)
            print("Temporary file cleaned up")
            
            return str(output_path)
        else:
            print(f"Generation failed: {result.get('generation_error', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    saved_path = generate_and_save_image()
    if saved_path:
        print(f"\nSuccessfully saved image to: {saved_path}")
    else:
        print("\nFailed to generate image")