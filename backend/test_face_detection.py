#!/usr/bin/env python3
"""
Simple test script for face detection endpoint
"""

import requests
import base64
import json
import cv2
import numpy as np

def create_test_frame():
    """Create a simple test frame with a colored rectangle"""
    # Create a 640x480 test image
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add a colored rectangle to simulate a face-like object
    cv2.rectangle(frame, (200, 150), (440, 330), (255, 255, 255), -1)
    cv2.rectangle(frame, (250, 200), (390, 280), (0, 0, 0), -1)
    
    return frame

def frame_to_base64(frame):
    """Convert OpenCV frame to base64 string"""
    # Encode frame to JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    
    # Convert to base64
    frame_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return frame_base64

def test_face_detection_endpoint():
    """Test the face detection endpoint"""
    url = "http://localhost:8000/face-detection/detect"
    
    # Create test frame
    test_frame = create_test_frame()
    frame_base64 = frame_to_base64(test_frame)
    
    # Prepare request data
    request_data = {
        "frame": frame_base64,
        "frame_id": "test_frame_001",
        "timestamp": "2024-01-01T12:00:00Z"
    }
    
    try:
        # Send request
        response = requests.post(url, json=request_data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Face count: {result.get('face_count')}")
            print(f"Multiple faces: {result.get('has_multiple_faces')}")
            print(f"Confidence: {result.get('confidence')}")
            print("✅ Face detection endpoint is working!")
        else:
            print("❌ Face detection endpoint failed!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the backend is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health_endpoint():
    """Test the health check endpoint"""
    url = "http://localhost:8000/face-detection/health"
    
    try:
        response = requests.get(url)
        print(f"Health Check Status: {response.status_code}")
        print(f"Health Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Health endpoint is working!")
        else:
            print("❌ Health endpoint failed!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the backend is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Testing Face Detection Endpoints...")
    print("=" * 40)
    
    print("\n1. Testing Health Endpoint:")
    test_health_endpoint()
    
    print("\n2. Testing Face Detection Endpoint:")
    test_face_detection_endpoint()
    
    print("\n" + "=" * 40)
    print("Test completed!")
