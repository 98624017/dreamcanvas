(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

const filterMessage = (message: unknown) =>
  typeof message === "string" && message.includes("ReactDOMTestUtils.act is deprecated");

const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  if (filterMessage(args[0])) {
    return;
  }
  originalConsoleError(...args);
};

const originalConsoleWarn = console.warn;
console.warn = (...args: unknown[]) => {
  if (filterMessage(args[0])) {
    return;
  }
  originalConsoleWarn(...args);
};

const originalStderrWrite = process.stderr.write.bind(process.stderr);
process.stderr.write = ((chunk: any, encoding?: any, callback?: any) => {
  const text = typeof chunk === "string" ? chunk : chunk?.toString?.();
  if (text && text.includes("ReactDOMTestUtils.act is deprecated")) {
    return true;
  }
  return originalStderrWrite(chunk, encoding, callback);
}) as typeof process.stderr.write;

import { vi } from "vitest";

vi.mock("@/modules/system/backendClient", async () => {
  const mod = await import("@/modules/system/components/__mocks__/backendClient");
  return mod;
});
