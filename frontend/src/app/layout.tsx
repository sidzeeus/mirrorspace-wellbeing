import "./globals.css";

import type { Metadata, Viewport } from "next";
import { Hanken_Grotesk, IBM_Plex_Mono, Noto_Sans_Devanagari } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

import { AuroraBackground } from "@/components/AuroraBackground";
import { Providers } from "@/components/Providers";
import { SkipLink } from "@/components/ui/primitives";
import { PREFS_BOOT_SCRIPT } from "@/lib/prefs";

const display = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-display",
  display: "swap",
  // Not preloaded, so low-bandwidth mode (which never uses it) downloads no font.
  preload: false,
});
// Used for small data labels only, so it is not preloaded.
const data = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-data",
  display: "swap",
  preload: false,
});
// Loaded only when Devanagari text is actually on the page.
const devanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500"],
  variable: "--font-devanagari",
  display: "swap",
  preload: false,
});

export const metadata: Metadata = {
  title: { default: "Mirrorspace", template: "%s · Mirrorspace" },
  description:
    "A private wellbeing companion for students aged 18 and over. Not therapy, and not an emergency service.",
  applicationName: "Mirrorspace",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#07060d" },
    { media: "(prefers-color-scheme: light)", color: "#f7f5fc" },
  ],
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const [locale, messages, t] = await Promise.all([
    getLocale(),
    getMessages(),
    getTranslations("common"),
  ]);
  return (
    <html
      lang={locale}
      data-theme="night"
      className={`${display.variable} ${data.variable} ${devanagari.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: PREFS_BOOT_SCRIPT }} />
      </head>
      <body className="text-moon antialiased">
        <NextIntlClientProvider locale={locale} messages={messages} timeZone="UTC">
          <AuroraBackground />
          <SkipLink>{t("skipToContent")}</SkipLink>
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
