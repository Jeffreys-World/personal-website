# Design System — Jeffrey De La Cruz Portfolio

## Product Context
- **What this is:** A single-page personal portfolio whose job is to get Jeffrey De La Cruz hired as a software engineer. It is structured as a case study, not a résumé.
- **Who it's for:** Hiring managers and technical recruiters at NYC tech companies, reading for roughly 45 seconds before deciding whether to open GitHub or book a call.
- **Space/industry:** Developer portfolios. A category saturated with clones of `brittanychiang.com` v4 (fixed sidebar, `#0f172a` navy, `#64ffda` mint, Inter, numbered nav).
- **Project type:** Marketing site / editorial single-page.

## The Memorable Thing
**"He finds the real problem."**

Every decision in this document serves that one sentence. It is backed by evidence, not
asserted: the ticket-triage case study opens with a five-whys teardown, reports 41.6%
overall accuracy without flinching, and explains why top-severity recall was deliberately
optimized over precision. That intellectual honesty is the product. The design exists to
give it room.

## Aesthetic Direction
- **Direction:** Editorial, with industrial precision.
- **Decoration level:** Minimal. Typography and whitespace do all the work. No gradients, no blobs, no texture.
- **Mood:** A well-typeset technical report. Something you'd read, not something you'd skim. Warm rather than clinical, precise rather than decorative.
- **Why:** Editorial layout is the design language of investigation and argument (magazines, long-form journalism, research papers). Card grids are the language of catalogues. Jeffrey's advantage is depth over breadth, so the page must be shaped like an argument.
- **Reference points:** [leerob.com](https://leerob.com) for content-first restraint; [brittanychiang.com](https://brittanychiang.com) as the anti-reference to deliberately break from.

## Typography
- **Display/Hero:** **Fraunces** (variable: `opsz` 9–144, `wght` 400–700) — an old-style serif with real character and optical sizing. Editorial and warm. Almost unused in this category, which is the point.
- **Body/UI:** **Instrument Sans** (400/500/600) — slightly condensed grotesque, excellent at small sizes, sits cleanly under Fraunces without competing.
- **Data/Tables:** **JetBrains Mono** with `font-variant-numeric: tabular-nums` — for ticket scores, metrics tables, and the queue demo. Numbers must align in columns.
- **Code:** JetBrains Mono (same face).
- **Explicitly rejected:** Inter (what the site used, and the single most convergent choice in the category), Space Grotesk (the AI-default "safe alternative to Inter"), Roboto, Poppins, Montserrat.
- **Loading:** Google Fonts, single combined request, `display=swap`, with `preconnect` to both `fonts.googleapis.com` and `fonts.gstatic.com`.

### Scale
| Level | Size | Face | Leading | Tracking |
|---|---|---|---|---|
| Display | `clamp(2.5rem, 6.4vw, 5rem)` | Fraunces 600 | 1.04 | -0.022em |
| H2 | `clamp(1.75rem, 3.2vw, 2.5rem)` | Fraunces 600 | 1.12 | -0.018em |
| H3 | `1.3125rem` | Fraunces 600 | 1.25 | -0.01em |
| Lede | `clamp(1.0625rem, 1.5vw, 1.25rem)` | Instrument Sans 400 | 1.62 | 0 |
| Body | `1.0625rem` | Instrument Sans 400 | 1.72 | 0 |
| Small | `0.875rem` | Instrument Sans 400 | 1.6 | 0 |
| Micro/Label | `0.75rem` | Instrument Sans 500 | 1.4 | 0.12em, uppercase |
| Data | `0.8125rem` | JetBrains Mono 400 | 1.6 | 0, tabular-nums |

## Color
- **Approach:** Restrained. Warm neutrals carry the page; one accent, used rarely and only where urgency is the actual meaning.

### Light (default)
| Token | Hex | Usage |
|---|---|---|
| `--bg` | `#FAF7F2` | Warm paper. The page. |
| `--surface` | `#F3EFE8` | Recessed panels, code blocks, the queue demo. |
| `--ink` | `#14110D` | Headings. Near-black with warmth, never pure `#000`. |
| `--body` | `#4A443C` | Body copy. |
| `--muted` | `#726A60` | Labels, metadata, captions. |
| `--rule` | `#DED7CB` | Hairlines and borders. |
| `--accent` | `#C1300B` | Signal red. 5.3:1 on `--bg`, 5.0:1 on `--surface`. |

### Dark
| Token | Hex | Usage |
|---|---|---|
| `--bg` | `#14120F` | |
| `--surface` | `#1E1B17` | |
| `--ink` | `#F5F1EA` | |
| `--body` | `#B5AEA3` | |
| `--muted` | `#8C8477` | |
| `--rule` | `#2E2A24` | |
| `--accent` | `#FF6B3D` | Lightened and desaturated ~15% for dark surfaces. |

### Semantic — severity ramp
Lifted directly from the ticket-triage product's own 🔴🟠🟡🟢 scale. The color system
*is* the thesis: this palette is about deciding what matters first.

| Level | Light | Dark |
|---|---|---|
| Critical | `#C1300B` | `#FF6B3D` |
| High | `#B4600A` | `#E0913A` |
| Medium | `#8A6D00` | `#C9A83C` |
| Low | `#3F6B4A` | `#6FA980` |

- **Accent discipline:** red means urgency, never decoration. It appears on the hero's key phrase, active nav state, link underlines on hover, and the Critical severity marker. It never lands on a neutral affordance or a generic button.
- **Dark mode strategy:** surfaces are redesigned rather than inverted; accent saturation reduced ~15%; rules lightened relative to background rather than darkened.

## Spacing
- **Base unit:** 8px.
- **Density:** Spacious. Editorial layouts need air, and long-form reading rewards it.
- **Scale:** `2xs(4) xs(8) sm(12) md(16) lg(24) xl(32) 2xl(48) 3xl(64) 4xl(96) 5xl(128)`

## Layout
- **Approach:** Creative-editorial. Single column with an asymmetric margin-label column.
- **Structure:** On ≥900px, each section is a `8.5rem 1fr` grid. Section labels (`01 / Selected work`) sit sticky in the left margin like scholarly sidenotes. This delivers editorial character *without* the cloned fixed sidebar, and reclaims the 34vw that sidebar was wasting.
- **Grid:** Single column below 900px; label + content above.
- **Max content width:** `1120px` shell, `68ch` measure for prose.
- **Border radius:** `0 / 2px / 4px` only. The old system's 10px cards and 999px pills are the template's fingerprint. Tight radii read as engineering precision.

## Motion
- **Approach:** Intentional. Motion clarifies structure; it never performs.
- **Easing:** enter `cubic-bezier(0.22, 1, 0.36, 1)`, exit `ease-in`, move `ease-in-out`.
- **Duration:** micro 100ms / short 180ms / medium 320ms / long 520ms.
- **Patterns:** scroll-reveal fires once per element with a stagger; sticky header reveals after the hero clears; scroll-progress bar tracks document position; hovers are 180ms and mechanical (no bounce, no scale-up).
- **Forbidden:** parallax, scroll-jacking, bouncy spring easing, entrance animations that replay on every scroll-by.
- **Reduced motion:** `prefers-reduced-motion: reduce` disables all transforms, reveals, and smooth scroll. Content is visible at rest, always.

## Deliberate Risks
| # | Risk | Gain | Cost |
|---|---|---|---|
| 1 | Light warm paper as default, not dark navy | The category is ~90% dark; this reads instantly as not-a-template and is better for long-form | Loses the "hacker" register some devs prefer |
| 2 | Signal red accent instead of mint/cyan/violet | Palette carries the urgency thesis; nobody in the category uses red | Red reads as "error", so it must stay rare |
| 3 | Serif display face (Fraunces) | Reads as thinking, not as template | Some read serifs as less technical |
| 4 | Hero leads with the problem, not the name | Proves the memorable thing in 3 seconds instead of claiming it | A recruiter scanning for a job title reads one line first |

## Anti-Patterns (never reintroduce)
- Purple/violet gradients as accent
- 3-column feature grid with icons in colored circles
- Centered-everything with uniform spacing
- Uniform bubbly border-radius; pill-shaped tag chips
- Gradient buttons as primary CTA
- `system-ui` / `-apple-system` as display or body face
- Inter or Space Grotesk as a primary face
- Fabricated employers, projects, or metrics

## Content Integrity Rule
This site states only what is verifiable. Every metric on the page traces to
`Customer Support Specialist Week 3 and 4/results/evaluation.md`. Employment history that
does not exist is omitted rather than invented. If a fact is unknown, it is left as a
marked placeholder in the HTML, never filled with plausible fiction.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-29 | Initial design system created | `/design-consultation`, informed by WebSearch on 2026 hiring-manager expectations plus browse screenshots of brittanychiang.com and leerob.com |
| 2026-07-29 | Abandoned the Brittany Chiang v4 clone structure | The site was a near-exact copy (fixed sidebar, navy/mint, numbered nav, tag pills). Structurally wrong for two deep projects, and instantly recognizable to recruiters |
| 2026-07-29 | Removed fabricated experience and projects | Two invented employers and two invented projects were listed while two real projects sat unlinked. Fabrication is the single biggest risk on a portfolio |
| 2026-07-29 | Severity ramp adopted as the semantic palette | The triage product's own 🔴🟠🟡🟢 scale, making the color system an expression of the work rather than decoration |
