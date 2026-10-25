import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AssessmentDetails from "../src/components/AssessmentDetails";
import ProgramGrantHistory from "../src/components/ProgramGrantHistory";
import PaybackFollowUp from "../src/components/PaybackFollowUp";
import { localToday, formatRecordDateTime } from "../src/utils/dates";
import type { ParticipationRead } from "../src/types";

const api = vi.hoisted(() => ({ getPayback: vi.fn(), downloadPayback: vi.fn() }));
vi.mock("../src/api/payback", () => api);
beforeEach(() => vi.resetAllMocks());

const grant: ParticipationRead = {
  id: 1,
  program_id: 1,
  name: "EXAMPLE PROGRAM",
  delivering_hei: "EXAMPLE UNIVERSITY",
  start_date: null,
  end_date: null,
  start_term: "Summer",
  start_academic_year: "2021",
  end_term: null,
  end_academic_year: null,
  grant_type: "Thesis Aid",
  grant_other: null,
  status: "Payback",
  extension: null,
  remarks: null,
  payback_attention: "Recorded Payback",
  assessment_rule: "CONTRACT_RECORDED_PAYBACK",
  assessment_reason: "Payback was recorded by the office.",
  assessment_as_of: "2026-10-25",
  completion_deadline_source: "Explicit deadline",
};

test("profile shows factual assessment details without exposing internal rule codes", () => {
  render(<ProgramGrantHistory grants={[grant]} />);
  const summary = screen.getByText("Assessment details");
  expect(summary.closest("details")?.open).toBe(false);
  fireEvent.click(summary);
  expect(summary.closest("details")?.open).toBe(true);
  expect(screen.getByText(grant.assessment_reason!)).toBeTruthy();
  expect(screen.getByText("2026-10-25")).toBeTruthy();
  expect(screen.getByText("Explicit deadline")).toBeTruthy();
  expect(screen.queryByText(grant.assessment_rule!)).toBeNull();
});

test("older results without an explanation do not invent one", () => {
  render(<AssessmentDetails assessedOn="2026-10-25" />);
  expect(screen.queryByText("Assessment details")).toBeNull();
});

test("dashboard follow-up exposes the same explanation and preserves its recorded category", async () => {
  api.getPayback.mockResolvedValue({
    as_of: "2026-10-25",
    total: 1,
    scholar_counts: { "Recorded Payback": 1 },
    grant_counts: {},
    items: [
      {
        scholar_id: 1,
        scholar_name: "EXAMPLE SCHOLAR",
        department: "CAS",
        participation_id: 1,
        program_name: grant.name,
        academic_year: "2021",
        recorded_status: "Payback",
        attention: "Recorded Payback",
        contract_completed_on: null,
        grace_ends_on: null,
        days_remaining: null,
        assessment_reason: grant.assessment_reason,
        completion_deadline_source: "Explicit deadline",
      },
    ],
  });
  render(
    <MemoryRouter>
      <PaybackFollowUp />
    </MemoryRouter>,
  );
  const summary = await screen.findByText("Assessment details");
  fireEvent.click(summary);
  expect(screen.getByText(grant.assessment_reason!)).toBeTruthy();
  expect(screen.getByText("2026-10-25")).toBeTruthy();
  expect(api.downloadPayback).not.toHaveBeenCalled();
});

test("business dates and naive UTC history timestamps share Philippine time", () => {
  expect(localToday(new Date("2026-10-25T15:59:59Z"))).toBe("2026-10-25");
  expect(localToday(new Date("2026-10-25T16:00:00Z"))).toBe("2026-10-26");
  expect(formatRecordDateTime("2026-10-24 16:01:00", "en-GB")).toBe(
    formatRecordDateTime("2026-10-25T00:01:00+08:00", "en-GB"),
  );
  expect(formatRecordDateTime("2026-10-24 16:01:00", "en-GB")).toContain("25 Oct 2026");
  expect(formatRecordDateTime("damaged time")).toBe("Not recorded");
});
