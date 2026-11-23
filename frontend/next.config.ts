import type { NextConfig } from "next";

// Where `next dev` forwards API calls. The production build is a static export that
// Flask serves from the same origin, so it needs no rewrites (and a static export
// rejects them).
const API_DEV_URL = process.env.API_DEV_URL ?? "http://localhost:5001";
const API_PATHS = ["/chat", "/history", "/health", "/prompt", "/domains/:path*", "/chat-info/:path*", "/api/:path*"];

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  ...(process.env.NODE_ENV === "development" && {
    async rewrites() {
      return API_PATHS.map((source) => ({ source, destination: `${API_DEV_URL}${source}` }));
    },
  }),
};

export default nextConfig;
