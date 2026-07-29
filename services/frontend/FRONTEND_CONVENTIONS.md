# Frontend Conventions & Architecture Rules

This document outlines the strict engineering standards, stack constraints, architectural patterns, and code conventions for `services/frontend`.

---

## 1. Locked Technology Stack

- **Framework**: Next.js 16 (App Router, Turbopack for dev, Server Components, Server Actions)
- **UI & React**: React 19.2 (Server Components, useEffectEvent, View Transitions)
- **Language**: TypeScript (Strict Mode, `noAny`, typed API contracts)
- **Styling**: Tailwind CSS v4 (CSS-first `@theme` configuration in `globals.css`, no `tailwind.config.js`)
- **Forms & Validation**: React Hook Form + Zod (`@hookform/resolvers/zod`)
- **Server State & Data Fetching**: TanStack Query v5 (client caching, background refetch, optimistic updates)
- **Client State**: Zustand (ephemeral UI state & auth memory store only)
- **Internationalization**: `next-intl` (App Router locale routing: `[locale]`, EN & UK messages)
- **Linting & Formatting**: Biome (`biome.json`, single tool for lint + format)
- **Testing**: Vitest (unit/component testing) + Storybook 9 (`@storybook/nextjs-vite` + `addon-vitest`) + Playwright (E2E)

---

## 2. Directory & File Organization

```
services/frontend/
├── src/
│   ├── app/
│   │   ├── [locale]/
│   │   │   ├── (auth)/             # Authentication routes (AuthLayout)
│   │   │   │   ├── login/
│   │   │   │   ├── register/
│   │   │   │   └── layout.tsx
│   │   │   ├── (app)/              # Protected application routes (AppShell)
│   │   │   │   ├── dashboard/
│   │   │   │   ├── subscriptions/
│   │   │   │   │   └── new/
│   │   │   │   ├── settings/
│   │   │   │   └── layout.tsx
│   │   │   └── page.tsx            # Root locale redirect
│   │   ├── globals.css             # Tailwind v4 @theme design tokens & z-index scale
│   │   └── layout.tsx               # Root layout (fonts, providers, inline theme script)
│   ├── components/
│   │   ├── ui/                     # Primitive design components (Button, Input, Badge, etc.)
│   │   ├── features/               # Domain-specific components (subscriptions, alerts, auth)
│   │   └── layouts/                # Structural layouts (AppShell, AuthLayout)
│   ├── hooks/                      # Custom React hooks (useAuth, useSubscriptions, etc.)
│   ├── lib/
│   │   ├── clients/                # API fetch client wrapper with 401 silent refresh
│   │   ├── queries/                # TanStack Query key factory & query functions
│   │   └── schemas/                # Zod schemas for forms & validation
│   ├── stores/                     # Zustand stores (authStore, uiStore)
│   └── types/                      # TypeScript API data models & contracts
├── messages/                       # i18n JSON files
│   ├── en.json
│   └── uk.json
├── middleware.ts                   # next-intl + cookie-based auth guard
├── biome.json                      # Biome rules
├── playwright.config.ts
└── vitest.config.ts
```

---

## 3. Data & State Ownership Rules

1. **Server Data (Subscriptions, Alerts, User Profile)**: Owned exclusively by **TanStack Query**.
   - No duplication in Zustand stores or React state.
   - Mutations must invalidate query keys (defined in `lib/queries/keys.ts`) or perform optimistic updates.
2. **Auth Token (Access Token)**: Stored in **Zustand (`authStore`) in memory only**.
   - Never write access token to `localStorage` or `sessionStorage`.
   - Session restoration on cold start uses httpOnly `refresh_token` cookie via `/api/v1/auth/refresh`.
3. **UI & Ephemeral State**: Stored in **Zustand (`uiStore`)** or React `useState`.
   - Theme and locale preferences persist to `localStorage`.
   - Subscription creation wizard state persists to `sessionStorage` and is explicitly cleared (`clearWizard()`) on successful submit.

---

## 4. Styling & Design Tokens Rules

- Define all design tokens (colors, radii, shadows, z-index) in `src/app/globals.css` using Tailwind CSS v4 `@theme`.
- **Theme Support**: Use `[data-theme="dark"]` attribute on `<html>`. The inline `<script>` in root `layout.tsx` restores theme before hydration to prevent flash.
- **Z-Index Layering**: Use defined semantic z-index CSS variables:
  - `--z-dropdown: 100`
  - `--z-sticky: 200`
  - `--z-modal: 300`
  - `--z-toast: 400`
- Do NOT hardcode arbitrary `z-[999]` or inline styles.

---

## 5. Forms & Validation

- All forms MUST use `react-hook-form` paired with a Zod schema via `@hookform/resolvers/zod`.
- Schemas live in `src/lib/schemas/`.
- Show field-level validation errors inline before making API requests.

---

## 6. Testing & Code Quality

- **Lint & Format**: Run `npx biome check` (enforced via `simple-git-hooks`).
- **Unit & Hook Tests**: Vitest + Testing Library in `src/__tests__/` or co-located `.test.ts` files.
- **Component Stories**: Storybook stories co-located with components (`*.stories.tsx`).
- **E2E Tests**: Playwright scripts in `e2e/`.
