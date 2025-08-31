#!/usr/bin/env python3
"""
Comprehensive Face Detection Test Script
Tests all components of the face detection system
"""

import requests
import json
import base64
import numpy as np
import cv2
from PIL import Image
import io

def create_test_image_with_face():
    """Create a simple test image with a face-like shape"""
    # Create a 640x480 image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Draw a simple face-like shape (circle for head, rectangles for eyes, etc.)
    # Head
    cv2.circle(img, (320, 240), 100, (255, 255, 255), -1)
    
    # Eyes
    cv2.rectangle(img, (290, 200), (310, 220), (0, 0, 0), -1)
    cv2.rectangle(img, (330, 200), (350, 220), (0, 0, 0), -1)
    
    # Nose
    cv2.rectangle(img, (315, 230), (325, 250), (0, 0, 0), -1)
    
    # Mouth
    cv2.ellipse(img, (320, 280), (30, 10), 0, 0, 180, (0, 0, 0), -1)
    
    return img

def image_to_base64(img):
    """Convert numpy image to base64 string"""
    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Convert to PIL Image
    pil_img = Image.fromarray(img_rgb)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    pil_img.save(img_bytes, format='JPEG', quality=90)
    img_bytes.seek(0)
    
    # Convert to base64
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    return img_base64

def test_backend_health():
    """Test backend health endpoint"""
    print("1. Testing Backend Health...")
    try:
        response = requests.get('http://localhost:8000/face-detection/health')
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Health check passed: {result}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_face_detection_with_test_image():
    """Test face detection with a generated test image"""
    print("\n2. Testing Face Detection with Test Image...")
    try:
        # Create test image
        test_img = create_test_image_with_face()
        img_base64 = image_to_base64(test_img)
        
        # Send to API
        payload = {
            "frame": img_base64,
            "frame_id": "test_face_001",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        response = requests.post(
            'http://localhost:8000/face-detection/detect',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Face detection test passed:")
            print(f"   - Face count: {result.get('face_count', 0)}")
            print(f"   - Multiple faces: {result.get('has_multiple_faces', False)}")
            print(f"   - Confidence: {result.get('confidence', 0)}")
            print(f"   - Status: {result.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Face detection test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Face detection test error: {e}")
        return False

def test_face_detection_with_no_face():
    """Test face detection with an image containing no face"""
    print("\n3. Testing Face Detection with No Face...")
    try:
        # Create blank image
        blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
        img_base64 = image_to_base64(blank_img)
        
        # Send to API
        payload = {
            "frame": img_base64,
            "frame_id": "test_no_face_001",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        response = requests.post(
            'http://localhost:8000/face-detection/detect',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ No-face test passed:")
            print(f"   - Face count: {result.get('face_count', 0)}")
            print(f"   - Multiple faces: {result.get('has_multiple_faces', False)}")
            print(f"   - Status: {result.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ No-face test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ No-face test error: {e}")
        return False

def test_frontend_proxy():
    """Test if frontend proxy is working"""
    print("\n4. Testing Frontend Proxy...")
    try:
        # Test health endpoint through frontend proxy
        response = requests.get('http://localhost:3000/api/face-detection/health')
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Frontend proxy health check passed: {result}")
            return True
        else:
            print(f"❌ Frontend proxy health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend proxy error: {e}")
        print("   Note: This test requires the frontend to be running on port 3000")
        return False

def test_face_detection_through_frontend():
    """Test face detection through frontend proxy"""
    print("\n5. Testing Face Detection Through Frontend...")
    try:
        # Create test image
        test_img = create_test_image_with_face()
        img_base64 = image_to_base64(test_img)
        
        # Send to API through frontend proxy
        payload = {
            "frame": img_base64,
            "frame_id": "test_frontend_001",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        response = requests.post(
            'http://localhost:3000/api/face-detection/detect',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Frontend face detection test passed:")
            print(f"   - Face count: {result.get('face_count', 0)}")
            print(f"   - Status: {result.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Frontend face detection test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Frontend face detection test error: {e}")
        print("   Note: This test requires the frontend to be running on port 3000")
        return False

def main():
    """Run all tests"""
    print("🧪 COMPREHENSIVE FACE DETECTION TEST")
    print("=" * 50)
    
    tests = [
        test_backend_health,
        test_face_detection_with_test_image,
        test_face_detection_with_no_face,
        test_frontend_proxy,
        test_face_detection_through_frontend
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Face detection system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("\n🔧 TROUBLESHOOTING TIPS:")
    print("1. Make sure the backend is running: python app.py")
    print("2. Make sure the frontend is running: npm run dev")
    print("3. Check that face_recognition is installed: pip install face-recognition")
    print("4. Verify all dependencies are installed: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
