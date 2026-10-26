# UI simplification audit — 26 October 2026

Reviewed the login, shared shell, all four roles, ledger, search, import list and wizard, import report, review list and case detail, analytics, oversight, passport, timeline, certificate upload and report, career guidance, print output and error pages. This is a UI review and implementation record; the wider specification gaps in `../verification-report.md` remain separate.

The owner's new requirements retire presentation controls and prohibit horizontal scrolling. These choices supersede the original brief's density and developer-page requirements.

## Findings and changes

| Finding | Change | Reason |
| --- | --- | --- |
| A density preference appeared above every table, including very small evidence lists. | Removed its UI, state and styles. | Adds repeated decisions without helping the record workflow. |
| Workspace, institution and pagination settings were duplicated or overexposed. | Removed the topbar institution switcher and rows/advice/events-per-page selectors. Filters stay on their relevant pages; pagination appears only when necessary. | One place to change each scope; fewer persistent controls. |
| Architecture and Demo controls belonged to the development process. | Removed both routes and their components. Documentation and CLI tools remain in the repository. | Technical tools do not belong in the product interface. |
| Three layers of synthetic-data messaging and a decorative footer repeated the same information. | Kept one persistent synthetic-service banner; removed the secondary strip, sidebar seal and slogan footer. Specific certificate and trust limitations remain next to their results. | Preserve the meaning without repeating it on every surface. |
| Display serif headings, cream/gold styling, all-caps subtitles and decorative seals made the app look like a presentation template. | Applied consistent sans-serif typography, neutral surfaces, quieter borders, smaller headings and restrained status colors. Removed decorative seals and circular trust display. | Let record names, status and actions establish hierarchy. |
| Login had a marketing hero unrelated to the immediate task. | Replaced it with a single sign-in panel and compact product identity. Demo account shortcuts remain optional. | Access is the task; promotion adds a second competing purpose. |
| Tables and section links relied on sideways movement. | Reflow tables into labeled records below 680px container width; wrap navigation, steps and long text. Keep all fields and links available. | No horizontal scrolling and no hidden columns. |
| Search and analytics exposed cache flags, epochs, raw timings, timestamps and program UUIDs. | Removed performance internals from normal views, formatted update times and resolved program names. Aggregate admissions are grouped by cohort when no institution is selected. | Display information a user can interpret and act on. |
| Certificate processing technology occupied a primary metric card. | Moved extraction-engine information into optional processing details beside the document evidence. | Keep confidence and risk prominent while retaining diagnostic transparency. |
| Record links and print actions were duplicated. | Use one record-name link where available and one print action per view. | Avoid redundant click targets. |
| Career history filled the page with repeated entries and implementation labels. | Show five entries at a time, retain navigation to older advice, use “Career guidance” and remove the phrasing-engine label. | Keep the decision and skill evidence prominent. The API still uses supported 25-record batches. |
| Sample downloads competed with upload actions. | Move sample files into optional disclosures. | Help demo users without crowding the main task. |
| Small empty tables rendered large illustrated placeholder panels. | Replace them with a short empty-state line. | Empty evidence should not dominate a page. |
| Charts alternated colors within a single series without a meaning. | Use one series color; reserve distinct colors for quality-status categories. | Color should communicate a distinction. |
| Keyboard and table semantics needed attention after reflow. | Added a skip link, retained table headers and roles, associated data cells with their headers, labeled mobile fields and preserved focus behavior. | Reflow must work with assistive technology as well as visually. |

## Source review locations

- `apps/web/src/components/shared/data-table.tsx:9` — density removed; record links and responsive field labels centralized.
- `apps/web/src/components/shared/page-heading.tsx:3` — decorative page subtitles removed.
- `apps/web/src/components/shell/app-shell.tsx:11` — duplicate notices/footer removed; main content target added.
- `apps/web/src/components/shell/topbar.tsx:14` — duplicate scope selector removed.
- `apps/web/src/components/students/profile-header.tsx:5` — decorative seal and score ring removed.
- `apps/web/src/components/students/audit-timeline.tsx:12` — fixed event pagination and optional technical change details.
- `apps/web/src/components/career/career-screen.tsx:23` — shorter history with supported API batching.
- `apps/web/src/app/globals.css:1` — shared typography, color, spacing, print and responsive rules.

## Verification

- Production build and TypeScript checks passed.
- ESLint passed with one pre-existing navigation warning in `src/lib/api.ts`.
- Full browser suite: **26 passed, 0 failed, 0 skipped**, recorded in [browser-results.json](browser-results.json). Covers role restrictions, real search, certificates, career history, audit integrity, cookie handling, request refresh, privacy and responsive accessibility.
- Separate route-removal check passed for `/architecture` and `/settings/demo`: [retired-pages-results.json](retired-pages-results.json).
- Role screens were checked at **375, 768 and 1440px** for document overflow and horizontally scrollable elements. All fields in narrow record layouts remain available. The mobile screens also passed automated WCAG A/AA checks.
- Import report, case detail and certificate report were additionally checked at all three widths: [detail-review.json](detail-review.json). No horizontal scrolling was found.
- All three A4 passport pages were rendered and visually reviewed. Printing retains the conventional table layout.
- The browser login helper honors the server's cooldown when the suite repeatedly signs into the same demo account. Application authentication limits were not relaxed.
- Final empty-state rendering was checked separately against the search/privacy flows.
- After the last empty-state, timestamp and certificate-detail refinements, **8 targeted browser checks passed**: [final-refinement-results.json](final-refinement-results.json).
- The repository placeholder and generated-secret scan passed.

No live usability study was conducted. “Less AI-made” is an aesthetic preference; the measurable changes here are reduced repetition, clearer information hierarchy, accessible reflow and preserved task behavior.

## Reference material

- [Reddit: adapting a dashboard table for mobile](https://www.reddit.com/r/UXDesign/comments/1b2znzv). Replies include switching to stacked rows/cards when sideways scrolling is unsuitable.
- [Reddit: three approaches to mobile tables](https://www.reddit.com/r/UXDesign/comments/1waou1e/3_ways_to_adapt_a_table_for_mobile_devices/). The discussion is mixed and stresses the tradeoff between comparison and individual record reading. The implementation follows the owner's explicit no-horizontal-scroll constraint.
- [Reddit: critique of generic generated interfaces](https://www.reddit.com/r/UXDesign/comments/1tvt03p/aigenerated_ui_proves_people_value_design_but_not/). Useful criticism concerns excessive decoration, weak hierarchy and visual signals without a task purpose; it is qualitative feedback, not a universal design standard.
- [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) informed the keyboard, form, content and responsive checks.

## Visual evidence

- [Login — desktop](login-desktop.png) and [mobile](login-mobile.png)
- [Institution ledger](dashboard-desktop.png)
- [Import report](import-report.png)
- [Review case](case-detail.png)
- [Certificate report](certificate-report.png)
- Refreshed search, analytics, career, mobile passport and print evidence are in the parent `docs/` directory.
