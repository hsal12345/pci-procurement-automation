import type { Metadata } from "next";
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

export const metadata: Metadata = {
  title: "PCI Procurement & SPJ System | CV Pustaka Cemerlang Indonesia",
  description: "Enterprise procurement, document generation, and SPJ verification system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans bg-background text-foreground antialiased`}
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
