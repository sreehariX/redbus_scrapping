import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ['react-leaflet'],
  webpack: (config) => {
    return config;
  }
};

export default nextConfig;
