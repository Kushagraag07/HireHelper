import cv2
import numpy as np
import face_recognition
from typing import List, Dict, Tuple, Optional
import base64

def decode_base64_image(frame_base64: str) -> Optional[np.ndarray]:
    """
    Decode base64 image string to numpy array
    """
    try:
        # Remove data URL prefix if present
        if frame_base64.startswith('data:image'):
            frame_base64 = frame_base64.split(',')[1]
        
        # Decode base64 to bytes
        frame_bytes = base64.b64decode(frame_base64)
        
        # Convert to numpy array
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return frame
    except Exception as e:
        print(f"Error decoding base64 image: {e}")
        return None

def detect_faces_in_frame(frame: np.ndarray) -> Tuple[List[Tuple], List[np.ndarray], int]:
    """
    Detect faces in a frame using face_recognition library
    
    Returns:
        - face_locations: List of (top, right, bottom, left) tuples
        - face_encodings: List of face encodings
        - face_count: Number of faces detected
    """
    try:
        # Convert BGR to RGB (face_recognition uses RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(frame_rgb)
        face_encodings = face_recognition.face_encodings(frame_rgb, face_locations)
        
        return face_locations, face_encodings, len(face_locations)
    except Exception as e:
        print(f"Error detecting faces: {e}")
        return [], [], 0

def process_face_locations(face_locations: List[Tuple]) -> List[Dict]:
    """
    Convert face locations to a more usable format
    """
    processed_locations = []
    
    for i, (top, right, bottom, left) in enumerate(face_locations):
        face_info = {
            "id": i,
            "top": int(top),
            "right": int(right),
            "bottom": int(bottom),
            "left": int(left),
            "width": int(right - left),
            "height": int(bottom - top),
            "center_x": int((left + right) / 2),
            "center_y": int((top + bottom) / 2)
        }
        processed_locations.append(face_info)
    
    return processed_locations

def calculate_face_detection_confidence(face_count: int, face_locations: List[Tuple]) -> float:
    """
    Calculate confidence score for face detection
    """
    if face_count == 0:
        return 0.0
    
    # Base confidence
    confidence = 0.8
    
    # Adjust based on number of faces (more faces might indicate lower quality)
    if face_count > 1:
        confidence -= 0.1 * (face_count - 1)
    
    # Ensure confidence is between 0 and 1
    return max(0.0, min(1.0, confidence))

def validate_frame_data(frame_data: Dict) -> bool:
    """
    Validate frame data structure
    """
    required_fields = ["frame"]
    
    for field in required_fields:
        if field not in frame_data:
            return False
    
    if not frame_data["frame"]:
        return False
    
    return True
