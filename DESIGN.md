# ScopeQuay interface system

The local dashboard extends the existing research reports' navy/teal identity to
an operational master-detail application. The primary user reviews actions on a
desktop in ordinary indoor light; white work surfaces and dark text keep evidence
readable. The navy rail remains distinct from the approval workspace.

Colors: ink #163544, navigation #123442, action teal #006e68, ground #eef4f4,
white surface #fff, lines #cedbdc. Amber identifies approval or clarification;
red identifies policy/authority blocks; green identifies ready/completed states.
Every color-coded state includes visible text. Typography uses Segoe UI/system
sans; code uses Consolas/monospace. Body size is 15px with a 1.55 line height.

The queue and detail share one framed workspace. Standard labeled select, textarea
and buttons support the main task. Approval changes the request in place and adds
to its ordered history; execution remains separate. The audit table is secondary.
Below 800px the navigation becomes a top row and queue/detail stack; the queue has
a bounded scroll region. Audit tables scroll horizontally on narrow screens.

Focus outlines, loading/disabled controls, errors, empty states, reduced-motion
behavior and explicit single-user simulation notices are implemented. Desktop
workflow was exercised in the browser; a 390px viewport showed no horizontal
document overflow. Initial tests found database handles left open on Windows;
the connection context now explicitly closes them and the regression suite passes.
An export control that remained disabled after mutation was corrected during UI
verification. This is not a claim of a full accessibility or security audit.

Screenshot provenance: docs/images/approval-dashboard.jpg is a browser capture of
our running local demo after explicit simulated approval/execution on 12 November
2026. Its example content is illustrative; no external art or stock asset is used.

Brand assets updated 12 November 2026: the user supplied the dark and light PNG wordmarks. Both originals are copied byte-for-byte into the application and public guide, with aspect ratios preserved. The dark wordmark appears in the sidebar; the light wordmark heads the guide; the README chooses by color scheme. No generated replacement or image editing was performed.

The v0.4 workbench makes the experiment form, measured comparisons, outcome selector and action/effect trail the main workflow. A browser run completed 304 supplied-action records across 152 held-out points for two controllers with zero model calls. The review command returned ESCALATE for the approval example. The unavailable-model error was verified. A 390px viewport had a 380px document width and single-column controls; tables intentionally scroll. docs/images/workbench-v04.jpg is a browser capture of that actual comparison on 13 November, not fabricated model results.
