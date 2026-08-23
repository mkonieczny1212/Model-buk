# Global Agent Instructions (Codex)

> Install to `~/.codex/AGENTS.md` for global scope, or drop into a project root
> for project-only scope. Adapted from a Claude Code `CLAUDE.md` setup.

---

## Session & phase startup ritual

At the start of every new session OR when beginning a new project phase (e.g.
switching from planning to implementation, from coding to testing), the agent MUST:

1. **Review the available skills/reference docs and MCP servers**
2. **Identify which ones are relevant to the upcoming work**
3. **Present a short proposal** to the user in this format:

> "For this phase I suggest using:
> - **[Skill/MCP name]** — [one sentence why it's useful here]
> - **[Skill/MCP name]** — [one sentence why it's useful here]
> Should I proceed with these?"

Wait for the user's confirmation before starting. This keeps the user in control
and ensures the best tools are always being used intentionally.

---

## How "skills" work in Codex

Codex has no built-in skill-invocation tool. Skills here are plain markdown
guides stored under `~/.codex/skills/<name>/SKILL.md`.

**Rule:** before acting on a task, check whether a relevant skill file exists.
If it does, **read it fully and follow it** before writing code, then state
"Using `<skill>` to <purpose>". Treat that as the equivalent of invoking it.

---

## Skills — when to use automatically

Scan for a matching skill and use it if there's even a 1% chance it applies.

### Design & Frontend
- **Any UI/UX, design, layout, animation, component work** → start with
  `ui-ux-pro-max`. Many design skills overlap — see **"Skill tiers &
  tie-breakers"** below to choose among them (and when to ask the user).
- **Generating visual art or illustrations** → `canvas-design` or Nakkas MCP (SVG)
- **Image editing tasks** → Photopea MCP

### Development workflow
- **Starting any new feature or task** → `superpowers:brainstorming` if creative
  decisions are needed
- **Writing an implementation plan** → `superpowers:writing-plans`
- **Executing a written plan** → `superpowers:executing-plans`
- **Any bug, test failure, or unexpected behavior** →
  `superpowers:systematic-debugging`
- **Before declaring any task complete** →
  `superpowers:verification-before-completion`
- **Code review requested** → `superpowers:requesting-code-review`
- **2+ independent tasks** → `superpowers:dispatching-parallel-agents`

### Documents & files
- **Any .xlsx or spreadsheet** → `document-skills:xlsx`
- **Any .docx or Word file** → `document-skills:docx`
- **Any .pptx or PowerPoint file** → `document-skills:pptx`
- **Any .pdf file** → `document-skills:pdf`

### Diagrams & architecture
- **Flowcharts, sequence diagrams, ERDs, architecture visuals** → AI Diagram
  Maker MCP

### Data visualization — d3.js
- **Proactively consider d3** whenever a task involves: custom/interactive
  charts, graphs, data-driven visuals, dashboards, force/network diagrams, maps,
  or any bespoke visualization a static chart or diagram tool can't cover.
- **Before using d3, think about *where* it's needed and ASK the user**, e.g.:
  > "This looks like a good fit for d3. How should I make it available in
  > **[project]**? Options: `npm install d3` in the project (recommended), or a
  > CDN `<script>` for a quick browser prototype."
- A global npm install is **not** auto-importable in projects (Node resolves deps
  from local `node_modules`), so d3 must be added per-project. Never assume it's
  importable — confirm the install method first.
- For simple/standard charts, prefer lighter options (CDN, or a higher-level lib)
  and say so; reserve d3 for cases that genuinely need its low-level control.

---

## Skill tiers & tie-breakers (overlap resolution)

Many skills overlap. Nothing is removed — instead, resolve competition with these
tiers.

**Meta-rule:** Default to the **Primary** for a job and state which skill you're
using ("Using X to …"). When 2+ options genuinely fit **and the choice changes
the output** — especially visual **style direction** — briefly **ASK the user
which to use** before proceeding, consistent with the session startup ritual.
When the choice is obvious, just pick the Primary.

### Frontend / UI design
- **Primary — plan, build, or review any UI** → `ui-ux-pro-max` (spans many
  styles, palettes, stacks incl. shadcn/ui).
- **Build brand-new components from scratch** → `frontend-design`.
- **Quality / audit pass (after building, before "done")** → `impeccable` (its
  `audit`/`critique`/`polish` detectors); pairs with
  `verification-before-completion`.
- **Upgrading or redesigning an existing site/app** → `redesign-skill`.
- **Style-specific skills — use ONLY when that exact aesthetic is requested,
  otherwise ASK which direction:** `minimalist-skill`, `brutalist-skill`,
  `soft-skill`, `gpt-tasteskill`, `stitch-skill`, `taste-skill`. Do NOT auto-fire
  these — `ui-ux-pro-max` already covers these styles.
- **Components on demand** → `shadcn` MCP (live registry code/examples) or
  `magic` MCP (21st.dev inspiration; `component_inspiration` before
  `component_builder`).

### Design reference images (mockups before coding) — pick by medium
- Website / landing comps → `imagegen-frontend-web` (one image per section)
- Mobile app screens → `imagegen-frontend-mobile`
- Generate a design image, then build to match it → `image-to-code-skill`
- Brand identity / guidelines boards → `brandkit`

### Web data (Firecrawl is credit-limited — always ask first; prefer free search)
- General search → built-in web search (free, default).
- Scrape one known URL → `firecrawl-scrape`.
- Local file → markdown → `firecrawl-parse`.
- Multi-page structured JSON extraction → `firecrawl-agent` / firecrawl extract.
- `firecrawl-build-*` skills → **only** when embedding Firecrawl into product
  code, never for research.

### Coding process (process skill sets the approach → implementation skill executes)
- **Primary framework** → Superpowers: `brainstorming`, `writing-plans` /
  `executing-plans`, `systematic-debugging`,
  `verification-before-completion`, `requesting-code-review`.
- **Mindset check on non-trivial edits** → `karpathy-guidelines` (surgical
  changes, surface assumptions, verifiable success criteria) — complements
  Superpowers, does not replace it.

### Context-engineering suite (bdi-mental-states, latent-briefing, harness-engineering, memory-systems, evaluation, etc.)
- Use **only** for explicit context/agent-engineering work. Do NOT trigger for
  normal UI or document tasks.

---

## MCP usage rules

### Firecrawl — ALWAYS ASK BEFORE USE (credit-limited)
- **NEVER use Firecrawl without explicit user confirmation first**
- Before any Firecrawl call, say: "I'd like to use Firecrawl to [reason]. This
  uses credits — should I proceed?"
- Wait for a "yes" / "go ahead" before calling any Firecrawl tool
- Use free/built-in web search for all general queries — Firecrawl is only for:
  - Deep scraping of a specific URL (clean markdown extraction)
  - Crawling multiple pages of a site
  - Structured data extraction that plain search cannot provide
- Always prefer firecrawl **search** over **scrape** if a URL isn't known yet

### Magic MCP — use for UI components
- When scaffolding a new React/Next.js component, check Magic first for inspiration
- Use `component_inspiration` before `component_builder` — browse before generating
- Good for: pricing tables, navbars, cards, testimonials, hero sections, CTAs

### shadcn MCP — use for shadcn/ui components (live registry)
- Use when working in a React/Next.js project that uses (or should use) shadcn/ui
- Search the registry and pull exact, current component code/examples rather than
  recalling from memory
- Best inside a real project with a `components.json`; run
  `npx shadcn@latest init` there first if missing
- Complements Magic MCP: shadcn = canonical shadcn/ui primitives; Magic/21st.dev
  = broader community inspiration

### Playwright — use for visual verification
- After making UI changes, offer to use Playwright to screenshot and verify
- Use for automated testing of user flows
- Prefer Playwright over Chrome DevTools for automation tasks

### Chrome DevTools — use for debugging
- Use when inspecting a live running app (console errors, network requests)
- Requires Chrome launched with `--remote-debugging-port=9222`

### Nakkas — use for SVG/decorative art
- Use for generating decorative SVG elements, icons, backgrounds
- Fully local, no credits consumed — use freely

### AI Diagram Maker — use for diagrams
- Use whenever a visual diagram would clarify architecture, flow, or process
- Good for client deliverables and technical explanations

### Photopea — use for image editing
- Use when the user needs to edit, composite, or process images
- No credits consumed, runs locally via browser

---

## General behavior

- Always prefer reading existing code before writing new code
- Never assume — check files before modifying them
- When multiple approaches exist, briefly explain the trade-offs
- Commit messages should be descriptive and focus on "why" not "what"
- Never commit unless explicitly asked
- Ask before running destructive operations

---

## Reference links & assets (bookmarks)

Curated external resources to reach for when relevant. These are
references/libraries, not installed tools.

### Data & APIs
- **Public APIs** — https://github.com/public-apis/public-apis — huge curated
  list of free public APIs by category (finance, geo, data, etc.). Use to find a
  live data source for dashboards, prototypes, or demos.
- **Awesome Public Datasets** —
  https://github.com/awesomedata/awesome-public-datasets — curated open datasets
  across domains. Use for research and realistic data in d3 visualizations.

### Frontend & design
- **Phosphor Icons** — https://phosphoricons.com — flexible open-source icon
  family (6 weights, MIT). Not globally installable; add **per project**:
  React → `npm install @phosphor-icons/react`; plain web →
  `npm install @phosphor-icons/web`. Preferred icon set for web/app UI.
- **Animista** — https://animista.net — interactive CSS animation generator (pick
  an effect, copy the CSS). Use as a reference to eyeball a motion effect; CSS
  keyframes can also be hand-written directly.

### Automation & workflows
- **n8n workflow templates** — https://github.com/zie619/n8n-workflows — 4,300+
  ready-made n8n automation workflows (JSON) across 15 categories. NOT an agent
  tool — these import into a running **n8n** instance. Reach for this whenever a
  task calls for n8n automation templates. Browse at
  zie619.github.io/n8n-workflows.

### Agent tooling (reference only — deliberately NOT installed)
- **Ruflo** — https://github.com/ruvnet/ruflo — heavyweight multi-agent
  meta-harness (100+ agents, 60+ commands, vector memory, agent federation). Kept
  as a bookmark, **not installed on purpose**: it overlaps native agent
  subagents/workflows + Superpowers and adds large complexity. Revisit only if a
  project genuinely needs large-scale multi-agent orchestration.
