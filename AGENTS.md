# AI Operations Agent — Agent Instructions

## Project objective
Build a portfolio-quality AI-powered e-commerce operations assistant. The system should answer operational questions using controlled, auditable tools backed by application data. Prioritize correctness, maintainability, security, and explainability over feature count.

## Working principles
- Inspect the existing repository, `pyproject.toml`, `poetry.lock`, documentation, and relevant tests before proposing changes. Do not assume a file or feature exists.
- Preserve existing architecture and conventions unless there is a clear reason to change them.
- Work incrementally. Implement one small, testable scope at a time; do not scaffold unrelated features or rewrite large parts of the project without approval.
- For substantial or ambiguous work, first explain the plan, affected files, trade-offs, and acceptance criteria, and wait for approval before implementation.
- Ask questions when requirements or business rules are unclear. State assumptions explicitly.
- Do not silently install packages, alter dependency versions, run destructive commands, delete data, or change environment configuration.
- Never claim tests passed unless they were actually run. Report commands and results accurately.

## Communication
- Communicate with the developer in Traditional Chinese (繁體中文, Taiwan usage).
- Keep code identifiers, file names, commit messages, and technical terminology in clear, conventional English.
- Before coding, briefly state the goal and proposed approach. After coding, summarize changes, reasons, tests, and any remaining risks or follow-up work.
- Explain nontrivial design choices so the developer can learn from and review the implementation.

## Technology and environment
- Python 3.12; manage Python dependencies with Poetry and the project-local `.venv`.
- Use `poetry add` / `poetry add --group dev` for dependency changes, `poetry install` for installation, and `poetry run ...` for project commands.
- Never use `pip install` directly into an arbitrary environment or create extra tool environments such as `.poetry-tool` without explicit approval.
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.x, pytest. Prefer type annotations and clear module boundaries.
- Frontend: React with Vite, when frontend work is in scope.
- Database: follow the repository's current database configuration; SQLite may be used in early development, with PostgreSQL and Alembic introduced when planned. Do not switch databases unilaterally.
- LLM integration: Gemini, behind a replaceable service interface. Do not couple domain logic directly to provider SDK calls.
- Docker Compose is optional until the relevant phase requires it.
- Inspect existing project scripts and configuration before choosing commands or paths.

## Architecture and code quality
- Separate API routes, request/response schemas, business services, persistence, and external LLM integration.
- Keep route handlers thin; business logic belongs in services or domain modules.
- Use Pydantic schemas to validate API payloads and tool arguments. Use SQLAlchemy models for persistence.
- Avoid unnecessary abstraction, generic frameworks, or premature optimization.
- Prefer deterministic, independently testable business logic over LLM-generated calculations.
- Add concise comments only where intent is not obvious. Do not introduce unrelated formatting or refactors.
- Maintain consistent error handling and meaningful logs without leaking secrets or sensitive data.

## AI agent and tool-calling safety
- Expose only explicitly registered, allowlisted tools. Never allow the LLM to execute arbitrary Python, shell commands, or SQL.
- Validate all tool arguments with Pydantic before execution; enforce business constraints and reasonable limits.
- Treat model outputs as untrusted input. The application, not the model, decides which operations are permitted.
- Keep read-only tools separate from any future state-changing tools. Require explicit user confirmation for consequential or write operations.
- Record agent runs and tool executions, including status, tool name, validated arguments where appropriate, execution outcome, timestamps, and sanitized errors. Avoid storing credentials or unnecessary sensitive data.
- Prevent unbounded tool loops by enforcing execution limits and timeouts.
- Keep inventory, sales summaries, and restock calculations grounded in database records; never invent business figures.
- Planned example tools: `get_low_stock_products`, `get_sales_summary`, `calculate_restock`, and `export_report`. Implement only when their phase is approved.

## Data and migrations
- Use database transactions for multi-step writes and maintain referential integrity.
- Do not drop tables, reset databases, or overwrite user data without explicit approval.
- When Alembic is introduced, create and review migrations rather than silently changing schemas.
- Keep development seed data clearly separate from production-like data.

## Testing and verification
- Add or update focused pytest tests for new backend behavior and bug fixes.
- Cover normal cases, validation failures, boundaries, and relevant error paths.
- Mock external LLM calls and other network dependencies in automated tests; tests must not require paid API calls.
- For tool calling, test allowlisting, invalid arguments, execution failures, and audit logging.
- Run the smallest relevant test suite first; run broader checks when appropriate.
- If tests cannot run, explain why and provide the exact command to verify later.

## Security and configuration
- Never hardcode or commit API keys, passwords, tokens, or connection strings.
- Use environment variables and an ignored `.env` file for local secrets; provide `.env.example` with placeholders when needed.
- Do not log secrets or expose raw internal exceptions in API responses.
- Validate and constrain any export file paths, filters, and query parameters.
- Avoid new external services or dependencies without explaining their purpose and obtaining approval.

## Git and scope control
- Respect `.gitignore`; never commit `.venv`, `.poetry-tool`, `.poetry-cache`, `.env`, caches, generated reports, or local databases unless explicitly intended.
- Keep changes narrowly scoped. Do not modify unrelated files.
- Do not commit, push, force-push, reset, rebase, or delete branches unless explicitly requested.
- Update `README.md` or relevant docs when setup steps, commands, architecture, or behavior change.

## Definition of done
A task is complete only when:
1. The requested behavior is implemented without unrelated changes.
2. Input validation, failure handling, and security implications have been considered.
3. Relevant tests are added or updated and results are reported truthfully.
4. Documentation is updated if behavior or setup changed.
5. The developer receives a Traditional Chinese summary of modified files, key decisions, verification commands/results, and remaining limitations.

## Initial development priority
Start with a runnable, tested FastAPI backend and a clear project structure. Establish data models and basic APIs before integrating Gemini tool calling. Introduce the frontend, migrations, and deployment infrastructure incrementally, based on the approved project plan.
