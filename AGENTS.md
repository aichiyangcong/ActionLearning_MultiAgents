# AGENTS.md

## Global Rules
- Code style: consistent with existing (run prettier/eslint)
- No new deps without reason + approval
- Tests: aim 80%+ coverage for core logic
- Commits: atomic, descriptive

## Roles
Team Lead → overall
Architect → design & plan
Frontend → client-side
Backend → server-side
Logic Engineer → core intelligence (prompts, flows, memory)
Tester → quality & reliability

## Routing
Keyword match preferred:
- frontend/ui/chat → Frontend
- api/server/db/streaming → Backend
- prompt/logic/agent/memory/reasoning → Logic Engineer
- test/bug/case → Tester
- unsure/big → Architect plan → Lead assigns

## Workflow Template
- Lead: clarify requirement
- Architect: output plan + files list
- Assign → implement → test → review → commit