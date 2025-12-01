# IPA Platform Frontend

Modern React frontend for the Intelligent Process Automation Platform.

## Tech Stack

- **Framework**: React 18 + TypeScript 5
- **Build Tool**: Vite 5
- **Styling**: TailwindCSS 3 + Shadcn/ui
- **State Management**: Zustand + TanStack Query
- **Routing**: React Router 6
- **Charts**: Recharts

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm run test
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
VITE_API_URL=/api/v1
```

## Project Structure

```
src/
├── api/                 # API client and hooks
├── components/
│   ├── ui/             # Shadcn/ui components
│   ├── layout/         # Layout components
│   └── shared/         # Shared business components
├── hooks/              # Custom React hooks
├── lib/                # Utility functions
├── pages/              # Page components
│   ├── dashboard/
│   ├── workflows/
│   ├── agents/
│   ├── approvals/
│   ├── audit/
│   └── templates/
├── store/              # Zustand stores
└── types/              # TypeScript types
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run test` | Run unit tests |
| `npm run test:e2e` | Run E2E tests |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | Type check |

## Pages

| Route | Description |
|-------|-------------|
| `/dashboard` | System overview and metrics |
| `/workflows` | Workflow management |
| `/workflows/:id` | Workflow details |
| `/agents` | Agent management |
| `/agents/:id` | Agent details and testing |
| `/templates` | Template marketplace |
| `/approvals` | Approval workbench |
| `/audit` | Audit logs |

## Sprint 5 Features

- Dashboard with key metrics and charts
- Workflow list and detail views
- Agent management and testing
- Template marketplace
- Approval workbench
- Audit log viewer

---

**Sprint**: 5 - Frontend UI
**Version**: 0.1.0
