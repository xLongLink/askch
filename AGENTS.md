# AGENTS Instructions

AskCH is an open-source AI chatbot designed to help users explore, understand, and interact with Swiss data through natural language.
The project aims to make information about Switzerland more accessible by allowing users to ask questions and receive clear, relevant, and easy-to-understand answers.

## Project guidelines
- PREFER simple, maintainable, conventional solutions.
- After creating a merge request, DO return the local checkout to its previous branch.
- When they simplify implementation, PREFER the standard library or established libraries over handwritten implementations.
- DO validate inputs at system boundaries.
- DO test actual behavior instead of duplicating production logic in tests.
- Unless the user explicitly requests tests, DON'T add them.
- When duplication improves clarity, PREFER explicit duplication to helpers or shared code.
- Where practical, PREFER real implementations and explicit dependency boundaries to mocks or global runtime-state changes.
- NEVER EVER EVER add any new comment in markdown files, only fix existing one.
- NEVER create new markdown files unless indicated from the user.

## Apertus Simplification Guidelines

When reviewing or simplifying tasks for Apertus, prioritize short instructions, small tool schemas, and predictable workflows.

- PREFER application code over model reasoning for arithmetic, filtering, date handling, and deterministic formatting.
- DO remove contradictory or duplicated instructions.
- DO give tools clear names, simple inputs, sensible defaults, and concise outputs.
- DO avoid unnecessary tool calls and repeated data.
- DO return clear errors and ask for clarification instead of guessing.
- DO preserve validation, source attribution, permissions, and safety checks.
- AVOID new abstractions, speculative features, and cosmetic refactoring.

Review workflow:
1. Inspect the code before recommending changes.
2. Return five actionable findings, or fewer when the code does not support five. NEVER invent findings to fill the list.
3. For each finding, include the exact file path and line range, the current problem and unnecessary work it creates, the smallest safe change, behavior or compatibility changes, and confidence (High, Medium, or Low).
4. Wait for the user to select findings before editing, unless they have already authorized specific changes.

After implementation:
- DO run relevant existing tests, formatting, linting, type checking, and the build where applicable.
- Unless the user explicitly requests tests, DON'T add them.
- DO review the diff for further simplification.
- DO summarize changes, verification results, and remaining limitations.
- DON'T claim improved model quality unless it was evaluated with Apertus.

## Python Guidelines

- AVOID renaming imports.
- AVOID using the `as exc`
- PREFER the simplest correct implementation. AVOID features needed only for hypothetical future use.
- DO construct class instances in separate, multi-line assignments before invoking their methods.
- PREFER idiomatic Python and readability over efficiency.
- DO use clear domain names.
- PREFER single-word Python filenames.
- DO use `Protocol` for behavioral interfaces and dependency contracts.
- DO represent application state with typed models, enums, or structured objects.
- PREFER namespaced module APIs to importing many related functions directly.
- DO use exceptions for genuine errors.
- AVOID unnecessary `try`/`except` blocks.
- DO store asynchronous query results in a named variable before calling `.all()`, `.one_or_none()`, or similar result methods.
- DO use `collections.abc.Sequence` instead of `list` for read-only query result return types.
- DO declare `response_model` on FastAPI routes and let FastAPI validate responses.
- DO group Pydantic fields into commented sections.
- Within each section, DO order fields from the shortest name to the longest name.
- DO add a descriptive `# ...` comment before each logic block, with one blank line before the comment.

## JavaScript / TypeScript Guidelines

