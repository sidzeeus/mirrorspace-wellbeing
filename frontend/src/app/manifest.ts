import type { MetadataRoute } from "next";

/** Makes the app installable. It opens on the home screen, with Support one tap away. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Mirrorspace",
    short_name: "Mirrorspace",
    description:
      "A private wellbeing companion for students aged 18 and over. Not therapy, and not an emergency service.",
    start_url: "/home",
    scope: "/",
    display: "standalone",
    background_color: "#06070c",
    theme_color: "#06070c",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [{ name: "Support", url: "/support" }],
  };
}
