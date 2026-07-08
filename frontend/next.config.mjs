/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // API proxying is handled by Route Handlers in src/app/api/* (supports long /chat runs).
  // Do not use rewrites here — Next dev proxy times out on multi-minute crew requests.
};

export default nextConfig;
