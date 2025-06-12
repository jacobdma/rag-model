import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    disableStaticImages: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  experimental: {
    allowedDevOrigins: process.env.ALLOWED_DEV_ORIGIN
      ? [process.env.ALLOWED_DEV_ORIGIN]
      : ['http://localhost:3000'],
  } as any,
};

export default nextConfig;