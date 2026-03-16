import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "JIP MF Recommendation Engine",
  description:
    "Jhaveri Intelligence Platform — Mutual Fund Scoring & Recommendations",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased overflow-x-hidden`}>
        <Sidebar />
        <main className="md:ml-56 bg-slate-50 min-h-screen p-4 pt-14 md:pt-6 md:p-6">{children}</main>
      </body>
    </html>
  );
}
