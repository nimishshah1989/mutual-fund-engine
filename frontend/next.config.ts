import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8001";
    return {
      beforeFiles: [
        {
          source: "/api/:path*",
          destination: `${backendUrl}/api/:path*`,
        },
        {
          source: "/health/:path*",
          destination: `${backendUrl}/health/:path*`,
        },
        {
          source: "/health",
          destination: `${backendUrl}/health`,
        },
        {
          source: "/docs",
          destination: `${backendUrl}/docs`,
        },
        {
          source: "/openapi.json",
          destination: `${backendUrl}/openapi.json`,
        },
      ],
    };
  },
};

export default nextConfig;
