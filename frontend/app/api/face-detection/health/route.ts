import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Forward the request to the backend (using Next.js proxy)
    const response = await fetch(`http://localhost:8000/face-detection/health`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const result = await response.json();
    return NextResponse.json(result);
    
  } catch (error) {
    console.error('Face detection health check error:', error);
    return NextResponse.json(
      { 
        status: "unhealthy",
        service: "face-detection",
        available: false,
        error: "Backend service unavailable"
      },
      { status: 503 }
    );
  }
}
