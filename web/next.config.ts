import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // the preview pane loads via 127.0.0.1; allow its HMR/dev resources
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
