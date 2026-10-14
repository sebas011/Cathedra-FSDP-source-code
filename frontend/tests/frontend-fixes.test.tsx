import { StrictMode } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, expect, test, vi } from 'vitest';
import BackupExportPage from '../src/pages/BackupExportPage';
import SystemReadinessPage from '../src/pages/SystemReadinessPage';
import AppShell from '../src/components/AppShell';
import { validateGrant } from '../src/utils/grantValidation';
import type { MaintenanceStatus, ParticipationInput } from '../src/types';
import { administrator } from './fixtures';

const api=vi.hoisted(()=>({getMaintenanceStatus:vi.fn(),getCurrentUser:vi.fn(),restoreDatabase:vi.fn(),clearSession:vi.fn(),downloadExport:vi.fn(),createDatabaseBackup:vi.fn(),deleteDatabaseBackup:vi.fn(),downloadDatabaseBackup:vi.fn(),setBackupProtection:vi.fn(),getServiceHealth:vi.fn(),signOut:vi.fn(),exitDesktop:vi.fn()}));
const review=vi.hoisted(()=>({recordBackupReview:vi.fn()}));
vi.mock('../src/api',()=>({...api,releaseVersion:'test'}));
vi.mock('../src/api/maintenance',()=>review);
const status:MaintenanceStatus={database_status:'healthy',database_file:'cathedra.db',database_size_bytes:1,fsdp_records:2,backup_count:1,latest_backup_at:null,backup_retention:null,backups:[{filename:'cathedra-backup-example.db',created_at:'2026-10-03T00:00:00Z',size_bytes:1,protected:true}]};
function open(element:React.ReactElement){const router=createMemoryRouter([{path:'/review',element},{path:'/away',element:<h1>Away</h1>},{path:'/login',element:<h1>Signed out</h1>}],{initialEntries:['/review']});return {...render(<RouterProvider router={router}/>),router};}
beforeEach(()=>{vi.resetAllMocks();api.getCurrentUser.mockReturnValue(administrator);api.getMaintenanceStatus.mockResolvedValue(status);vi.spyOn(window,'confirm').mockReturnValue(true);vi.stubGlobal('matchMedia',vi.fn(()=>({matches:false,addEventListener:vi.fn(),removeEventListener:vi.fn()})));api.getServiceHealth.mockResolvedValue({status:'ok',product:'fsdp',desktop_mode:true,release_version:'test'});});

async function pendingRestore(){api.restoreDatabase.mockReturnValue(new Promise(()=>{}));const view=open(<BackupExportPage/>);fireEvent.click(await screen.findByRole('button',{name:'Restore Selected Backup'}));await waitFor(()=>expect(api.restoreDatabase).toHaveBeenCalled());return view;}

test('pending restore blocks route navigation, unload, and application leave',async()=>{
 const {router}=await pendingRestore();
 expect(window.dispatchEvent(new Event('cathedra-can-leave',{cancelable:true}))).toBe(false);
 const unload=new Event('beforeunload',{cancelable:true});window.dispatchEvent(unload);expect(unload.defaultPrevented).toBe(true);
 await act(async()=>{await router.navigate('/away')});
 const dialog=await screen.findByRole('dialog',{name:'Finishing the operation'});
 expect(dialog.textContent).toContain('restore');expect(router.state.location.pathname).toBe('/review');
 expect(screen.getByRole('button',{name:'Leave without saving'}).matches(':disabled')).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Stay here'}));expect(router.state.location.pathname).toBe('/review');
});

