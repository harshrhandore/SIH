import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { GlobalBanner } from "@/components/shared/scope-banner";
const heading = localFont({
  src: "../../public/fonts/fraunces/latin-600.woff2",
  variable: "--font-heading",
  weight: "600",
  display: "swap",
});
const body = localFont({
  src: [
    {
      path: "../../public/fonts/instrument-sans/latin-400.woff2",
      weight: "400",
    },
    {
      path: "../../public/fonts/instrument-sans/latin-500.woff2",
      weight: "500",
    },
    {
      path: "../../public/fonts/instrument-sans/latin-600.woff2",
      weight: "600",
    },
  ],
  variable: "--font-body",
  display: "swap",
});
const mono = localFont({
  src: "../../public/fonts/ibm-plex-mono/latin-400.woff2",
  variable: "--font-mono",
  weight: "400",
  display: "swap",
});
export const metadata: Metadata = {
  title: "Shiksham · Synthetic academic ledger",
  description:
    "Synthetic student records, explainable local checks and accountable human review.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${heading.variable} ${body.variable} ${mono.variable}`}
    >
      <body>
        <GlobalBanner />
        {children}
      </body>
    </html>
  );
}
