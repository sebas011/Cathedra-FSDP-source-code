import PageHeading from "../components/PageHeading";
import OfficeLogPanel from "../components/OfficeLogPanel";

export default function OfficeLogPage() {
  return (
    <div className="stack-md">
      <PageHeading title="Office log" />
      <OfficeLogPanel />
    </div>
  );
}
