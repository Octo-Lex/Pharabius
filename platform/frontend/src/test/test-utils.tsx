import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactElement } from "react";

export function renderWithRouter(
  ui: ReactElement,
  { route = "/" }: { route?: string } = {},
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
    ),
    ...options,
  });
}
