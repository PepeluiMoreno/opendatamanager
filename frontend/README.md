# OpenDataManager Frontend

Vue 3 + Vite + Tailwind CSS frontend for managing OpenData  resources.

## Setup

### Prerequisites

Node.js 18+ must be installed. Download from: https://nodejs.org/

### Installation

```powershell
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Features

- **Dashboard**: Overview of system stats and quick actions
- **Resources**: Full CRUD management of data resources with dynamic forms
- **Resource Test**: Live execution and testing of resources with JSON result viewer
- **Fetcher**: View available fetcher implementations
- **Applications**: Manage subscribed applications and their project subscriptions

## Tech Stack

- **Vue 3** (Composition API)
- **Vite** (Build tool)
- **Tailwind CSS** (Styling)
- **Vue Router** (Navigation)
- **graphql-request** (GraphQL client)

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── graphql.js           # GraphQL client and queries
│   ├── assets/
│   │   └── styles.css           # Global styles with Tailwind
│   ├── components/
│   │   └── Sidebar.vue          # Navigation sidebar
│   ├── views/
│   │   ├── Dashboard.vue        # Main dashboard
│   │   ├──  Resources.vue          #  Resources management
│   │   ├── SourceTest.vue       # Test source execution
│   │   ├── Fetchers.vue     # View fetcher types
│   │   └── Applications.vue     # Applications management
│   ├── router/
│   │   └── index.js             # Vue Router config
│   ├── App.vue                  # Root component
│   └── main.js                  # App entry point
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Backend Connection

The frontend connects to the GraphQL API at `http://localhost:8040/graphql`.

Make sure the backend server is running before starting the frontend:

```powershell
cd ..
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8040 --reload
```

## Development

The Vite dev server runs on `http://localhost:5173` with hot module replacement.

All GraphQL queries and mutations are defined in `src/api/graphql.js`.

## Design

- **Dark mode** UI with VS Code-inspired aesthetics
- **JetBrains Mono** font for technical/developer feel
- **Tailwind CSS** for utility-first styling
- **Responsive** layout with sidebar navigation
