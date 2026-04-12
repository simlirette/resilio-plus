import { NextResponse } from 'next/server'

// Mock config — replace with real backend call when API is ready
export function GET() {
  return NextResponse.json({
    api_url: 'http://localhost:8000',
    version: '1.0.0',
    features: {
      strava: true,
      hevy: true,
      terra: true,
    },
  })
}
