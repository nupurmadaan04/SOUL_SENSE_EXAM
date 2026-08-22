/** @type {import('next').NextConfig} */
const nextConfig = {
  // Optimize images
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'i.pravatar.cc',
      },
      {
        protocol: 'https',
        hostname: 'avatars.githubusercontent.com',
      },
      {
        protocol: 'https',
        hostname: 'github.com',
      },
    ],
    formats: ['image/webp', 'image/avif'],
  },

  // Enable SWC minification for faster builds
  swcMinify: true,

  eslint: {
    ignoreDuringBuilds: true,
  },

  // Performance optimizations
  experimental: {
    // optimizeCss: true, // Only available for "pages" directory
  },

  // Headers for better caching and security
  async headers() {
    return [
      {
        source: '/:all*(svg|jpg|jpeg|png|ico|webp)',
        locale: false,
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },
};

// Wrap with bundle analyzer if ANALYZE=true
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
  openAnalyzer: false,
});

module.exports = withBundleAnalyzer(nextConfig);
