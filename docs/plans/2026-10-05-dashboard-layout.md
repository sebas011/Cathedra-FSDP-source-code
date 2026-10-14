# Dashboard presentation — 0.5.7

Read-only audit: current Dashboard contains summary cards, simple tracks, a CSS donut, a large quick-link card, ten scholars and duplicated report totals/filters. Analytics APIs already return correct scoped category counts. No data/schema changes are needed.

Use frontend-design. Preserve the institutional green #176247, white surfaces #ffffff, pale green #eef6f1, ink #24352e, muted #64746c and rule #dce6df. Keep existing Segoe UI typography; use 30px headings, 32px totals, 18px section titles and readable 14px labels. Align text and comparisons to the left. Favor measured chart space over decorative blocks.

Layout:
Header and department/year/order controls
Four concise summary cards
Department comparison (wide) | Grant outcomes donut (narrow)
Latest ten scholars (wide)   | Grant-type comparison + follow-up links
Dashboard reports and print/export views

Reviewed against the brief: use actual count axes and readable legends; no invented time-series, growth percentages or enrollment forecasts. Give department comparisons priority, since scholars are the office's principal entities; explain grant-record counts separately. Keep reports embedded and preserve shared filters, print/export, recent scholar links, loading/error and zero-data behavior. Use SVG charts with text equivalents; no third-party dependency needed. Responsive chart scrolling is confined to the chart region; page layout must not overflow at phone width.

Validate sorting/scales, totals and percentage legends, empty states, scope/export integration, accessibility, responsive screenshots, frontend checks and packaged desktop smoke. Install guarded with original database hash unchanged and a retained rollback snapshot. Office distribution remains unchanged.
