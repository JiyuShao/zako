# Issue tracker: Local Markdown

Issues and specs live as Markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`.
- Specs: `.scratch/<feature-slug>/spec.md`.
- Implementation tickets: `.scratch/<feature-slug>/issues/<NN>-<slug>.md`,
  numbered from `01`, one file per ticket.
- Record triage state in a `Status:` line near the top of each issue.
  Use the vocabulary in `triage-labels.md`.
- Append comments and conversation history under `## Comments`.

## Publishing and fetching

When a skill says "publish to the issue tracker", create the appropriate
spec or issue file at the paths above, creating directories as needed.

When a skill says "fetch the relevant ticket", read the referenced file.
Resolve a ticket number within its feature directory.

## Wayfinding operations

Used by `/wayfinder`.

- Map: `.scratch/<effort>/map.md`, containing Notes, Decisions-so-far,
  and Fog.
- Child ticket: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`.
  Record its type in `Type:` (`research`, `prototype`, `grilling`, or `task`).
- Blocking: record `Blocked by: NN, NN` near the top. A ticket is unblocked
  when every listed ticket has `Status: resolved`.
- Frontier: scan for open, unblocked, unclaimed tickets; first by number wins.
- Claim: set `Status: claimed` and save before beginning work.
- Resolve: append the answer under `## Answer`, set `Status: resolved`,
  and append a brief finding with a link to the map's Decisions-so-far.

The `claimed` and `resolved` statuses apply to the wayfinding lifecycle.
