import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import Providers from "./providers";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const viewport: Viewport = {
  themeColor: "#02569D",
};

export const metadata: Metadata = {
  title: "PCI Procurement & SPJ System | CV Pustaka Cemerlang Indonesia",
  description: "Sistem Otomasi Pengadaan Barang/Jasa & Dokumen SPJ Resmi CV Pustaka Cemerlang Indonesia",
  icons: {
    icon: [
      { url: "/images/pci-icon.png", sizes: "32x32", type: "image/png" },
      { url: "/images/pci-icon.png", sizes: "192x192", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
    apple: "/images/pci-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const storedTheme = localStorage.getItem('pci_theme');
                if (storedTheme === 'dark') {
                  document.documentElement.classList.add('dark');
                } else {
                  document.documentElement.classList.remove('dark');
                }
              } catch (e) {}
            `,
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans bg-background text-foreground antialiased min-h-screen`}
        style={{
          // @ts-ignore
          "--font-inter": "var(--font-geist-sans)",
          "--font-jetbrains-mono": "var(--font-geist-mono)",
        }}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
