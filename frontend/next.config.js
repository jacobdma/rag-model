/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    allowedDevOrigins: process.env.ALLOWED_DEV_ORIGIN
      ? [process.env.ALLOWED_DEV_ORIGIN]
      : ['http://localhost:3000'],
  },
};

module.exports = nextConfig;