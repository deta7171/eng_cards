import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  // vitest.config.ts runs without `globals: true`, so @testing-library/react's
  // own auto-cleanup (which hooks the global afterEach) never registers -
  // without this, DOM from earlier tests in the same file stays mounted and
  // later tests' screen.getByText() queries can match stale elements.
  cleanup();
  server.resetHandlers();
  localStorage.clear();
});
afterAll(() => server.close());
