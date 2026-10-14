import { beforeEach, expect, test, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import axe from "axe-core";
import FsdpDashboardPage from "../src/pages/FsdpDashboardPage";
import FsdpListPage from "../src/pages/FsdpListPage";
import FsdpFormPage from "../src/pages/FsdpFormPage";
import FsdpDetailPage from "../src/pages/FsdpDetailPage";
import BackupExportPage from "../src/pages/BackupExportPage";
import { administrator, scholar } from "./fixtures";

const api=vi.hoisted(()=>Object.fromEntries(["getFsdpAnalytics","getFsdpRecords","getFsdpSummary","getFsdpRecord","getMaintenanceStatus","getCurrentUser","clearSession","createDatabaseBackup","deleteDatabaseBackup","downloadDatabaseBackup","downloadExport","restoreDatabase","setBackupProtection"].map(name=>[name,vi.fn()])));
vi.mock("../src/api/officeLog",()=>({getOfficeLogs:async()=>({items:[],total:0,page:1,page_size:50})}));
vi.mock("../src/api",()=>api);
beforeEach(()=>{
  vi.resetAllMocks();
  api.getCurrentUser.mockReturnValue(administrator);
  api.getFsdpRecord.mockResolvedValue(scholar);
  api.getFsdpRecords.mockResolvedValue({items:[scholar],total:1,page:1,page_size:50});
  api.getFsdpSummary.mockResolvedValue({total:1,ongoing:0,graduated:0,payback:0,withdrawn:0,missing_requirements:0});
  api.getFsdpAnalytics.mockResolvedValue({scholars:1,grants:0,ongoing_scholars:0,requirements_follow_up:0,statuses:[],grant_types:[],departments:[],recent_scholars:[scholar],options:{departments:[],start_academic_years:[]}});
  api.getMaintenanceStatus.mockResolvedValue({database_status:"healthy",database_file:"cathedra.db",database_size_bytes:1,fsdp_records:1,backup_count:0,latest_backup_at:null,backup_retention:null,backups:[],backup_due:true});
});
const rules=["button-name","link-name","label","aria-valid-attr","aria-valid-attr-value","aria-required-attr","aria-roles","heading-order","table-duplicate-name","td-headers-attr","image-alt"];
for(const [name,element,path,url] of [
  ["Dashboard",<FsdpDashboardPage/>,"*","/"],
  ["Directory",<FsdpListPage/>,"*","/fsdp"],
  ["Editor",<FsdpFormPage/>,"*","/fsdp/new"],
  ["Profile",<FsdpDetailPage/>,"/fsdp/:id","/fsdp/1"],
  ["Maintenance",<BackupExportPage/>,"*","/backup-export"],
] as const){
  test(`${name} has labelled controls and accessible structure`,async()=>{
    const router=createMemoryRouter([{path,element:<main>{element}</main>}],{initialEntries:[url]});
    const {container}=render(<RouterProvider router={router}/>);
    await waitFor(()=>expect(container.querySelectorAll("h1").length).toBeGreaterThan(0));
    await new Promise(resolve=>setTimeout(resolve,0));
    const result=await axe.run(container,{runOnly:{type:"rule",values:rules}});
    expect(result.violations.map(item=>`${item.id}: ${item.description}`)).toEqual([]);
  });
}
