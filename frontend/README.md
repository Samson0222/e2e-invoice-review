# Invoice Review Frontend

The frontend for Northstar Facilities B.V. Invoice Review application, built with React 19, TypeScript, Vite, and Tailwind CSS.

## Features

- **Guided Workflow**: Welcome portal $\rightarrow$ Document Upload $\rightarrow$ Live Processing $\rightarrow$ Review & Approval loop.
- **Document Preview & Extraction Review**: Side-by-side original PDF/image preview alongside extracted invoice/receipt metadata.
- **Provenance & Conflict Highlighting**: Visual indicators distinguishing primary Azure AI Document Intelligence extractions from Azure OpenAI fallbacks and rule validation status.
- **Interactive Corrections & GL Categorization**: Field editing capabilities, error clearing, and General Ledger (GL) account suggestion and manual override.
- **Correction Email Drafting**: On-demand generator for supplier correction emails with one-click copy functionality.
- **Document History Inbox**: Filterable inbox of processed invoices and receipts with status indicators and local deletion affordance.

## Tech Stack

- **Framework**: React 19, TypeScript (Strict mode)
- **Styling**: Tailwind CSS v4
- **Build Tool**: Vite 8
- **Package Manager**: pnpm (strict frozen lockfile)

## Getting Started

### Prerequisites

- Node.js 20+
- pnpm `11.3.0` installed globally or via corepack

### Installation & Running

1. Install dependencies:
   ```bash
   pnpm install --frozen-lockfile
   ```

2. Setup environment variables (if non-default backend port):
   ```bash
   cp .env.example .env
   ```

3. Start the development server:
   ```bash
   pnpm dev
   ```
   The application will be accessible at `http://localhost:5173`.

## Available Scripts

- `pnpm dev`: Starts the Vite development server.
- `pnpm build`: Runs TypeScript check (`tsc -b`) and builds the production assets into `dist/`.
- `pnpm lint`: Runs ESLint across the project.
- `pnpm preview`: Previews the production build locally.

## Project Structure

```text
src/
├── components/          # React UI components (DocumentReview, DocumentInbox, etc.)
│   └── ui/              # Base UI elements
├── lib/                 # Utility functions and API client (`api.ts`, `env.ts`)
├── App.tsx              # Main application shell and state orchestration
├── main.tsx             # Entry point
└── index.css            # Styling & Tailwind setup
```

