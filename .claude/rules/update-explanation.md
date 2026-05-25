# Rule: Keep Explanation Docs Current

`docs/explanations/*-explanation.md` files describe how each project area works. Keep them aligned with source changes so future Claude Code sessions can understand the repo quickly.

## Documentation mapping

Do not hard-code the project folder list in this rule. Derive the matching explanation file from the current repository state:

1. List existing `docs/explanations/*-explanation.md` files.
2. Match the changed area to the explanation file with the same area name, e.g. `<area>/` ↔ `docs/explanations/<area>-explanation.md`.
3. For repo-level runtime/config changes, update the explanation file whose name and content describe infrastructure, setup, orchestration, or runtime operations.
4. For a new major service/tool, create `docs/explanations/<area>-explanation.md` only when no existing explanation file covers it.
5. If a change touches multiple areas, update each matching explanation file.

Source of truth is the current directory names and existing explanation files, not this rule file.

## When to update

Update explanation docs when a change affects future understanding of structure, behavior, operations, or integration.

Required updates:

- Add/remove/rename important files or folders.
- Add/remove/change public APIs, routes, endpoints, CLI args, env vars, ports, or generated files.
- Change runtime behavior: startup, shutdown, cleanup, logs, process ownership, Docker resources, safety scope.
- Change business logic or cross-service flow.
- Add/remove dependencies in `pom.xml`, `package.json`, or `requirements.txt`.
- Change DB migrations, seed data, tables, indexes, or default accounts.
- Change auth/security, secrets handling, or credentials policy.
- Change AI model selection, model path fallback, detection flow, storage upload, alert flow, or worker threading.
- Add runner scripts or change how local tools are executed.

Usually skip updates for:

- Tiny bug fixes that do not change external behavior or future-session context.
- Pure formatting changes.
- Internal refactors with no name/signature/behavior/config/runtime change.
- Log text changes that do not alter operations.
- Test-only changes unless they document important behavior or setup.

When unsure, prefer a short doc update over stale docs.

## What to update inside an explanation file

### 1. Structure tree

If files/folders changed, update the ASCII tree.

Keep entries short:

```text
├── service.py          ← HTTP API: health/start/stop/status/stream
└── src/config.py       ← Runtime/model config
```

Do not list generated/local artifacts unless users must know they are created/ignored.

### 2. Behavior sections

Update the section that explains the changed behavior:

- Request/response flow.
- Runtime lifecycle.
- Worker/thread flow.
- Storage/DB/queue flow.
- Cleanup behavior.
- Env/config behavior.
- CLI usage.

Prefer concise source-derived descriptions. Do not invent future features.

### 3. Tables and examples

Update tables/code blocks when the source changes:

- Endpoint tables.
- CLI arguments.
- Env var tables.
- Dependency tables.
- Port/resource tables.
- Example commands.
- Payload examples.

Examples must match current source defaults.

### 4. Footer

Each explanation file ends with a phase/status footer, for example:

```markdown
*Tài liệu phản ánh trạng thái backend tại **Giai đoạn 6**. ...*
```

Update the footer when:

- The file content changes materially.
- The project phase changes.
- The footer describes outdated behavior.

Keep the existing language/style of the doc unless the user asks to translate it.

## Order of operations

For code/config behavior changes:

1. Implement the source change.
2. Verify the source change with the smallest relevant check.
3. Update matching explanation file(s).
4. Check the updated section/footer.
5. Update `docs/plannings/planning.md` if structure, phase, runtime behavior, ports, services, or explanation files changed.
6. Final response must mention docs/planning updates, or explicitly say they were not needed.

## Consistency rules

- Source of truth is current code/config, not older docs.
- Do not document behavior that is not implemented.
- Do not leave old filenames, old ports, old service names, or old cleanup behavior in docs.
- Do not create new documentation files unless a new major area needs one or the user asks.
- Keep docs explanatory, not a chronological changelog.
- Preserve project language/style in existing docs unless asked otherwise.
