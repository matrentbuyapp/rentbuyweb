import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rent vs Buy Calculator — Should You Rent or Buy a Home?",
  description:
    "Free Monte Carlo simulator that runs hundreds of scenarios using real market data to compare renting vs buying a home. See breakeven timing, net worth projections, and cost breakdowns for any US ZIP code.",
  keywords: [
    "rent vs buy calculator",
    "should I rent or buy",
    "rent or buy a home",
    "home buying calculator",
    "mortgage calculator",
    "rent vs buy comparison",
    "real estate calculator",
    "Monte Carlo simulation",
    "breakeven analysis",
    "home affordability",
  ],
  authors: [{ name: "rentbuysellapp.com" }],
  creator: "rentbuysellapp.com",
  metadataBase: new URL("https://rentbuysellapp.com"),
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://rentbuysellapp.com",
    siteName: "Rent vs Buy Calculator",
    title: "Should You Rent or Buy? — Free Calculator with Real Market Data",
    description:
      "Run hundreds of Monte Carlo simulations using real home values, mortgage rates, and tax data for any US ZIP code. See exactly when buying beats renting.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Rent vs Buy Calculator — Net worth comparison chart",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Rent vs Buy Calculator — Real Data, Real Simulations",
    description:
      "Free tool that runs Monte Carlo simulations to compare renting vs buying for any US ZIP code. See breakeven timing and net worth projections.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    name: "Rent vs Buy Calculator",
    url: "https://rentbuysellapp.com",
    description:
      "Monte Carlo simulator comparing renting vs buying a home using real market data for any US ZIP code.",
    applicationCategory: "FinanceApplication",
    operatingSystem: "Any",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
    featureList: [
      "Monte Carlo simulation with 500+ scenarios",
      "Real home values from Zillow for 26,000+ ZIP codes",
      "Current mortgage rates from Freddie Mac",
      "Property tax rates from US Census Bureau",
      "Net worth comparison charts",
      "Breakeven analysis",
      "PMI and tax deduction calculations",
    ],
  };

  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="text-gray-800">{children}</body>
    </html>
  );
}
