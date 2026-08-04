<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **viraldy** (18551 symbols, 31863 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Default Workflow

- **Default to GitNexus for code understanding.** For non-trivial code questions, debugging, review, refactoring, or feature work, check GitNexus first before relying on text search alone.
- **Use `query` before broad search.** When looking for a feature, route, flow, module, or concept, start with `query({search_query: "..."})`, then use file reads or `rg` to inspect exact implementation details.
- **Use `context` before editing a known symbol.** When the target function, class, method, route handler, or shared constant is known, run `context({name: "..."})` to understand callers, callees, and execution flows.
- **Use `impact` before modifying behavior.** Before changing a symbol's logic, signature, return shape, validation, persistence, or API contract, run `impact({target: "...", direction: "upstream"})` and report the risk.
- **Use `trace` for cross-layer questions.** For frontend-to-backend, endpoint-to-service, job-to-worker, or provider flow questions, use `trace` when the start and end symbols are known.
- **Use `detect_changes` after implementation.** Before finalizing meaningful code changes, run `detect_changes()` and compare the affected flows with the intended scope.
- If the GitNexus MCP tools are unavailable in the current agent session, use the local CLI fallback: `node .gitnexus/run.cjs query`, `context`, `impact`, `trace`, and `detect_changes`.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/viraldy/context` | Codebase overview, check index freshness |
| `gitnexus://repo/viraldy/clusters` | All functional areas |
| `gitnexus://repo/viraldy/processes` | All execution flows |
| `gitnexus://repo/viraldy/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
