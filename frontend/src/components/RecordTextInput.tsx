import { useRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { recordText } from "../utils/recordText";

type RecordControl = HTMLInputElement | HTMLTextAreaElement;

/** Update the DOM before React restores a controlled value, retaining the user's selection. */
function uppercaseAtSelection(control: RecordControl) {
  const before = control.value;
  const next = recordText(before);
  if (next === before) return next;
  const start = control.selectionStart;
  const end = control.selectionEnd;
  const direction = control.selectionDirection;
  control.value = next;
  if (start !== null && end !== null) {
    control.setSelectionRange(
      recordText(before.slice(0, start)).length,
      recordText(before.slice(0, end)).length,
      direction ?? undefined,
    );
  }
  return next;
}

function useRecordTextChange(onValueChange: (value: string) => void) {
  const composing = useRef(false);
  return {
    onCompositionStart: () => {
      composing.current = true;
    },
    onCompositionEnd: (event: { currentTarget: RecordControl }) => {
      composing.current = false;
      onValueChange(uppercaseAtSelection(event.currentTarget));
    },
    onChange: (event: { currentTarget: RecordControl; nativeEvent: Event }) => {
      const inComposition = composing.current || (event.nativeEvent as InputEvent).isComposing;
      onValueChange(
        inComposition ? event.currentTarget.value : uppercaseAtSelection(event.currentTarget),
      );
    },
  };
}

type RecordInputProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "value" | "onChange" | "onCompositionStart" | "onCompositionEnd"
> & {
  value: string;
  onValueChange: (value: string) => void;
};

export function RecordInput({ value, onValueChange, ...props }: RecordInputProps) {
  const changes = useRecordTextChange(onValueChange);
  return <input {...props} value={value} {...changes} />;
}

type RecordTextareaProps = Omit<
  TextareaHTMLAttributes<HTMLTextAreaElement>,
  "value" | "onChange" | "onCompositionStart" | "onCompositionEnd"
> & {
  value: string;
  onValueChange: (value: string) => void;
};

export function RecordTextarea({ value, onValueChange, ...props }: RecordTextareaProps) {
  const changes = useRecordTextChange(onValueChange);
  return <textarea {...props} value={value} {...changes} />;
}
