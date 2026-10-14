import type { Blocker } from "react-router-dom";
import ConfirmationDialog from "./ConfirmationDialog";

export default function UnsavedChangesDialog({ blocker, pending = false, pendingTitle = "Saving your changes", pendingDescription = "A save is still being processed. Wait for confirmation before leaving; leaving does not cancel a submitted save." }: { blocker: Blocker; pending?: boolean; pendingTitle?: string; pendingDescription?: string }) {
  return <ConfirmationDialog open={blocker.state === "blocked"} title={pending ? pendingTitle : "Keep your changes?"} description={pending ? pendingDescription : "Your edits have not been saved. Stay here to finish, or leave and discard them."} cancelLabel={pending ? "Stay here" : "Stay and keep editing"} confirmLabel="Leave without saving" confirmDisabled={pending} onCancel={() => blocker.reset?.()} onConfirm={() => { if (!pending) blocker.proceed?.(); }} />;
}
