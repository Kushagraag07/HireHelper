from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import base64
import io
from PIL import Image
import face_recognition
import json
from typing import List, Dict, Any
from utils.face_detection_utils import (
    decode_base64_image,
    detect_faces_in_frame,
    process_face_locations,
    calculate_face_detection_confidence,
    validate_frame_data
)

router = APIRouter(prefix="/face-detection", tags=["face-detection"])

class FaceDetectionResponse:
    def __init__(self, face_count: int, has_multiple_faces: bool, face_locations: List[Dict], confidence: float):
        self.face_count = face_count
        self.has_multiple_faces = has_multiple_faces
        self.face_locations = face_locations
        self.confidence = confidence

@router.post("/detect")
async def detect_faces(frame_data: Dict[str, Any]):
    """
    Detect faces in a video frame
    Expected input: {"frame": "base64_encoded_image", "frame_id": "unique_id"}
    """
    try:
        # Validate input data
        if not validate_frame_data(frame_data):
            raise HTTPException(status_code=400, detail="Invalid frame data structure")
        
        # Extract frame data
        frame_base64 = frame_data.get("frame")
        frame_id = frame_data.get("frame_id", "unknown")
        
        # Decode base64 image
        frame = decode_base64_image(frame_base64)
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Detect faces
        face_locations, face_encodings, face_count = detect_faces_in_frame(frame)
        
        # Process results
        has_multiple_faces = face_count > 1
        processed_face_locations = process_face_locations(face_locations)
        confidence = calculate_face_detection_confidence(face_count, face_locations)
        
        # Create response
        response = {
            "frame_id": frame_id,
            "face_count": face_count,
            "has_multiple_faces": has_multiple_faces,
            "face_locations": processed_face_locations,
            "confidence": confidence,
            "timestamp": frame_data.get("timestamp"),
            "status": "success"
        }
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face detection error: {str(e)}")

@router.post("/detect-multiple")
async def detect_multiple_frames(frames_data: List[Dict[str, Any]]):
    """
    Detect faces in multiple video frames
    Expected input: [{"frame": "base64_encoded_image", "frame_id": "unique_id"}, ...]
    """
    try:
        results = []
        
        for frame_data in frames_data:
            try:
                # Use the single frame detection logic
                result = await detect_faces(frame_data)
                results.append(result.body.decode() if hasattr(result, 'body') else result)
            except Exception as e:
                # Continue processing other frames even if one fails
                error_result = {
                    "frame_id": frame_data.get("frame_id", "unknown"),
                    "face_count": 0,
                    "has_multiple_faces": False,
                    "face_locations": [],
                    "confidence": 0.0,
                    "timestamp": frame_data.get("timestamp"),
                    "status": "error",
                    "error": str(e)
                }
                results.append(error_result)
        
        return JSONResponse(content={
            "results": results,
            "total_frames": len(frames_data),
            "successful_frames": len([r for r in results if r.get("status") == "success"]),
            "status": "completed"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multiple frame detection error: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for face detection service"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "face-detection",
        "available": True
    })
