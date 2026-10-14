# Validation: 0.5.12

- Backend: 191 tests passed; Ruff passed.
- Frontend: 121 tests passed; application and test TypeScript checks passed; production build passed.
- Packaged executable: authenticated startup, schema persistence, separate profile/grant remarks, CSV, education, latest status, filters, cloning, account revocation and shutdown checks passed.
- Private copy of development database: schema 8 to 10 with a verified protected snapshot. All 126 scholar identities and all grant, requirement, education and account values preserved. 26 profiles classified Staff; original noncanonical affiliation labels retained in profile remarks. COE and COED remain distinct.
- Browser: whole-profile remarks edited and saved with grant notes intact using synthetic records. Desktop profile and Dashboard reviewed. At 390px width, page content stays within the viewport; vertical charts scroll inside their own regions. Chart text alternatives and labelled controls remain available. Existing five-screen automated structural accessibility checks passed.
- Release delivery preserves the installed database during runtime replacement; migration runs on normal startup after making a protected snapshot. The Office update contains no live data folder.

This verifies local behavior and a copied database, not a deployment to the actual Office PC.
