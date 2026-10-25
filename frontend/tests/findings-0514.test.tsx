import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import ProgramGrantHistory, { groupAnnualGrants } from "../src/components/ProgramGrantHistory";
import { copyAnnualGrant } from "../src/utils/annualGrant";
import { personnelType } from "../src/utils/colleges";
import type { ParticipationRead } from "../src/types";
const grant: ParticipationRead = {
  id: 1,
  program_id: 5,
  name: "Ph.D. Computing",
  delivering_hei: "University",
  start_date: null,
  end_date: null,
  start_term: "1st",
  start_academic_year: "2021-2022",
  end_term: "3rd",
  end_academic_year: "2021-2022",
  grant_type: "Full Scholarship",
  grant_other: null,
  status: "On Going",
  extension: null,
  remarks: "First year note",
};

test("annual history groups by program identity and retains independently expandable years", () => {
  const grants = [
    grant,
    { ...grant, id: 2, start_academic_year: "2022-2023", grant_type: "Partial Scholarship" },
    {
      ...grant,
      id: 3,
      start_academic_year: "2023-2024",
      grant_type: "Thesis Aid",
      status: "Graduated",
    },
    { ...grant, id: 4, program_id: 6, name: "Other program" },
  ];
  expect(groupAnnualGrants(grants)[0].map((item) => item.id)).toEqual([3, 2, 1]);
  const { container } = render(<ProgramGrantHistory grants={grants} />);
  const programs = container.querySelectorAll<HTMLDetailsElement>(".program-history");
  expect(programs.length).toBe(2);
  expect(programs[0].open).toBe(true);
  // Browser-native details controls support keyboard and pointer activation.
  programs[0].open = true;
  fireEvent(programs[0], new Event("toggle"));
  expect(screen.getByText("2023-2024")).toBeTruthy();
  expect(screen.getByText(/Partial Scholarship/)).toBeTruthy();
  const annual = programs[0].querySelectorAll<HTMLDetailsElement>(".annual-grant")[1];
  expect(annual.open).toBe(false);
  annual.open = true;
  fireEvent(annual, new Event("toggle"));
  window.dispatchEvent(new Event("beforeprint"));
  expect(
    Array.from(container.querySelectorAll<HTMLDetailsElement>("details")).every(
      (item) => item.open,
    ),
  ).toBe(true);
  window.dispatchEvent(new Event("afterprint"));
  expect(programs[0].open).toBe(true);
  expect(programs[1].open).toBe(false);
  expect(annual.open).toBe(true);
});

test("next-year draft keeps program but resets outcome and dates while retaining remarks without mutating original", () => {
  const original = {
    ...grant,
    program_name: grant.name,
    source_program_id: 5,
    delivering_hei: "University",
    start_term: "1st",
    end_term: "3rd",
    start_academic_year: "2021-2022",
    end_academic_year: "2021-2022",
    grant_other: "",
    extension: "Old extension",
    status: "Graduated",
    remarks: "Graduated in 2022",
    contract_completed_on: "2021-03-01",
  };
  const copy = copyAnnualGrant(original);
  expect(copy.source_program_id).toBe(5);
  expect(copy.program_name).toBe(original.program_name);
  expect(copy.start_academic_year).toBe("2022-2023");
  expect(copy.end_academic_year).toBe("2022-2023");
  expect(copy.id).toBeUndefined();
  expect(copy.status).toBe("On Going");
  expect(copy.remarks).toBe(original.remarks);
  expect(copy.contract_completed_on).toBeNull();
  expect(original.remarks).toBe("Graduated in 2022");
  expect(
    copyAnnualGrant({ ...original, start_academic_year: "Not recorded" }).start_academic_year,
  ).toBe("Not recorded");
});

test("affiliation automatically determines personnel including missing information", () => {
  expect(personnelType("COE")).toBe("Faculty");
  expect(personnelType("COED")).toBe("Faculty");
  expect(personnelType("Staff Talisay")).toBe("Staff");
  expect(personnelType("")).toBe("Unknown");
  expect(personnelType(null)).toBe("Unknown");
});

test("a program's summary uses the latest term before the grant ID", () => {
  const rows = groupAnnualGrants([
    { ...grant, id: 10, start_term: "1st", status: "Graduated" },
    { ...grant, id: 2, start_term: "3rd", status: "On Going" },
  ]);
  expect(rows[0][0].status).toBe("On Going");
});
