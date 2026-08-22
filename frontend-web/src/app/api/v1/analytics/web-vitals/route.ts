import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const data = await request.json().catch(() => ({}));
    // In production or development, accept metrics gracefully
    return NextResponse.json({ status: 'ok', received: true });
  } catch (error) {
    return NextResponse.json({ status: 'ok' });
  }
}
