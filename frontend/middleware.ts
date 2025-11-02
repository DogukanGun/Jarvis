import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if the user is trying to access protected routes
  if (pathname.startsWith('/dashboard')) {
    // Since we can't access localStorage in middleware, we'll rely on client-side protection
    // The dashboard pages will handle the actual auth check and redirect
    return NextResponse.next();
  }

  // Allow access to all other routes
  return NextResponse.next();
}

// Configure which routes should be protected
export const config = {
  matcher: [
    '/dashboard/:path*',
  ],
};
