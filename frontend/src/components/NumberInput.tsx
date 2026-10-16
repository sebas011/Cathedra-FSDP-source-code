import { useEffect, useRef, type InputHTMLAttributes } from "react";

/** Keep keyboard number controls while preventing an accidental wheel change. */
export default function NumberInput(props: Omit<InputHTMLAttributes<HTMLInputElement>, "type">) {
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const element = input.current;
    const preventChange = (event: WheelEvent) => {
      if (document.activeElement === element) event.preventDefault();
    };
    element?.addEventListener("wheel", preventChange, { passive: false });
    return () => element?.removeEventListener("wheel", preventChange);
  }, []);
  return <input {...props} ref={input} type="number" />;
}
