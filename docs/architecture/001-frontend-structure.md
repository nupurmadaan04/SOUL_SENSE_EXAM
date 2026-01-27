# ADR 001: Frontend Directory Structure and Conventions

**Date:** 2026-01-27
**Status:** Accepted

## Context

The current frontend codebase lacks a standardized structure for components, utilities, and configuration. As the project scales, this ambiguity leads to inconsistent imports, scattered business logic, and maintenance friction.

## Decision

We will adopt a **feature-sliced, domain-driven** directory structure within the `src` folder, utilizing strict separation of concerns and barrel file exports.

### Directory Structure

```
src/
├── app/                  # Next.js App Router (Pages & Layouts)
│   ├── (routes)/         # Route groups (e.g., (auth), (dashboard))
│   └── layout.tsx        # Root layout
├── components/           # Reusable UI & Logic
│   ├── ui/               # Primitive, headless-first UI (Button, Input)
│   ├── layout/           # Structural components (Navbar, Footer)
│   ├── forms/            # Complex form logic & composites
│   ├── sections/         # Feature-specific page sections (Hero, Features)
│   └── shared/           # Cross-cutting business components
├── lib/                  # Utilities & Helpers
│   ├── api/              # API Clients & Fetchers
│   ├── hooks/            # Custom React Hooks
│   ├── utils/            # Pure helper functions
│   └── constants/        # Static configuration & magic numbers
├── types/                # Global TypeScript definitions
└── store/                # Global State Management (Context/Zustand)
```

### Conventions

- **Component Names**: `PascalCase` (e.g., `Button.tsx`).
- **Utility Names**: `camelCase` (e.g., `formatDate.ts`).
- **Imports**: Absolute imports via `@/` alias (e.g., `@/components/ui`, not `../../components/ui`).
- **Exports**: Use `index.ts` (barrel files) at the root of `ui`, `layout`, etc., to enable named imports.
- **Strictness**: `tsconfig.json` will enforce strict mode and no implicit any.

## Consequences

### Positive

- **Discoverability**: Logic is easy to find based on its domain.
- **Scalability**: New features have a clear home.
- **Refactoring**: Isolating primitives makes system-wide UI updates reliable.

### Negative

- **Initial Friction**: Requires moving existing files and updating import paths.
- **Boilerplate**: Might feel like "over-engineering" for very simple components initially.

## Code Review Checklist

- [ ] **Import Paths**: ensure `@/` aliases are used instead of relative paths.
- [ ] **Internal Imports**: check that components within a domain (e.g., `ui`) do NOT import from their own `index.ts`.
- [ ] **Naming**: verify `PascalCase` for components and `camelCase` for utilities.
- [ ] **Placement**: utilities should be in `lib/utils`, hooks in `lib/hooks`, etc.
- [ ] **Barrel Files**: new public components/utilities must be added to the local `index.ts`.