test.each(['Logout','Exit Cathedra'])('pending restore blocks %s in the shell',async action=>{
 api.restoreDatabase.mockReturnValue(new Promise(()=>{}));
 render(<RouterProvider router={createMemoryRouter([{path:'/review',element:<AppShell/>,children:[{index:true,element:<BackupExportPage/>}]}],{initialEntries:['/review']})}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Restore Selected Backup'}));
 await waitFor(()=>expect(api.restoreDatabase).toHaveBeenCalled());
 fireEvent.click(await screen.findByRole('button',{name:action}));
 await screen.findByText('Wait for the current save to finish before leaving.');
 expect(api.signOut).not.toHaveBeenCalled();expect(api.exitDesktop).not.toHaveBeenCalled();
});

test('successful restore releases navigation guard and signs out',async()=>{
 let finish!:(value:unknown)=>void;api.restoreDatabase.mockImplementation(()=>new Promise(resolve=>{finish=resolve}));
 const {router}=open(<BackupExportPage/>);fireEvent.click(await screen.findByRole('button',{name:'Restore Selected Backup'}));
 await waitFor(()=>expect(api.restoreDatabase).toHaveBeenCalled());await act(async()=>finish({safety_backup:'safe.db'}));
 await screen.findByRole('heading',{name:'Signed out'});expect(router.state.location.pathname).toBe('/login');expect(api.clearSession).toHaveBeenCalledTimes(1);
});

test('failed restore keeps page available and releases the pending guard',async()=>{
 api.restoreDatabase.mockRejectedValue(new Error('Restore failed'));
 const {router}=open(<BackupExportPage/>);fireEvent.click(await screen.findByRole('button',{name:'Restore Selected Backup'}));await screen.findByText('Restore failed');
 await waitFor(()=>expect(window.dispatchEvent(new Event('cathedra-can-leave',{cancelable:true}))).toBe(true));
 await act(async()=>{await router.navigate('/away')});await screen.findByRole('heading',{name:'Away'});expect(api.clearSession).not.toHaveBeenCalled();
});

test('recovery-review save blocks parent operations through status refresh',async()=>{
 let finish!:()=>void;review.recordBackupReview.mockImplementation(()=>new Promise<void>(resolve=>{finish=resolve}));
 open(<BackupExportPage/>);await screen.findByRole('button',{name:'Restore Selected Backup'});
 fireEvent.change(screen.getByLabelText('Backup reviewed'),{target:{value:status.backups[0].filename}});
 fireEvent.click(screen.getByRole('checkbox',{name:'I copied this backup to private off-device storage.'}));fireEvent.click(screen.getByRole('button',{name:'Record recovery review'}));
 await waitFor(()=>expect(review.recordBackupReview).toHaveBeenCalled());
 expect(window.dispatchEvent(new Event('cathedra-can-leave',{cancelable:true}))).toBe(false);
 expect(screen.getByRole('button',{name:'Restore Selected Backup'}).matches(':disabled')).toBe(true);
 let refresh!:(value:MaintenanceStatus)=>void;api.getMaintenanceStatus.mockImplementationOnce(()=>new Promise(resolve=>{refresh=resolve}));
 await act(async()=>finish());await waitFor(()=>expect(api.getMaintenanceStatus).toHaveBeenCalledTimes(2));
 expect(window.dispatchEvent(new Event('cathedra-can-leave',{cancelable:true}))).toBe(false);
 await act(async()=>refresh(status));await waitFor(()=>expect(window.dispatchEvent(new Event('cathedra-can-leave',{cancelable:true}))).toBe(true));
});

test('export failure does not change healthy database feedback',async()=>{
 api.downloadExport.mockRejectedValue(new Error('Export failed'));open(<BackupExportPage/>);fireEvent.click(await screen.findAllByRole('button',{name:'Download CSV'}).then(buttons=>buttons[0]));await screen.findByText('Export failed');
 expect(screen.getByRole('heading',{name:'Database connection is available'})).toBeTruthy();expect(screen.getByText('Connected')).toBeTruthy();
});

test('failed status refresh clears the healthy badge',async()=>{
 open(<BackupExportPage/>);await screen.findByText('Connected');api.getMaintenanceStatus.mockRejectedValueOnce(new Error('Status unavailable'));
 fireEvent.click(screen.getByRole('button',{name:'Refresh status'}));await screen.findByText('Status unavailable');expect(screen.queryByText('Connected')).toBeNull();expect(screen.getByRole('heading',{name:'Database status unavailable'})).toBeTruthy();
});

test.each(['success','failure'])('readiness ignores older %s after the newer result',async old=>{
 let finish!:(value:MaintenanceStatus)=>void;let fail!:(reason:Error)=>void;
 api.getMaintenanceStatus.mockImplementationOnce(()=>new Promise<MaintenanceStatus>((resolve,reject)=>{finish=resolve;fail=reject}));
 if(old==='success')api.getMaintenanceStatus.mockRejectedValueOnce(new Error('Current failed'));else api.getMaintenanceStatus.mockResolvedValueOnce(status);
 render(<StrictMode><RouterProvider router={createMemoryRouter([{path:'*',element:<SystemReadinessPage/>}])}/></StrictMode>);
 await waitFor(()=>expect(api.getMaintenanceStatus).toHaveBeenCalledTimes(2));
 await act(async()=>{if(old==='success')finish(status);else fail(new Error('Old failed'))});
 if(old==='success'){await screen.findByText(/Current failed/);expect(screen.queryAllByText('Available')).toHaveLength(0);}else{await screen.findAllByText('Available');expect(screen.queryByRole('alert')).toBeNull();}
});

test('readiness refresh stays disabled until the current check completes',async()=>{
 let finish!:(value:MaintenanceStatus)=>void;api.getMaintenanceStatus.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));open(<SystemReadinessPage/>);
 expect(screen.getByRole('button',{name:'Refresh Check'}).matches(':disabled')).toBe(true);await act(async()=>finish(status));expect(screen.getByRole('button',{name:'Refresh Check'}).matches(':disabled')).toBe(false);
});

const grant:ParticipationInput={program_name:'Example',delivering_hei:'',start_date:null,end_date:null,start_term:'1st',start_academic_year:'2026-2027',end_term:'',end_academic_year:'',grant_type:null,grant_other:'',status:'On Going',extension:'',remarks:''};
test('custom grant terms and aliases are accepted',()=>{expect(validateGrant({...grant,start_term:'3rd'})).toBe('');expect(validateGrant({...grant,start_term:'1st Term'})).toBe('');});
test('custom terms can be changed without the original-grant validation state',()=>{const original={...grant,id:7,start_term:'3rd'};expect(validateGrant(original)).toBe('');expect(validateGrant({...original,start_term:'2nd'})).toBe('');expect(validateGrant({...original,id:8})).toBe('');});
