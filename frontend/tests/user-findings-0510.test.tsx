import { useState } from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expect, test } from "vitest";
import EducationSection from "../src/components/EducationSection";
import type { EducationInput } from "../src/types";

function Editor() {
  const [entries, setEntries] = useState<EducationInput[]>([
    {
      id: 1,
      degree: "BS",
      level: "Bachelor’s",
      institution: "University",
      graduation_year: "2010",
    },
  ]);
  const [draft, setDraft] = useState<EducationInput | null>(null);
  return (
    <>
      <EducationSection entries={entries} onChange={setEntries} onDraftChange={setDraft} />
      <output aria-label="Open education draft">{draft ? "Open" : "Closed"}</output>
    </>
  );
}

test("education editor stages entries, edits existing rows and keeps saved rows on cancellation", async () => {
  render(<Editor />);
  expect(screen.queryByLabelText("Degree", { exact: true })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Add education" }));
  await screen.findByRole("region", { name: "Education editor" });
  fireEvent.change(screen.getByLabelText("Degree", { exact: true }), {
    target: { value: "Master of Science" },
  });
  expect(
    within(screen.getByRole("region", { name: "Scholar education" })).queryByText(
      "MASTER OF SCIENCE",
    ),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Save education" }));
  expect(screen.getByText("MASTER OF SCIENCE")).toBeTruthy();
  expect(screen.getByLabelText("Open education draft").textContent).toBe("Closed");
  fireEvent.click(screen.getByRole("button", { name: "Edit education 2" }));
  await screen.findByLabelText("Degree", { exact: true });
  fireEvent.change(screen.getByLabelText("Graduation year", { exact: true }), {
    target: { value: "2026" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Update education" }));
  expect(screen.getByText("2026")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Add education" }));
  await screen.findByLabelText("Degree", { exact: true });
  fireEvent.change(screen.getByLabelText("Degree", { exact: true }), {
    target: { value: "Discarded draft" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Cancel education" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Discard changes" }));
  await waitFor(() =>
    expect(screen.queryByRole("region", { name: "Education editor" })).toBeNull(),
  );
  expect(screen.getByText("MASTER OF SCIENCE")).toBeTruthy();
  expect(screen.queryByText("DISCARDED DRAFT")).toBeNull();
});
