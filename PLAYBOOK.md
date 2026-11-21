# Playbook: agents in a hierarchy

How Claude works on chrono-trader from 21 Nov 2026. The aim is small contexts: every agent reads only what its job
needs, so each step stays cheap and a 5-hour usage window holds real work.

## Why

- A model's cost per step grows with the context it carries. On 11 Nov, reviewers that read PLAN.md and whole modules
  used about 2 points of the 5-hour window a minute each (Fable at high effort), and four at once took the window from
  25% to 90% in 16 minutes with nothing finished (memory: feedback-model-tiering).
- Long sessions pile up history. By 21 Nov the M1 session carried about 380,000 tokens of context, and every step
  there paid for all of it.

## The levels

| Level | Role | Model and effort | Reads | Produces |
|---|---|---|---|---|
| 0 | The owner | | the lead's short reports | decisions, approvals, pushes to master |
| 1 | The lead | Opus, high | the project-status memory, this playbook, reports, digests | briefs, the status memory, questions for the owner |
| 2 | A task session | Opus, high | its brief, and the digests and files the brief names | code, tests, its milestone note, a report file |
| 3 | A subagent | pinned by its type in `.claude/agents/` | its brief | a file, and an answer of at most 15 lines |

- **The lead** is one session at a time. It never reads code or data itself: it sends a scout. It starts one task
  session at a time, checks the outcome cheaply, updates the status memory and asks the owner what only the owner can
  decide. A new lead starts when the current one passes about 30% of its context window, or when a milestone ends.
- **A task session** does one task on its own worktree and branch: a milestone step, a fix or a review. It ends when
  its report is written. The next task gets a fresh session, even inside the same milestone.
- **Subagents** do the parts of a task: lookups, digests, checks, a narrow judgement, a refutation. They run inside
  the lead or a task session, one at a time.

## Subagent types

| Type | Model, effort | Job | Never |
|---|---|---|---|
| `chrono-scout` | Haiku | Find files, functions, lines and facts, and answer with file and line | edit or judge |
| `chrono-digest` | Sonnet, medium | Turn a large file or table into a short digest under `docs/digests/` | judge |
| `chrono-checker` | Sonnet, high | Run tests, queries and greps, reproduce numbers, and report what it ran and what it printed | change code |
| `chrono-judge` | Opus, high | A high-level judgement on one narrow question: the time wall, a leak, the simulator's accounting, a design choice | read beyond its brief |
| `chrono-skeptic` | Opus, high | Try to refute one finding: it stands only if the skeptic's own check shows it | accept a claim without a check |

## Rules

1. **Narrow briefs.** A brief names at most about five files, with line ranges where they help, and the digests to
   use. It never says "read PLAN.md": PLAN's rules reach agents through `docs/digests/plan_rules.md`, whose line
   numbers lead back to the original.
2. **Results go to files.** Agents write findings, digests and reports to files and answer in at most 15 lines. The
   lead opens a file only when it must.
3. **One agent at a time.** Call `get_usage` before every agent. Start none above 75% of the 5-hour window, and no
   judge or skeptic above 55% (one Opus judge used 27 points on 21 Nov). At 85%, save the state (the status memory and the task's note) and stop. The owner's line
   is 90%.
4. **Models by level** (memory: feedback-model-tiering). Never Fable (the owner, 21 Nov). Opus at high effort for
   judgement, building, planning and refuting. Sonnet for digests and mechanical checks. Haiku for lookups. The
   types above pin these; any other agent or workflow call sets `model` and `effort` itself.
5. **Evidence.** Every claim carries a check someone can rerun (AGENTS.md, Facts). Before telling the owner a task is
   done, the lead checks its key claims with cheap commands: `git log`, the test summary line, a file listing.
6. **The owner decides** commits, pushes, merges, new accounts, spending and deletions, and runs pushes to master.
7. **Handoffs go through the status memory.** Every session ends by updating the project-status memory in a few lines
   (done, next, open questions) and its milestone note. A new session starts from the status memory, never from an
   old transcript.

## The flow of one task

1. The lead reads the status memory, picks the next step, checks usage and writes the brief.
2. It starts a task session (fresh context, its own worktree cut from master) with that brief.
3. The task session works: digests for the rules it needs, scouts for lookups, the checker for tests and counts, and a
   judge for a narrow review of any leak-sensitive or accounting code it wrote. It writes its milestone note and a
   report, then ends.
4. The lead checks the report's key claims, updates the status memory, asks the owner for approvals (commit, push,
   merge) and picks the next step.

## Brief template

```
Goal: one sentence. Done when: ...
Read: file:lines, file:lines. Digests: docs/digests/...
Do not read: the whole of PLAN.md, other milestones' notes, raw data beyond counts.
Agents: which types, in what order, one at a time.
Usage: get_usage before each agent; save the state and stop at 85%.
Output: <file path>; reply in at most 15 lines.
Rules that matter here: the one or two AGENTS.md rules this task touches.
```

## Digests

Digests live under `docs/digests/`. `chrono-digest` makes and refreshes them, and they are committed like any doc.
Counts only: no prices and no headlines.
- `plan_rules.md`: every rule and decision in PLAN.md, one line each, with its line numbers.
- `code_map.md`: each module's job and its public functions, one line each, with file and line.
- `store_tables.md`: each Parquet table in `D:\chrono-data\store`, with its columns, its row count and the rule
  behind each column.

Each digest records the commit of its source. Before using one, run `git log -1 -- <source>`; if the source changed
since, refresh the digest first.

## Reviews

A review runs in stages, one agent at a time: the digests first (Sonnet); then a judge for each high-level area
(Opus: the time wall and leaks, then the simulator and the labels); then Opus for the plan's consistency and the news
and reader rules; then checkers for the mechanical areas (prices, identity, the docs' numbers, the licensing greps);
then a skeptic for each area with findings (Opus); then the report. Each agent gets the digests and only its area's
files.
