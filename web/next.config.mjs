/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // When a file is present in public/downloads/ Next.js serves it directly
    // (static files take priority). This rewrite only fires as a fallback —
    // e.g. on Vercel where the large binaries aren't committed — redirecting
    // the browser to the matching GitHub Releases asset instead.
    const GH = 'https://github.com/DogukanGun/Jarvis/releases/latest/download'
    return [
      { source: '/downloads/:file', destination: `${GH}/:file` },
    ]
  },
}

export default nextConfig
