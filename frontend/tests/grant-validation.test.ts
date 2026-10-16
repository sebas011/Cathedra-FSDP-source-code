import { expect, test } from "vitest";
import type { ParticipationInput } from "../src/types";
import { canonicalTerm, validateGrant } from "../src/utils/grantValidation";

const grant = (): ParticipationInput => ({
  program_name: "Synthetic program",
  delivering_hei: "",
  start_date: null,
  end_date: null,
  start_term: "",
  start_academic_year: "",
  end_term: "",
  end_academic_year: "",
  grant_type: null,
  grant_other: "",
  status: "On Going",
  extension: "",
  remarks: "",
});

test("partial and historical academic periods are accepted", () => {
  expect(validateGrant({ ...grant(), start_term: "1st", start_academic_year: "2026-2028" })).toBe(
    "",
  );
  expect(validateGrant({ ...grant(), start_term: "1st", start_academic_year: "2026-2027" })).toBe(
    "",
  );
});
test("recorded period order does not block a grant", () => {
  expect(
    validateGrant({
      ...grant(),
      start_term: "2nd",
      start_academic_year: "2026-2027",
      end_term: "1st",
      end_academic_year: "2026-2027",
    }),
  ).toBe("");
});
test("term aliases normalize without discarding historical custom terms", () => {
  expect(canonicalTerm("1st Semester")).toBe("1st");
  expect(canonicalTerm("summer")).toBe("Summer");
  expect(validateGrant({ ...grant(), start_term: "Historical term" })).toBe(
    "Choose 1st, 2nd, 3rd or Summer.",
  );
});

test("Program Applied is the only required grant field", () => {
  expect(validateGrant({ ...grant(), program_name: "   " })).toBe("Program Applied is required.");
  expect(
    validateGrant({ ...grant(), grant_type: "Others", grant_other: "", end_date: "2026-01-01" }),
  ).toBe("");
});
