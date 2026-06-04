# Pharabius Platform Frontend

## Commands

| Command | Description |
|---------|-------------|
| `npm install` | Install dependencies |
| `npm test` | Run frontend tests (Vitest) |
| `npm run test:watch` | Run tests in watch mode |
| `npm run build` | TypeScript check + production build (`tsc && vite build`) |
| `npm run dev` | Development server (port 3000, proxies `/api` to port 8000) |

## Test Setup

- **Runner**: Vitest with jsdom environment
- **Libraries**: React Testing Library, jest-dom matchers, user-event
- **Config**: `vitest.config.ts`
- **Setup**: `src/test/setup.ts` (jest-dom matchers + cleanup)
- **Helpers**: `src/test/test-utils.tsx` (`renderWithRouter`)
- **Fixtures**: `src/test/api-mocks.ts` (DTO factories)

## Adding Tests

Place test files alongside the component they test:

```
src/views/WorkPackages.tsx
src/views/WorkPackages.test.tsx

src/components/EvidenceChip.tsx
src/components/EvidenceChip.test.tsx
```

Use `vi.hoisted()` for mock functions to ensure they're available when `vi.mock()` is hoisted:

```ts
const { mockFn } = vi.hoisted(() => ({
  mockFn: vi.fn(),
}));

vi.mock("../api/client", () => ({
  myFunction: mockFn,
}));
```

Mock API functions from `../api/client` directly. No MSW or network mocking.

## Validation Gate

Every frontend change should pass:

1. `npm test` — all frontend tests green
2. `npm run build` — TypeScript + Vite build clean

These do not verify run-context behavior or user-visible states.
For routes and navigation, add component tests.
For visual correctness, use manual verification.
