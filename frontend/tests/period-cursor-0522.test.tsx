import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, test } from "vitest";
import AcademicYearInput from "../src/components/AcademicYearInput";
import { RecordInput, RecordTextarea } from "../src/components/RecordTextInput";
import { copyAnnualGrant } from "../src/utils/annualGrant";
import { newProgramApplication } from "../src/utils/grantApplications";
import type { ParticipationInput } from "../src/types";

function TextHarness({ multiline = false, initial = "FIRST LINE\nLAST LINE" }) {
  const [value, setValue] = useState(initial);
  const Control = multiline ? RecordTextarea : RecordInput;
  return (
    <>
      <Control aria-label="Record text" value={value} onValueChange={setValue} />
      <output aria-label="Stored text">{value}</output>
    </>
  );
}

function typeAtSelection(control: HTMLInputElement | HTMLTextAreaElement, text: string) {
  const start = control.selectionStart!;
  const end = control.selectionEnd!;
  fireEvent.change(control, {
    target: {
      value: `${control.value.slice(0, start)}${text}${control.value.slice(end)}`,
      selectionStart: start + text.length,
      selectionEnd: start + text.length,
    },
  });
}

test("typing into an existing first line retains the cursor for the next character", () => {
  render(<TextHarness multiline />);
  const control = screen.getByLabelText("Record text") as HTMLTextAreaElement;
  control.focus();
  control.setSelectionRange(0, 0);
  typeAtSelection(control, "a");
  expect(control.value).toBe("AFIRST LINE\nLAST LINE");
  expect(control.selectionStart).toBe(1);
  expect(control.selectionEnd).toBe(1);
  typeAtSelection(control, "b");
  expect(control.value).toBe("ABFIRST LINE\nLAST LINE");
  expect(control.selectionStart).toBe(2);
  expect(screen.getByLabelText("Stored text").textContent).toBe("ABFIRST LINE\nLAST LINE");
});

test("replacement and Unicode uppercase expansion preserve the matching selection position", () => {
  render(<TextHarness initial="FIRST LAST" />);
  const control = screen.getByLabelText("Record text") as HTMLInputElement;
  control.focus();
  control.setSelectionRange(0, 5);
  typeAtSelection(control, "straße");
  expect(control.value).toBe("STRASSE LAST");
  expect(control.selectionStart).toBe(7);
  typeAtSelection(control, "x");
  expect(control.value).toBe("STRASSEX LAST");
  expect(control.selectionStart).toBe(8);
});

test("an edit that normalizes back to the previous value retains its caret", () => {
  render(<TextHarness initial="FIRST LAST" />);
  const control = screen.getByLabelText("Record text") as HTMLInputElement;
  control.focus();
  control.setSelectionRange(0, 1);
  typeAtSelection(control, "f");
  expect(control.value).toBe("FIRST LAST");
  expect(control.selectionStart).toBe(1);
  typeAtSelection(control, "x");
  expect(control.value).toBe("FXIRST LAST");
});

test("composition text stays intact until the composition finishes", () => {
  render(<TextHarness multiline initial={"FIRST\nLAST"} />);
  const control = screen.getByLabelText("Record text") as HTMLTextAreaElement;
  control.focus();
  control.setSelectionRange(0, 0);
  fireEvent.compositionStart(control);
  typeAtSelection(control, "é");
  expect(control.value).toBe("éFIRST\nLAST");
  fireEvent.compositionEnd(control);
  expect(control.value).toBe("ÉFIRST\nLAST");
  expect(control.selectionStart).toBe(1);
  typeAtSelection(control, "x");
  expect(control.value).toBe("ÉXFIRST\nLAST");
});

test("opening historical mixed-case text does not modify it until the user edits", () => {
  render(<TextHarness multiline initial={"Historical note\nOriginal second line"} />);
  const control = screen.getByLabelText("Record text") as HTMLTextAreaElement;
  expect(control.value).toBe("Historical note\nOriginal second line");
  fireEvent.focus(control);
  fireEvent.blur(control);
  expect(screen.getByLabelText("Stored text").textContent).toBe(
    "Historical note\nOriginal second line",
  );
});

test("single calendar years remain literal through typing and blur", () => {
  function PeriodHarness() {
    const [value, setValue] = useState("");
    return <AcademicYearInput aria-label="Program period" value={value} onValueChange={setValue} />;
  }
  render(<PeriodHarness />);
  const control = screen.getByLabelText("Program period") as HTMLInputElement;
  fireEvent.change(control, { target: { value: "2021" } });
  fireEvent.blur(control);
  expect(control.value).toBe("2021");
  fireEvent.change(control, { target: { value: "2021-2022" } });
  fireEvent.blur(control);
  expect(control.value).toBe("2021-2022");
});

test("annual copy advances a single calendar year without turning it into a range", () => {
  const original = {
    start_academic_year: "2021",
    end_academic_year: "2021",
  } as ParticipationInput;
  const next = copyAnnualGrant(original);
  expect(next.start_academic_year).toBe("2022");
  expect(next.end_academic_year).toBe("2022");
  expect(original.start_academic_year).toBe("2021");
});

test("annual funding copies retain the same application's recorded program deadline", () => {
  const original = {
    program_name: "MASTERS",
    start_date: "2021-06-01",
    start_academic_year: "2021",
    end_academic_year: "2021",
    allowed_duration_years: 3,
    completion_due_on: "2024-06-01",
    payback_payment_status: "Fully paid",
  } as ParticipationInput;
  expect(copyAnnualGrant(original)).toMatchObject({
    start_date: "2021-06-01",
    allowed_duration_years: 3,
    completion_due_on: "2024-06-01",
    payback_payment_status: null,
    start_academic_year: "2022",
  });
  expect(newProgramApplication(original)).toMatchObject({
    start_date: null,
    allowed_duration_years: null,
    completion_due_on: null,
    payback_payment_status: null,
  });
});

test("a repeat application retains single-year periods and clears its previous deadline and payments", () => {
  const original = {
    program_name: "CERTIFICATION",
    start_academic_year: "2021",
    end_academic_year: "2021",
    allowed_duration_years: 1,
    completion_due_on: "2022-01-01",
    payback_payment_status: "Fully paid",
  } as ParticipationInput;
  const repeat = newProgramApplication(original);
  expect(repeat).toMatchObject({
    start_academic_year: "2022",
    end_academic_year: "2022",
    allowed_duration_years: null,
    completion_due_on: null,
    payback_payment_status: null,
  });
  expect(original.completion_due_on).toBe("2022-01-01");
});

test("a repeat application preserves single years independently from explicit academic-year ranges", () => {
  const original = {
    program_name: "ENHANCEMENT",
    start_academic_year: "2021",
    end_academic_year: "2021-2022",
  } as ParticipationInput;
  expect(newProgramApplication(original)).toMatchObject({
    start_academic_year: "2022",
    end_academic_year: "2022-2023",
  });
});
