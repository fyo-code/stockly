import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stockly - Site Demo",
  description: "A sanitized interactive site demo for Stockly.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-950">{children}</body>
    </html>
  );
}
