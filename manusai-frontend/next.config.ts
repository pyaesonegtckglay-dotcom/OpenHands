import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Remove 'standalone' output for Vercel deployment (Vercel handles this natively)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
  // Allow Vercel to optimize images from any domain
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
