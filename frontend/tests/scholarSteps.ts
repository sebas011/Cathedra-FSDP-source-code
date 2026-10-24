import { fireEvent, screen } from "@testing-library/react";

export function scholarStep(step: number) {
  fireEvent.click(screen.getByRole("button", { name: new RegExp(`^Step ${step}:`) }));
}

export function saveScholarForm() {
  scholarStep(4);
  fireEvent.click(screen.getByRole("button", { name: "Save Scholar" }));
}
