# Google report and publication plan

**Release:** 0.5.23; database schema 16 remains unchanged.

1. Add a dedicated Google reporting projection with exactly fifteen columns: No., Name, Age, Tenure, Department, Rank/position, Previous degree, Program, Delivering HEI, Grant type, Date started, Date ended, Extension, Status, Remarks.
2. Keep scholars alphabetical and grants together. Number scholars once, retain all education entries, use actual dates or the recorded academic period, and distinguish profile and grant remarks in the single Remarks column. Preserve optional and missing values without inventing dates or modifying records. Keep CSV exports unchanged.
3. Expand the administrator setup guide with Google Cloud project/API/client steps, test-user approval, the correct account's editing access, per-PC sign-in, errors, manual report replacement, and credential handling. Include the guide in Office downloads and both GitHub repositories. Fix the in-app guide link.
4. Test the exact output contract, grouped grants, education, dates, literal cells, permissions and failure handling using synthetic records. Run release regressions, formatting, types, clean-seed packaging, bundled verification and a native Office updater rehearsal.
5. Prepare a current application-only update and sanitized source snapshot. Publish normally to the existing repositories, preserve their histories/releases, verify fresh downloads, and check the source workflow. Never publish the working database, accounts, local Google credentials, refresh tokens or encrypted connection file.
6. Install the verified local runtime when Cathedra is closed, preserving the database and existing local Google connection. Verify the installed runtime and record actual publication and installation evidence separately.

The user's successful live connection confirms the existing OAuth flow works. It does not authorize placing their email address, project details, spreadsheet address, scholar records or downloaded credentials in public documentation. All published examples use neutral placeholders.
