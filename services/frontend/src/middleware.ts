import type { NextRequest } from "next/server";
import createMiddleware from "next-intl/middleware";

const intlMiddleware = createMiddleware({
  locales: ["en", "uk"],
  defaultLocale: "en",
  localePrefix: "always",
});

const PROTECTED_ROUTES = ["/dashboard", "/subscriptions", "/settings"];

export default function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Extract locale prefix from pathname, e.g. /en/dashboard -> /dashboard
  const pathnameWithoutLocale = pathname.replace(/^\/(en|uk)/, "") || "/";

  const isProtectedRoute = PROTECTED_ROUTES.some(
    (route) =>
      pathnameWithoutLocale === route ||
      pathnameWithoutLocale.startsWith(`${route}/`),
  );

  if (isProtectedRoute) {
    const refreshToken = req.cookies.get("refresh_token")?.value;
    if (!refreshToken) {
      const locale = pathname.match(/^\/(en|uk)/)?.[1] || "en";
      const loginUrl = new URL(`/${locale}/login`, req.url);
      return Response.redirect(loginUrl);
    }
  }

  return intlMiddleware(req);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
