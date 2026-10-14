import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ScholarHistory from "../src/components/ScholarHistory";
import BackupReviewPanel from "../src/components/BackupReviewPanel";
import type { MaintenanceStatus } from "../src/types";

const history=vi.hoisted(()=>({getScholarHistory:vi.fn()}));
const maintenance=vi.hoisted(()=>({recordBackupReview:vi.fn()}));
vi.mock("../src/api/fsdp",()=>history);
vi.mock("../src/api/maintenance",()=>maintenance);
beforeEach(()=>vi.resetAllMocks());

test("history loads only when expanded and supports recovery from errors",async()=>{
  history.getScholarHistory.mockRejectedValueOnce(new Error("History unavailable")).mockResolvedValue({items:[],total:0,page:1,page_size:20});
  render(<ScholarHistory scholarId={3}/>);
  expect(history.getScholarHistory).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"Change history"}));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button",{name:"Retry"}));
  await screen.findByText("No attributable changes recorded.");
  expect(history.getScholarHistory).toHaveBeenCalledWith(3,1);
});

const status:MaintenanceStatus={database_status:"healthy",database_file:"cathedra.db",database_size_bytes:1,fsdp_records:0,backup_count:1,latest_backup_at:null,backup_retention:null,backups:[{filename:"cathedra-backup-example.db",created_at:"2026-10-03T00:00:00Z",size_bytes:1,protected:true}]};

test("recovery review requires explicit copy confirmation and retains it on failure",async()=>{
  maintenance.recordBackupReview.mockRejectedValueOnce(new Error("Review failed")).mockResolvedValue({recorded:true});
  const reload=vi.fn().mockResolvedValue(undefined);
  render(<BackupReviewPanel status={status} reload={reload} disabled={false}/>);
  const save=screen.getByRole("button",{name:"Record recovery review"});
  expect(save.hasAttribute("disabled")).toBe(true);
  fireEvent.change(screen.getByLabelText("Backup reviewed"),{target:{value:status.backups[0].filename}});
  expect(save.hasAttribute("disabled")).toBe(true);
  const copy=screen.getByRole("checkbox",{name:"I copied this backup to private off-device storage."});
  fireEvent.click(copy);
  fireEvent.click(save);
  await screen.findByText("Review failed");
  expect((copy as HTMLInputElement).checked).toBe(true);
  fireEvent.click(save);
  await waitFor(()=>expect(reload).toHaveBeenCalledTimes(1));
  expect(maintenance.recordBackupReview).toHaveBeenLastCalledWith(status.backups[0].filename,false);
  expect((copy as HTMLInputElement).checked).toBe(false);
});
