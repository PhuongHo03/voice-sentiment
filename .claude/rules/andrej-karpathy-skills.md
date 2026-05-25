# Claude Code Working Rules

Use these rules to reduce common coding-agent mistakes. They apply unless the user explicitly overrides them.

## 1. Clarify before acting

- State assumptions before non-trivial work.
- If the request has multiple valid meanings, ask or present the interpretations.
- If the task is simple, do it directly; if it is behavior-changing or multi-file, define success criteria first.
- If confused, stop and name the unclear point instead of guessing.

## 2. Read before writing

Before editing code/config/docs:

1. Read the target file.
2. Read immediate callers/config/tests/docs that define expected behavior.
3. Check existing style and naming.
4. Edit only after the current behavior is understood.

Never change code based only on filename assumptions.

## 3. Keep changes surgical

- Touch only files required by the request.
- Do not refactor adjacent code unless required.
- Do not rename, reformat, or reorganize unrelated code.
- Remove only unused code created by your own changes.
- Mention unrelated issues; do not fix them without approval.

Every changed line should trace to the user request.

## 4. Prefer the simplest working solution

- No speculative features.
- No abstractions for one-off logic.
- No compatibility shims unless explicitly needed.
- No extra validation/error handling for impossible internal states.
- Match project conventions over personal preference.

If a simpler approach exists, say so.

## 5. Use tools safely

- Prefer `Read`, `Edit`, `Glob`, `Grep` over shell commands for file work.
- Use shell only for commands that truly need shell/runtime behavior.
- Before destructive or shared-state actions, confirm unless user explicitly authorized scope.
- Never use broad destructive commands against repo root or global system state.
- In this repo, cleanup must stay scoped to FireSafe-owned paths/resources.

## 6. Verify with the smallest relevant check

Pick the lowest-cost check that proves intent:

- Syntax/config change → parser/config validation.
- Script change → parse + targeted unsafe-pattern scan.
- Backend change → focused Maven test/compile when possible.
- Frontend change → typecheck/build or browser check for UI behavior.
- Docs change → read changed section or grep expected anchors.

Do not claim tests pass unless they ran.

## 7. Update project context when behavior changes

If code/config behavior changes:

1. Update the matching `docs/explanations/*-explanation.md`.
2. Update the footer phase if needed.
3. Update `docs/plannings/planning.md` when structure, runtime behavior, ports, services, or explanation files change.

Do not create extra docs unless requested or required by project rules.

## 8. Communicate tersely but completely

- Before tools: say what will be checked/changed.
- During work: report only key findings, blockers, or direction changes.
- Final response: what changed + what was verified + any remaining risk.
- Surface skipped checks explicitly.

## 9. Fail loud

- If verification fails, say exactly what failed.
- If a check was not run, say why.
- If current state conflicts with memory/docs, trust current source and update stale docs if relevant.
- Do not hide uncertainty behind “done”.
