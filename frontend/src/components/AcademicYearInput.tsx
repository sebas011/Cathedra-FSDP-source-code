import type { InputHTMLAttributes } from "react";
import { formatAcademicYear } from "../utils/dates";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> & { value: string; onValueChange: (value: string) => void };
export default function AcademicYearInput({ value, onValueChange, onBlur, ...props }: Props) {
  return <input {...props} value={value} onChange={event => onValueChange(formatAcademicYear(event.target.value))}
    onBlur={event => { onValueChange(formatAcademicYear(event.target.value, true)); onBlur?.(event); }} />;
}
