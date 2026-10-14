import { useState } from "react";
import { Link } from "react-router-dom";
import PageHeading from "../components/PageHeading";
import { BackupIcon, FsdpIcon, HelpIcon, ReportsIcon, SettingsIcon } from "../components/Icons";
import { productName } from "../product";

const categories = [
  { name: "All topics", icon: HelpIcon },
  { name: "Scholars & grants", icon: FsdpIcon },
  { name: "Office log", icon: FsdpIcon },
  { name: "Reports", icon: ReportsIcon },
  { name: "Backup & recovery", icon: BackupIcon },
  { name: "Accounts & access", icon: SettingsIcon },
] as const;
const articles = [
  { title: "Program catalog permissions", category: "Scholars & grants",
    paragraphs: ["In the grant editor, use Existing program to select a saved program by its catalog ID, or enter a missing Program Applied name. Staff and administrators can create a missing typed program name when saving a scholar. Prefer an existing matching name so annual grants stay under the same program.", "Administrators manage the program catalog in Settings: add, edit, duplicate or remove unused entries. Programs with history cannot be deleted. Existing names that need identity review remain separate; select the intended catalog entry by its ID. Direct catalog editing and program duplication are administrator actions. Duplicate program saves a separate catalog entry immediately; cancelling a scholar draft does not undo that copy. For another year of the same program, use an annual grant instead."],
    links: [{ to: "/fsdp", label: "Open scholars" }] },
  { title: "Annual grants within one program", category: "Scholars & grants",
    paragraphs: ["Keep the same Program Applied for each year of a multi-year program. Create one grant per academic year and choose that year's Full Scholarship, Partial Scholarship or Aid grant type. Each record keeps its own outcome, case status, optional dates and remarks.", "Administrators can use Copy for next year to open a new annual draft under the same program. It advances recognized academic-year ranges, retains remarks, resets the outcome to On Going and the case to Open, and clears the extension plus start, end, contract completion and graduation dates. Review both periods, remarks and grant type before saving. Duplicate program creates a separate catalog program; use it only for a distinct program.", "Grant history starts collapsed. Expand Grant history, then a program and an academic-year row to see details. Printing expands every grant and restores the previous expanded or collapsed view afterward. Icon actions have labels available on hover and to assistive technology."],
    links: [{ to: "/fsdp", label: "Open scholars" }] },
  { title: "Graduation evidence and education", category: "Scholars & grants",
    paragraphs: ["A Completed grant adds its program to Education background even when remarks contain no graduation statement. Older Graduated outcomes are displayed and saved as Completed. You may record an optional Graduation date on each grant; its year supplies automatic education evidence for that program. Completing a grant does not invent a graduation date or year.", "Direct graduation statements about the current program can also add education. Examples include Graduated in 2022, Graduated on June 15, 2022 and Graduation year: 2022. Statements about another person, a previous degree or a different qualification are skipped, as are expected, planned, negative or unclear statements. Ambiguous dates such as 06/07/2022 are left for manual review. Academic years, grant end dates and contract completion dates do not prove graduation.", "Review education entries and correct or remove one when necessary. Deliberately edited or cleared years are preserved. Removed automatic entries stay removed until explicitly restored. Education extracted from remarks does not change the recorded grant outcome or payback assessment. After confirming completion, choose Completed to clear calculated follow-up for annual grants in that same program. Recorded Payback and Payback pending contract remain office decisions."],
    links: [{ to: "/fsdp", label: "Open scholars" }] },

  { title: "Add and update a scholar", category: "Scholars & grants",
    paragraphs: ["Open Scholars and add or edit scholar information. Add profile remarks, education entries, tenure in years, grants and requirements inside the scholar profile; save the scholar to persist changes.", "Use the Dashboard for contract assessment and reporting. Use Dashboard reports for filtered printable summaries."],
    links: [{ to: "/fsdp", label: "Open scholars" }, { to: "/", label: "Open dashboard" }] },
  { title: "Colleges and Staff", category: "Scholars & grants",
    paragraphs: ["The eight colleges are CIT, CAS, COED, COE, CCJ, COF, CBMA and CCS. COED (College of Education) and COE (College of Engineering) remain separate. All other affiliations, including IIT, campus labels, HRMO and Staff Talisay, use the single Staff category.", "Select College / Staff when editing a scholar. Staff affiliation also sets personnel type to Staff. Personnel type is automatic: any of the eight colleges is Faculty; any other known affiliation is Staff. Missing affiliation information is Unknown. During the upgrade, former staff or campus affiliation labels are retained in profile remarks, alongside any existing notes."],
    links: [{ to: "/fsdp", label: "Open scholars" }] },
  { title: "Profile remarks and grant remarks", category: "Scholars & grants",
    paragraphs: ["Profile remarks belong to the whole scholar and appear after age and tenure, beside education and grant history. Edit the scholar and enter Profile remarks under Scholar Information, then Save Scholar. Existing grant remarks remain separate and belong only to their individual grant.", "Profile remarks are included in the FSDP and Dashboard report CSV exports and when printing the profile. Remarks are plain text; line breaks are preserved."],
    links: [{ to: "/fsdp", label: "Open scholars" }] },
  { title: "Record text, academic years and numeric fields", category: "Scholars & grants",
    paragraphs: ["New or edited scholar, education, program, grant, requirement and office-log text is saved in capital letters, including remarks. Account names and passwords keep their original case. Existing text that you have not changed is retained.", "Typing a consecutive range such as 20262027 inserts the academic-year dash: 2026-2027. A single four-digit year completes to the next year when you leave the field or save. Partial, custom and nonconsecutive historical values remain accepted. Terms remain 1st, 2nd, 3rd and Summer.", "The mouse wheel does not alter age or tenure while those fields have focus. You can still type a number or use the arrow keys. Grant outcome and Open/Closed controls are near remarks at the end of the grant editor."],
    links: [{ to: "/fsdp", label: "Open scholars" }] },
  { title: "Grant outcomes and Open/Closed cases", category: "Scholars & grants",
    paragraphs: ["Outcome records what happened to the grant, including On Going, Completed, Transferred, Payback and Payback pending contract. Case status records whether the office is still handling that grant: Open or Closed. These are separate fields.", "Closing a case keeps its recorded outcome and does not clear payback review. Completing a program clears calculated follow-up for the same program, independently of case status. Confirm office evidence before recording Completed or a repayment outcome."],
    links: [{ to: "/fsdp", label: "Open scholars" }] },
  { title: "Record office notes and document movements", category: "Office log",
    paragraphs: ["Open Office log for general office notes or use Office log on a scholar profile to associate an entry with that scholar. Staff and administrators can add entries; viewers can read them. Select Note, Document received or Document transferred, enter a note and optionally identify the document and departments. Entry date defaults to today and can be changed.", "Saved entries retain their recorded author and creation time. They cannot be edited or deleted. Add a new entry explaining a correction when necessary. A scholar's historical name remains in the log if the profile is later deleted. This manual log is separate from the administrator's automatic Activity History.", "If saving is not confirmed, check the log and retry the same unchanged draft. The app retains a retry identifier to avoid saving that entry twice. Clear the draft before starting a different entry. Search and entry-type filters apply to the list and Export log CSV; the export includes all matching entries. Native Ctrl+P includes only visible page content."],
    links: [{ to: "/office-log", label: "Open office log" }] },
  { title: "Contract and payback counts", category: "Reports",
    paragraphs: ["Contract assessment counts each scholar once in each category. A scholar with multiple grants may appear in more than one category. Category counts cover the selected college/year scope; the table and CSV contain the selected category. Use Payback pending contract while the repayment contract is being arranged. Change the recorded outcome to Payback after the office completes that contract. Payback review identifies unfinished programs after the grace period and does not change a grant’s outcome automatically.", "The grace period is three calendar years after the optional contract completion date, including its final day. Payback review starts the following day. Recorded Payback and Payback pending contract keep their classifications even when another annual grant is Completed. Did Not Avail is excluded. Otherwise, a recorded completion clears calculated follow-up for annual grants in the same program. Closing a case does not clear this follow-up. Review candidates before changing recorded outcome; missing completion dates cannot produce a calculated deadline."],
    links: [{ to: "/#contract-assessment", label: "Review contract assessment" }] },
  { title: "Similar names and change history", category: "Scholars & grants",
    paragraphs: ["Saving a scholar checks similar names. Review the warning; separate people stay separate and are never automatically merged. Use the scholar ID and recorded details to distinguish people with the same name.", "Administrators can expand Change history on a scholar profile to see the editor, time and changed field names."],
    links: [{ to: "/fsdp", label: "Find a scholar" }] },
  { title: "Follow up on requirements and grant periods", category: "Scholars & grants",
    paragraphs: ["Scholar profiles retain requirement details. Dashboard contract assessment lists payback records and three-year grace periods. Grant terms use 1st, 2nd, 3rd and Summer, with a separate academic year. The optional contract completion date starts the grace period and is not a graduation date.", "Edit the scholar profile to update grant and requirement details, then save your changes."],
    links: [{ to: "/", label: "Open dashboard" }] },
  { title: "Filter, export and print a report", category: "Reports",
    paragraphs: ["Use Dashboard reports for filtered printable summaries. Choose the college / Staff, rank / position, current scholar status, grant type, delivering HEI or requirements follow-up filter. Clear filters to broaden the results.", "Choose Overview, Follow-up actions or Scholar results. Print dashboard and the top Print This Page button prepare the same complete dashboard document: its overview, the selected contract category and the selected report view. Each section prints its scope. Tables show one page at a time; these print buttons and CSV exports include all matching rows. Changing filters or leaving while print preparation is pending cancels that print. The scholar directory’s Print This Page button includes all matching scholars. Native Ctrl+P prints only the currently displayed page content, marked Visible page content; use the app’s print button for complete matching lists. Contract follow-up CSV includes every record in the selected category. Keep exported office records private."],
    links: [{ to: "/", label: "Open dashboard reports" }] },
  { title: "Read scholar and grant CSV rows", category: "Reports",
    paragraphs: ["Scholar-directory, Dashboard report detail and contract follow-up CSV files keep each scholar's grants together, with one grant per row. The first row shows the scholar's name and profile information beside the first grant. Following rows leave the scholar cells empty and show that scholar's other grants. The next named row starts a new scholar. A scholar with no grants has one profile row in the directory and report detail.", "Read each grant's own terms, academic years, dates, outcome, case status and remarks across its row. Empty scholar cells mean the same scholar as above; an empty grant field means no value was recorded for that grant. Keep continuation rows with their named scholar when sorting or filtering a spreadsheet. CSV includes every matching record, even when the screen shows only one page.", "Profile remarks and grant remarks have separate columns. Education and Office log CSV files keep one complete row per education entry or log entry. Exported files are reports; use a database backup for recovery. Keep office records private."],
    links: [{ to: "/backup-export", label: "Open exports" }, { to: "/", label: "Open dashboard reports" }] },
  { title: "Understand scholar and grant counts", category: "Reports",
    paragraphs: ["Dashboard scholars are counted once. The vertical bar chart compares scholars across colleges and Staff. The status doughnut shows the most recent grant status for each scholar. The grant-type pie counts individual grant records; its labels show counts and shares of the selected grants. Year filters use the recorded grant start academic year, not a presumed active semester.", "Department and academic year filters apply to the overview and reports. Requirements follow-up counts flagged profiles; unflagged profiles are not assumed to have complete requirements. No dates or missing grant types are guessed."],
    links: [{ to: "/", label: "Open dashboard" }] },
  { title: "Keep FSDP recovery copies", category: "Backup & recovery",
    paragraphs: ["Use this app to manage FSDP scholars, grants and requirements. Keep a private recovery copy of your office records.", "Keep private off-device backups. Restore only compatible Cathedra FSDP backups."],
    links: [{ to: "/backup-export", label: "Open backups" }] },
  { title: "Review your recovery copies", category: "Backup & recovery",
    paragraphs: ["Backup & Export reminds you after seven days without a local snapshot. Record an off-device recovery review only after copying the selected backup to private storage; report a restore test only when you actually completed one in an isolated data folder."],
    links: [{ to: "/backup-export", label: "Review backups" }] },
  { title: "Check protection of the working computer", category: "Backup & recovery",
    paragraphs: ["An encrypted external drive does not encrypt this PC’s live database. Check Windows Manage BitLocker for the home and office working drives.", "The read-only tools/check-device-protection.ps1 diagnostic reports unavailable checks as unverified and never changes encryption or reads recovery keys."],
    links: [{ to: "/system-readiness", label: "Open system readiness" }] },
  { title: "Passwords and office accounts", category: "Accounts & access",
    paragraphs: ["Use Accounts & Access to change your password. Passwords need at least 10 characters. A temporary password must be changed before accessing office records.", "Administrators can add office accounts, reset temporary passwords, disable or reactivate accounts, and sign out sessions. Give temporary passwords to the account owner securely. Staff can manage their own password."],
    links: [{ to: "/settings/accounts", label: "Open account settings" }] },
] as const;

