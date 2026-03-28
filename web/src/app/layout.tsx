import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rent vs Buy Calculator",
  description: "Monte Carlo simulation to compare renting vs buying a home",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="text-gray-800">{children}</body>
    </html>
  );
}
