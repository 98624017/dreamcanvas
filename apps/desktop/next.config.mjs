const nextConfig = {
  experimental: {
    appDir: true
  },
  output: "standalone",
  reactStrictMode: true,
  transpilePackages: ["@tauri-apps/api", "tldraw"]
};

export default nextConfig;
