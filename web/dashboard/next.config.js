/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    appDir: false
  },
  async rewrites() {
    return [
      {
        source: '/v1/:path*',
        destination: process.env.API_BASE_URL ? `${process.env.API_BASE_URL}/v1/:path*` : 'http://localhost:8000/v1/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
