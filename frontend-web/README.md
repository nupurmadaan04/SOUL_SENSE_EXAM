# 🌐 Soul Sense Web Frontend

Welcome to the web client for the Soul Sense EQ Test. This application is built with **Next.js 14**, **Tailwind CSS**, and **Framer Motion**.

## 🚀 Getting Started

### Prerequisites

- **Node.js**: `v20.x` (LTS/Iron) is required. See [.nvmrc](.nvmrc).
- **Package Manager**: `npm` (configured via [.npmrc](.npmrc) for strict dependency management).

### Installation

1.  Navigate to the web directory:

    ```bash
    cd frontend-web
    ```

2.  Install dependencies:

    ```bash
    npm install
    ```

3.  Set up environment variables:

    ```bash
    cp .env.example .env.local
    ```

4.  Start development server:
    ```bash
    npm run dev
    ```
    The app will be available at [http://localhost:3005](http://localhost:3005).

---

## 🏗️ Architecture & Standards

This project follows a **domain-driven, feature-sliced** architecture. For full details on the directory structure and design decisions, please read:
👉 **[ADR 001: Frontend Architecture](file:///b:/Open_Source/soul_sence_Exam/SOUL_SENSE_EXAM/docs/architecture/001-frontend-structure.md)**

### Key Conventions

- **Absolute Imports**: Always use `@/` aliases (e.g., `@/components/ui/button`).
- **Barrel Files**: Directories contain an `index.ts` for clean named exports.
- **Strict Linting**: Architectural boundaries are enforced via `no-restricted-imports` rules.
- **Component Placement**:
  - Primitives go to `src/components/ui`
  - Structural elements to `src/components/layout`
  - Content sections to `src/components/sections`

### Quality Gates

Before submitting a PR, ensure these checks pass:

- `npm run lint`: Checks for architectural violations and code style.
- `npm run build`: Ensures the application compiles correctly.

---

## 🛠️ Tech Stack

- **Framework**: [Next.js](https://nextjs.org/) (App Router)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Animation**: [Framer Motion](https://www.framer.com/motion/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **UI Components**: [Radix UI](https://www.radix-ui.com/)
- **Forms**: [React Hook Form](https://react-hook-form.com/) + [Zod](https://zod.dev/)
