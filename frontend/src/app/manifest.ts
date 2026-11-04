import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "PCI Procurement & SPJ System",
    short_name: "PCI SPJ",
    description:
      "Sistem Otomasi Pengadaan Barang & Jasa dan Dokumen Pertanggungjawaban (SPJ) Sekolah Dasar CV Pustaka Cemerlang Indonesia",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait-primary",
    background_color: "#FFFFFF",
    theme_color: "#02569D",
    lang: "id",
    categories: ["business", "productivity", "utilities"],
    icons: [
      {
        src: "/favicon.ico",
        sizes: "any",
        type: "image/x-icon",
      },
      {
        src: "/images/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable any" as any,
      },
      {
        src: "/images/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable any" as any,
      },
    ],
    shortcuts: [
      {
        name: "Paket Pengadaan",
        short_name: "Paket",
        description: "Buka daftar paket pengadaan barang dan jasa",
        url: "/packages",
        icons: [{ src: "/images/icon-192.png", sizes: "192x192" }],
      },
      {
        name: "Impor Spreadsheet",
        short_name: "Impor",
        description: "Unggah berkas Excel pengadaan",
        url: "/imports",
        icons: [{ src: "/images/icon-192.png", sizes: "192x192" }],
      },
      {
        name: "AI & Audit Usage",
        short_name: "AI & Audit",
        description: "Pantau tata kelola AI dan log sistem",
        url: "/ai/usage",
        icons: [{ src: "/images/icon-192.png", sizes: "192x192" }],
      },
    ],
  };
}

