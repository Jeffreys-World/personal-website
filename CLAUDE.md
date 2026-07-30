# Repository Scope

**This repo is the personal website only.** It holds `index.html`, `script.js`, `style.css`,
`DESIGN.md`, and the Week 2 technical assessment. Nothing else.

**The Customer Support Specialist project does not live here.** It has its own repo:

    https://github.com/Jeffreys-World/Customer-Support-Specialist-Project

A stale copy of that project was checked into this repo as
`Customer Support Specialist Week 3 and 4/` and removed on 2026-07-30. It had drifted a full
architecture behind its own repo — no `ui/` package, no `prediction_model.py` — and work done
in each copy was invisible to the other. That is the failure this separation exists to prevent.

Rules:

- Never re-add project source, data, or notebooks to this repo. If the website needs to cite a
  project result, link to the project repo by URL — do not vendor the file.
- Work on the project in a clone of its own repo, as a sibling directory, never nested inside
  this one. A repo inside a repo is what caused the drift.
- If asked to change "the customer support project" while this repo is the working directory,
  stop and say it belongs in the other repo. Do not create a local copy to work around it.

# gstack

Use the `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__` tools.

Available gstack skills: `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/setup-gbrain`, `/retro`, `/investigate`, `/document-release`, `/document-generate`, `/codex`, `/cso`, `/autoplan`, `/plan-devex-review`, `/devex-review`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

## Content Integrity
This portfolio states only verifiable facts. Never add employers, job titles, projects,
dates, or metrics that cannot be traced to a file in this repo. If a fact is unknown,
leave a marked placeholder — never fill it with plausible fiction.