export default function ProductGuidePage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All topics");
  const search = query.trim().toLocaleLowerCase();
  const results = articles.filter(article =>
    (category === "All topics" || article.category === category) &&
    [article.title, article.category, ...article.paragraphs].join(" ").toLocaleLowerCase().includes(search),
  );
  return <div className="stack-md office-guide">
    <PageHeading title={productName + " office guide"} description="Find guidance for scholar records, reporting, account access and recovery. Available offline." />
    <section className="guide-search no-print" aria-label="Search office guidance">
      <label>Search the office guide<input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Try requirements, backups, passwords or reports" /></label>
      <p>Choose a topic or search the guidance below.</p>
    </section>
    <section className="guide-recovery">
      <h2>Before restoring office records</h2>
      <p>Keep a private backup. Restore only a Cathedra FSDP backup. If Cathedra reports that database recovery is required, exit and restart it. If startup fails, keep the data folder and safety backups unchanged and contact your administrator.</p>
      <div className="action-group no-print"><Link className="btn secondary" to="/backup-export">Open backups</Link><Link className="btn secondary" to="/system-readiness">Check system readiness</Link></div>
    </section>
    <div className="guide-layout">
      <nav className="guide-categories no-print" aria-label="Guide topics">
        {categories.map(({ name, icon: Icon }) => <button type="button" key={name} aria-pressed={category === name} onClick={() => setCategory(name)}><Icon /><span>{name}</span></button>)}
      </nav>
      <div className="guide-articles">
        <p className="guide-result-count no-print" role="status">{results.length} {results.length === 1 ? "topic" : "topics"}{category !== "All topics" && ` in ${category}`}</p>
        {!results.length && <div className="data-card empty-state"><h2>No guidance matches your search</h2><p>Try a different phrase or clear the search and topic selection.</p><button className="btn secondary" type="button" onClick={() => { setQuery(""); setCategory("All topics"); }}>Clear search and topic</button></div>}
        {results.map(article => <details className="guide-article" key={article.title} open={!!search}>
          <summary><h2>{article.title}</h2></summary>
          <div className="guide-answer">{article.paragraphs.map(text => <p key={text}>{text}</p>)}<div className="action-group no-print">{article.links.map(link => <Link key={link.to} to={link.to}>{link.label}</Link>)}</div></div>
        </details>)}
      </div>
    </div>
  </div>;
}
