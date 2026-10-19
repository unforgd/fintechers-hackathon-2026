# AGENTS.md — submitted repo

**Rules for every AI agent working here** (Claude Code, Antigravity, others). This repo holds the code the jury judges.
Specs, decisions, status and the full conventions live in the team's working repo
(`../00_repo`, private: github.com/mlomovskoy/unforgd-fintechers-hackathon-2026): read its `AGENTS.md` and
`docs/STATUS.md` before starting. Every rule there applies here too. The essentials:

1. **Code freeze: Tue 20 Oct 2026, 13:30 CEST.** No commits after it.
2. **Only work done during the event is judged.** Start point: tag `hackathon-start`. Never move or delete it.
   Earlier material comes in only through a separate `import:` commit naming its source, listed in the README.
   **Never copy code from Konstantin's PartChainDemo / partpassport-demo** (he is not on this team).
3. **Synthetic data only.** No real personal data, client documents or production systems.
4. **Secrets only in `.env`** (git-ignored). Never commit, print or log a key. AWS access is SSO or IAM roles; no access keys.
5. **Keep README current:** "What existed before" and "Built during the hackathon" are required by the rules.
6. **Only Maxim pushes to this repo** (the only writer in the `unforgd` org). Others contribute through the working repo.
7. **Commit or push only when your user asks.** Conventional prefixes (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `import:`).
   A commit that implements a task names the task ID from `../00_repo/docs/specs/tasks.md`.
