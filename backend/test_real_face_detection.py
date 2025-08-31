#!/usr/bin/env python3
"""
Real Face Detection Test
Tests face detection with more realistic face images
"""

import requests
import json
import base64
import numpy as np
import cv2
from PIL import Image, ImageDraw
import io

def create_realistic_face_image():
    """Create a more realistic face image"""
    # Create a 640x480 image with a more realistic face
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Skin color background
    img[:, :] = [255, 220, 177]  # Light skin tone
    
    # Head shape (oval)
    cv2.ellipse(img, (320, 240), (120, 150), 0, 0, 360, [255, 220, 177], -1)
    
    # Hair (dark)
    cv2.ellipse(img, (320, 180), (130, 80), 0, 0, 180, [50, 25, 0], -1)
    
    # Eyes (more realistic)
    # Left eye
    cv2.ellipse(img, (280, 200), (25, 15), 0, 0, 360, [255, 255, 255], -1)  # White
    cv2.ellipse(img, (280, 200), (12, 12), 0, 0, 360, [139, 69, 19], -1)    # Brown iris
    cv2.ellipse(img, (280, 200), (6, 6), 0, 0, 360, [0, 0, 0], -1)          # Pupil
    
    # Right eye
    cv2.ellipse(img, (360, 200), (25, 15), 0, 0, 360, [255, 255, 255], -1)  # White
    cv2.ellipse(img, (360, 200), (12, 12), 0, 0, 360, [139, 69, 19], -1)    # Brown iris
    cv2.ellipse(img, (360, 200), (6, 6), 0, 0, 360, [0, 0, 0], -1)          # Pupil
    
    # Nose
    cv2.ellipse(img, (320, 250), (8, 20), 0, 0, 360, [255, 200, 150], -1)
    
    # Mouth
    cv2.ellipse(img, (320, 300), (30, 15), 0, 0, 180, [255, 255, 255], -1)  # Upper lip
    cv2.ellipse(img, (320, 300), (30, 15), 0, 180, 360, [255, 200, 200], -1) # Lower lip
    
    # Eyebrows
    cv2.ellipse(img, (280, 180), (20, 8), 0, 0, 180, [50, 25, 0], -1)  # Left eyebrow
    cv2.ellipse(img, (360, 180), (20, 8), 0, 0, 180, [50, 25, 0], -1)  # Right eyebrow
    
    return img

def create_multiple_faces_image():
    """Create an image with multiple faces"""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # First face (left side)
    # Head
    cv2.ellipse(img, (200, 240), (80, 100), 0, 0, 360, [255, 220, 177], -1)
    # Eyes
    cv2.ellipse(img, (180, 200), (15, 10), 0, 0, 360, [255, 255, 255], -1)
    cv2.ellipse(img, (220, 200), (15, 10), 0, 0, 360, [255, 255, 255], -1)
    # Nose
    cv2.ellipse(img, (200, 250), (5, 15), 0, 0, 360, [255, 200, 150], -1)
    # Mouth
    cv2.ellipse(img, (200, 280), (20, 10), 0, 0, 180, [255, 255, 255], -1)
    
    # Second face (right side)
    # Head
    cv2.ellipse(img, (440, 240), (80, 100), 0, 0, 360, [255, 220, 177], -1)
    # Eyes
    cv2.ellipse(img, (420, 200), (15, 10), 0, 0, 360, [255, 255, 255], -1)
    cv2.ellipse(img, (460, 200), (15, 10), 0, 0, 360, [255, 255, 255], -1)
    # Nose
    cv2.ellipse(img, (440, 250), (5, 15), 0, 0, 360, [255, 200, 150], -1)
    # Mouth
    cv2.ellipse(img, (440, 280), (20, 10), 0, 0, 180, [255, 255, 255], -1)
    
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

def test_single_face_detection():
    """Test face detection with a single realistic face"""
    print("1. Testing Single Face Detection...")
    try:
        # Create realistic face image
        face_img = create_realistic_face_image()
        img_base64 = image_to_base64(face_img)
        
        # Send to API
        payload = {
            "frame": img_base64,
            "frame_id": "single_face_test",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        response = requests.post(
            'http://localhost:8000/face-detection/detect',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Single face detection test:")
            print(f"   - Face count: {result.get('face_count', 0)}")
            print(f"   - Multiple faces: {result.get('has_multiple_faces', False)}")
            print(f"   - Confidence: {result.get('confidence', 0)}")
            print(f"   - Status: {result.get('status', 'unknown')}")
            
            # Save the test image for inspection
            cv2.imwrite('test_single_face.jpg', face_img)
            print(f"   - Test image saved as 'test_single_face.jpg'")
            
            return result.get('face_count', 0) > 0
        else:
            print(f"❌ Single face detection test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Single face detection test error: {e}")
        return False

def test_multiple_faces_detection():
    """Test face detection with multiple faces"""
    print("\n2. Testing Multiple Faces Detection...")
    try:
        # Create multiple faces image
        faces_img = create_multiple_faces_image()
        img_base64 = image_to_base64(faces_img)
        
        # Send to API
        payload = {
            "frame": img_base64,
            "frame_id": "multiple_faces_test",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        response = requests.post(
            'http://localhost:8000/face-detection/detect',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Multiple faces detection test:")
            print(f"   - Face count: {result.get('face_count', 0)}")
            print(f"   - Multiple faces: {result.get('has_multiple_faces', False)}")
            print(f"   - Confidence: {result.get('confidence', 0)}")
            print(f"   - Status: {result.get('status', 'unknown')}")
            
            # Save the test image for inspection
            cv2.imwrite('test_multiple_faces.jpg', faces_img)
            print(f"   - Test image saved as 'test_multiple_faces.jpg'")
            
            return result.get('face_count', 0) >= 2
        else:
            print(f"❌ Multiple faces detection test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Multiple faces detection test error: {e}")
        return False

def test_face_recognition_library_directly():
    """Test face_recognition library directly"""
    print("\n3. Testing Face Recognition Library Directly...")
    try:
        import face_recognition
        
        # Create realistic face image
        face_img = create_realistic_face_image()
        
        # Convert BGR to RGB (face_recognition uses RGB)
        face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(face_img_rgb)
        face_encodings = face_recognition.face_encodings(face_img_rgb, face_locations)
        
        print(f"✅ Direct face_recognition test:")
        print(f"   - Face locations found: {len(face_locations)}")
        print(f"   - Face encodings: {len(face_encodings)}")
        
        for i, (top, right, bottom, left) in enumerate(face_locations):
            print(f"   - Face {i+1}: top={top}, right={right}, bottom={bottom}, left={left}")
        
        return len(face_locations) > 0
        
    except Exception as e:
        print(f"❌ Direct face_recognition test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 REAL FACE DETECTION TEST")
    print("=" * 50)
    
    tests = [
        test_single_face_detection,
        test_multiple_faces_detection,
        test_face_recognition_library_directly
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
        print("🎉 All face detection tests passed!")
    else:
        print("⚠️  Some face detection tests failed.")
        print("   This might indicate that the face_recognition model needs real photos to work properly.")
    
    print("\n💡 NOTE: Face detection models typically work best with real photos.")
    print("   The generated test images might not be realistic enough for the model.")

if __name__ == "__main__":
    main()
