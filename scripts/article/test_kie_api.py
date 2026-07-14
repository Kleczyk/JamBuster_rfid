#!/usr/bin/env python3
"""Test script to check kie.ai API connection and find correct endpoint."""

import requests
import base64
from pathlib import Path

KIE_API_KEY = "3bc7f2c018b971f67ebafa46937b34e9"
KIE_API_BASE = "https://api.kie.ai"

# Test image
test_image = Path("lab bsk/selected_screenshots/Lab14_01__page_0_Picture_2.jpeg")

if not test_image.exists():
    print(f"Test image not found: {test_image}")
    exit(1)

# Read image
with open(test_image, 'rb') as f:
    image_data = f.read()
    image_base64 = base64.b64encode(image_data).decode('utf-8')

headers = {
    'Authorization': f'Bearer {KIE_API_KEY}'
}

# Test different endpoints
endpoints = [
    "/api/v1/image/edit",
    "/api/v1/images/edit", 
    "/api/v1/nano-banana/edit",
    "/api/v1/nano-banana-pro/edit",
    "/api/v1/generate",
    "/v1/generate",
    "/api/generate",
]

print("Testing kie.ai API endpoints...")
print("=" * 60)

for endpoint in endpoints:
    url = f"{KIE_API_BASE}{endpoint}"
    print(f"\nTesting: {url}")
    
    # Try multipart form
    try:
        files = {'image': (test_image.name, image_data, 'image/jpeg')}
        data = {'prompt': 'Remove red frames from this image'}
        
        response = requests.post(url, headers=headers, files=files, data=data, timeout=10)
        print(f"  Multipart: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"  Multipart: Error - {str(e)[:200]}")
    
    # Try JSON with base64
    try:
        json_data = {
            'image': f'data:image/jpeg;base64,{image_base64}',
            'prompt': 'Remove red frames from this image'
        }
        response = requests.post(url, headers={**headers, 'Content-Type': 'application/json'}, 
                                json=json_data, timeout=10)
        print(f"  JSON: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"  JSON: Error - {str(e)[:200]}")

print("\n" + "=" * 60)
print("Testing complete!")
















