import type { NextConfig } from "next";

// NEXT_TAURI_STATIC=1 enables static export for Tauri desktop production builds.
// The regular `next build` (SSR) is unaffected.
const isTauriBuild = process.env.NEXT_TAURI_STATIC === "1";

const nextConfig: NextConfig = {
  ...(isTauriBuild && {
    output: "export",
    distDir: "out",
    images: {
      unoptimized: true,
    },
  }),
};

export default nextConfig;
