# Face Detection Backend API

This backend provides face detection capabilities for the interview system using OpenCV and face_recognition libraries.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The following new dependencies have been added:
- `opencv-python` - For image processing
- `face-recognition` - For face detection and recognition
- `Pillow` - For image handling

### 2. Start the Backend

```bash
python app.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### 1. Face Detection - Single Frame

**Endpoint:** `POST /face-detection/detect`

**Request Body:**
```json
{
  "frame": "base64_encoded_image_string",
  "frame_id": "unique_frame_identifier",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Response:**
```json
{
  "frame_id": "unique_frame_identifier",
  "face_count": 1,
  "has_multiple_faces": false,
  "face_locations": [
    {
      "id": 0,
      "top": 100,
      "right": 300,
      "bottom": 400,
      "left": 200,
      "width": 100,
      "height": 300,
      "center_x": 250,
      "center_y": 250
    }
  ],
  "confidence": 0.8,
  "timestamp": "2024-01-01T12:00:00Z",
  "status": "success"
}
```

### 2. Face Detection - Multiple Frames

**Endpoint:** `POST /face-detection/detect-multiple`

**Request Body:**
```json
[
  {
    "frame": "base64_encoded_image_string_1",
    "frame_id": "frame_001",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  {
    "frame": "base64_encoded_image_string_2",
    "frame_id": "frame_002",
    "timestamp": "2024-01-01T12:01:00Z"
  }
]
```

**Response:**
```json
{
  "results": [
    {
      "frame_id": "frame_001",
      "face_count": 1,
      "has_multiple_faces": false,
      "face_locations": [...],
      "confidence": 0.8,
      "timestamp": "2024-01-01T12:00:00Z",
      "status": "success"
    }
  ],
  "total_frames": 2,
  "successful_frames": 2,
  "status": "completed"
}
```

### 3. Health Check

**Endpoint:** `GET /face-detection/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "face-detection",
  "available": true
}
```

## Usage Examples

### JavaScript/TypeScript (Frontend)

```javascript
// Convert video frame to base64
const canvas = document.createElement('canvas');
const context = canvas.getContext('2d');
canvas.width = video.videoWidth;
canvas.height = video.videoHeight;
context.drawImage(video, 0, 0);
const frameBase64 = canvas.toDataURL('image/jpeg').split(',')[1];

// Send to backend
const response = await fetch('/face-detection/detect', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    frame: frameBase64,
    frame_id: `frame_${Date.now()}`,
    timestamp: new Date().toISOString()
  })
});

const result = await response.json();
console.log(`Detected ${result.face_count} faces`);
console.log(`Multiple faces: ${result.has_multiple_faces}`);
```

### Python (Backend Testing)

```python
import requests
import base64
import cv2

# Load and encode image
image = cv2.imread('test_image.jpg')
_, buffer = cv2.imencode('.jpg', image)
frame_base64 = base64.b64encode(buffer).decode('utf-8')

# Send request
response = requests.post('http://localhost:8000/face-detection/detect', json={
    'frame': frame_base64,
    'frame_id': 'test_001',
    'timestamp': '2024-01-01T12:00:00Z'
})

print(response.json())
```

## Testing

Run the test script to verify the endpoints work:

```bash
python test_face_detection.py
```

## Features

- **Face Detection**: Detects faces in video frames using face_recognition library
- **Multiple Face Detection**: Identifies when multiple faces are present
- **Face Location Data**: Provides detailed coordinates and dimensions of detected faces
- **Confidence Scoring**: Calculates confidence levels for detection accuracy
- **Batch Processing**: Supports processing multiple frames at once
- **Error Handling**: Robust error handling with detailed error messages
- **Health Monitoring**: Health check endpoint for service monitoring

## Response Fields

- `face_count`: Number of faces detected in the frame
- `has_multiple_faces`: Boolean indicating if more than one face was detected
- `face_locations`: Array of face location objects with coordinates and dimensions
- `confidence`: Confidence score (0.0 to 1.0) for the detection
- `status`: Success/error status of the detection

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Successful detection
- `400`: Invalid input data
- `500`: Server error during processing

All errors include descriptive messages to help with debugging.
