# PCI Procurement & SPJ Automation — Frontend (Next.js)

Web interface for the CV Pustaka Cemerlang Indonesia (PCI) Procurement & SPJ Automation System, built with Next.js App Router, React Query, Tailwind CSS, and `pnpm`.

## Getting Started

Install dependencies and run the development server using `pnpm` (matching `pnpm-lock.yaml`):

```bash
corepack pnpm install
corepack pnpm dev
```

Open [http://localhost:3000/login](http://localhost:3000/login) to sign in (main dashboard redirects to `/packages`).

## Key Entry Points

- `src/app/login/page.tsx` — Manual RBAC authentication page (`/login`)
- `src/app/(dashboard)/packages/page.tsx` — Main procurement packages dashboard (`/packages`)
- `src/components/auth/auth-guard.tsx` — Client session & RBAC route guard
- `src/components/layout/sidebar.tsx` — Role-filtered navigation sidebar

## Typecheck & Production Build

```bash
corepack pnpm exec tsc --noEmit
corepack pnpm build
```

