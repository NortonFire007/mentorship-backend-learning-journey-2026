import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "cyrillic"],
});

export const metadata: Metadata = {
  title: "Travel Alerts Platform",
  description: "Automated price search and alert notification system",
};

const themeRestoreScript = `
  (function() {
    try {
      var stored = localStorage.getItem('ui-storage');
      var theme = 'light';
      if (stored) {
        var parsed = JSON.parse(stored);
        if (parsed.state && parsed.state.theme) {
          theme = parsed.state.theme;
        }
      } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        theme = 'dark';
      }
      document.documentElement.setAttribute('data-theme', theme);
    } catch (e) {}
  })();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <head>
        <script
          // biome-ignore lint/security/noDangerouslySetInnerHtml: theme restore inline script to prevent hydration flash
          dangerouslySetInnerHTML={{ __html: themeRestoreScript }}
        />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