- DO use React and shadcn/ui for the web frontend. DON'T use Astryx.
- DON'T use browsers or browser automation to inspect or verify changes.
- DO inspect source and run code-level checks instead.
- PREFER precise types, generics, `unknown` with narrowing, discriminated unions, and established validation libraries.
- Unless extraction improves reuse, readability, or separation of concerns, PREFER inline logic.
- AVOID single-use helpers, unnecessary abstractions, duplicated state, dead code, or unnecessarily complex solutions.
- DO keep changes small and follow existing project conventions.
- DO add JSDoc to JavaScript functions.
- When types do not make behavior clear, DO add JSDoc to TypeScript functions.
- DO add a descriptive `// ...` comment before each logic block, with one blank line before the comment.
- DO keep each lookup and its immediate existence check together, with the block comment before the lookup.
- DO use clear domain terms, concise filenames, consistent plural model names, and namespaced APIs for related factories or facades.
- Unless renaming improves clarity, AVOID renaming imports.
- DO inline simple, single-use prop types and `className` expressions.
- When prop types are shared or complex, DO keep named prop types.
- DO extract components only for meaningful UI boundaries.
- AVOID unnecessary cards, duplicated derived state, and effects that do not synchronize with external systems.
- PREFER explicit async/await.
- DO use concurrency only for independent operations.
- DO clean up timers, listeners, subscriptions, and observers.
- Unless unavoidable, AVOID changing global runtime state.
- DO declare route response schemas.
- DO return raw domain objects or primitive values without reconstructing response models solely for validation.
- DO run formatting, linting, type checking, and relevant existing tests.
- After verification, DO review the implementation for further simplification.
- DO use only `lucide-react` icons.
- For brand logos, you CAN use custom SVG components with official brand colors.
- DO keep each page simple and standalone.

## shadcn/ui Guidelines

<!-- SHADCN:START -->
Use shadcn/ui components with Tailwind CSS and the project's existing theme.
CLI: run commands from `web/` using `npx shadcn@latest <cmd>`.

SETUP — reuse the existing configuration:
- `web/components.json` configures the component style, aliases, and stylesheet.
- Components live in `web/src/components/ui/`; import them through `@/components/ui/<name>`.
- `web/src/styles.css` imports Tailwind CSS and defines semantic theme tokens.
- `web/src/main.tsx` imports the stylesheet once. No theme provider is required.

WORKFLOW:
1. Check existing components and official documentation at https://ui.shadcn.com/docs before adding a component.
2. `npx shadcn@latest add <component>` — add only the components needed. Don't overwrite customized components without reviewing the changes.
3. Compose pages from existing components and semantic HTML. Preserve the structure of existing pages unless a layout change is requested.

RULES:
- Use component variants and sizes first, then token-backed Tailwind utilities for layout and styling.
- Use semantic HTML where appropriate; don't create wrappers solely to replace standard elements.
- Dense data belongs in Table or list rows, not Card-wrapped lists. Use Card only for meaningful content groups.
- Use semantic colors such as `bg-background`, `text-muted-foreground`, and `border-border`. Define shared colors through the theme variables in `web/src/styles.css`, not per-component overrides.
- Use shadcn's ChartContainer, ChartTooltipContent, and ChartLegendContent with Recharts. Keep chart colors in the theme's chart tokens.
- Preserve missing chart values as gaps, never zero. Keep an accessible data table available.
- Preserve keyboard interaction, focus indicators, accessible names, and disabled states when composing components.
- Prefer existing variants and utilities over inline styles, arbitrary values, or new CSS rules. Dynamic chart and map styling may use inline values where necessary.
- SELF-CHECK: re-read changed files for unnecessary wrappers, duplicated styling, hardcoded colors, and inaccessible interactions. Run formatting, linting, type checking, a production build, and relevant existing tests without browser automation.

`npx shadcn@latest --help` lists available CLI commands.
<!-- SHADCN:END -->

## Commit Message Structure

DO use this structure for commit messages:

<commit-message>
	<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert</type>
	<scope>api|sdk|web (optional)</scope>
	<description>A short, imperative summary of the change</description>
</commit-message>

## Merge Request Structure

DO use this structure for merge requests:

<merge-request>
	<title>Use the commit message structure</title>
	<summary>What changed and why</summary>
	<validation>Checks run and results, or why not run</validation>
	<labels>Change-type labels from .github/release.yml and applicable area labels: api|sdk|web</labels>
</merge-request>
