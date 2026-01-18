Summary of work on publications.md

- Added a new 2026 section and moved the Adam Freese paper (Inspire 2929752) to Phys. Rev. D 113 (2026) 016011.
- Added new 2025 entries from the email/Inspire links: 3096040, 3092541, 3090271, 3089721, 3087417, 3086272, 3082176, 3076634, 3075180, 3073772, 3069966, 3033947, 2983527, 2968593, 2963557, 2964942, plus arXiv 2511.01818.
- Updated several 2025 entries from e-Print to published citations using Inspire metadata: 2956135, 2960502, 2954235, 2924990, 2921962, 2871492, 2952146, 2963564.
- Moved K.-F. Liu “Lattice QCD and the Neutron Electric Dipole Moment” from 2024 to Nov 2025 with Ann. Rev. Nucl. Part. Sci. 75 (2025) 377-397.
- Replaced the Tensor Case link (2505.11288) with the direct Inspire record (2921962).
- Added/kept the Collins-Soper kernel paper (2510.26489) and vector current paper (2512.23563) as e-Prints linked to Inspire.

Cross-check tooling

- Created scripts/check_publications.py to parse publications.md, extract Inspire/arXiv IDs, fetch metadata, and report mismatches. Requires network access to run.

Notes

- All Inspire links listed in requests are present in publications.md. Remaining arXiv-only IDs in the email are represented via their Inspire entries.

publications.md format

- YAML front matter with `title: Publications` and `classes: wide`.
- Year blocks are bold lines like `**2025**` (not headings).
- Each entry uses a Markdown list item with three lines: bold authors + `<br/>`, italic title + `<br/>`, then a link line with venue/e-Print and date.
- HTML `<br/>` or `<br>` is used for line breaks inside list items.
