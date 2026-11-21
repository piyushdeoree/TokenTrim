# TokenTrim Frontend

The TokenTrim frontend is a Next.js and TypeScript application that provides the user interface for the TokenTrim AI Cost Intelligence and Prompt Optimization Platform.

It allows users to analyze and optimize prompts, review token usage, estimate LLM costs, compare model pricing, and manage provider integrations through a web interface.

## 1. Features

### Prompt Analysis and Optimization
- Submit prompts for analysis and optimization.
- Display prompt analysis results.
- Present original and optimized prompt information.
- Show token usage and potential cost savings.

### AI Cost Intelligence
- Display estimated LLM costs.
- Present original versus optimized cost comparisons.
- Format small monetary values with appropriate precision.
- Support multiple display currencies.

### Compare Across LLMs
- Compare estimated prompt costs across supported models.
- Display original and optimized cost estimates.
- Present pricing-based comparisons using backend Cost Engine results.
- Identify the lowest-cost eligible model based on available verified pricing.

### BYOK Integration
- Support Bring Your Own Key (BYOK) workflows.
- Allow users to work with supported provider credentials.
- Display provider execution information and results.
- Keep credential handling within the backend integration rather than exposing stored credentials in the interface.

### Currency Selection
The frontend supports the following display currencies:

- USD — US Dollar
- INR — Indian Rupee
- EUR — Euro
- GBP — British Pound
- JPY — Japanese Yen
- CAD — Canadian Dollar
- AUD — Australian Dollar

Currency conversion uses configured reference rates. These are not live foreign-exchange rates.

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Next.js | Frontend framework |
| React | UI components |
| TypeScript | Type-safe application development |
| CSS / frontend styling | User interface presentation |
| Jest / frontend test tooling | Component and unit testing |
| ESLint | Code quality and linting |
| npm | Dependency management and scripts |

## 3. Project Structure

The frontend source code is organized into the following areas:

```text
frontend/
├── src/
│   ├── components/
│   │   └── token-trim/
│   ├── context/
│   ├── hooks/
│   ├── pages/
│   ├── services/
│   ├── types/
│   └── utils/
├── tests/
│   ├── components/
│   └── unit/
├── public/
├── package.json
└── README.md
```

### Main directories

- `components/` — Reusable UI components and TokenTrim feature components.
- `context/` — Shared application state and context providers.
- `hooks/` — Reusable React hooks.
- `pages/` — Application pages and routing.
- `services/` — API communication and frontend service logic.
- `types/` — TypeScript interfaces and type definitions.
- `utils/` — Formatting and utility functions.
- `tests/` — Component and unit tests.

## 4. Installation

### Prerequisites

- Node.js
- npm
- A running TokenTrim backend

### Clone the repository

```bash
git clone <repository-url>
cd TokenTrim
```

### Navigate to the frontend

```bash
cd frontend
```

### Install dependencies

```bash
npm install
```

## 5. Environment Configuration

The frontend communicates with the TokenTrim backend through its configured API service.

Configure the backend API address using the environment-variable name expected by the existing frontend configuration. Do not commit private credentials, API keys, or other secrets.

Refer to the frontend configuration and service files for the exact environment-variable names and expected values.

## 6. Running the Application

Start the development server:

```bash
npm run dev
```

Open the local frontend address shown in the terminal, typically:

```text
http://localhost:3000
```

Ensure the backend is running and accessible before testing features that require API communication.

## 7. Validation and Testing

Run the available frontend checks from the `frontend/` directory.

### Run tests

```bash
npm test
```

### TypeScript validation

```bash
npx tsc --noEmit
```

### ESLint

```bash
npm run lint
```

### Production build

```bash
npm run build
```

A successful production build confirms that the application can be compiled for deployment. Resolve build errors before deployment.

## 8. Backend Integration

The frontend integrates with the TokenTrim backend for application functionality such as:

- User authentication and application data.
- Prompt analysis and optimization.
- Cost estimation and model comparisons.
- Provider credential management.
- LLM provider execution.
- Cost and usage information.

The backend is responsible for API processing, database operations, provider communication, and Cost Engine integration.

## 9. Cost Comparison and Currency Handling

The Compare Across LLMs interface uses backend-provided cost comparison results.

The frontend displays original and optimized cost estimates for supported models. Pricing eligibility and cost calculations are handled by the backend and Cost Engine.

Currency selection changes the monetary display using configured reference conversion rates. The application does not represent these rates as live market exchange rates.

## 10. Development Guidelines

- Use TypeScript for new frontend functionality.
- Prefer reusable components over duplicated UI code.
- Keep API communication within the service layer.
- Use shared context for application-wide state where appropriate.
- Add or update tests when modifying components or utility functions.
- Run linting, TypeScript validation, tests, and the production build before submitting changes.
- Never commit API keys, credentials, or environment files containing secrets.

## 11. Build for Production

Create an optimized production build:

```bash
npm run build
```

Start the production server using:

```bash
npm start
```

The frontend must be configured with the correct backend API address for the deployment environment.

## 12. Team Responsibility

The frontend is maintained by the frontend development team.

Responsibilities include:

- User interface development.
- Frontend application architecture.
- API integration.
- Authentication and application workflows.
- Cost comparison and currency presentation.
- BYOK user interface integration.
- Component testing and frontend quality checks.

---

**TokenTrim — AI Cost Intelligence & Prompt Optimization Platform**

Frontend application built with Next.js, React, and TypeScript.
