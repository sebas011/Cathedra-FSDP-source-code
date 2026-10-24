import PageHeading from "../components/PageHeading";
import OfficeLogPanel from "../components/OfficeLogPanel";

export default function OfficeLogPage() {
  return (
    <div className="stack-md management-page office-log-page">
      <PageHeading title="Office log" eyebrow="OFFICE OPERATIONS" />
      <OfficeLogPanel />
    </div>
  );
}
