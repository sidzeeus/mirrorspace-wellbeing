import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";

export const LOCALES = ["en", "hi"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "en";
export const LOCALE_COOKIE = "locale";

function pick(value: string | undefined | null): Locale | null {
  const code = value?.slice(0, 2).toLowerCase();
  return (LOCALES as readonly string[]).includes(code ?? "") ? (code as Locale) : null;
}

/**
 * The language comes from a cookie the language selector sets, then from the
 * browser's preference. There is no locale in the URL, so links never change.
 * Any string missing from a translation falls back to English.
 */
export default getRequestConfig(async () => {
  const cookieLocale = pick((await cookies()).get(LOCALE_COOKIE)?.value);
  const headerLocale = pick((await headers()).get("accept-language"));
  const locale = cookieLocale ?? headerLocale ?? DEFAULT_LOCALE;
  const english = (await import("../../messages/en")).default as Tree;
  const messages =
    locale === "en"
      ? english
      : deepMerge(english, (await import(`../../messages/${locale}/index`)).default as Tree);
  return { locale, messages, timeZone: "UTC" };
});

type Tree = { [key: string]: string | Tree };

function deepMerge(base: Tree, override: Tree): Tree {
  const result: Tree = { ...base };
  for (const [key, value] of Object.entries(override)) {
    if (key.startsWith("_")) continue;
    const existing = result[key];
    result[key] =
      typeof value === "object" && typeof existing === "object"
        ? deepMerge(existing, value)
        : value;
  }
  return result;
}
