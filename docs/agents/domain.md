# Domain Docs

This repo uses a single-context domain documentation layout.

## Before exploring

- Read `GLOSSARY.md` at the repo root if it exists.
- Read decisions in root `docs/adr/` that touch the area being explored.

If these files do not exist, proceed silently. Create them lazily through
`/domain-modeling` when terms or decisions are resolved.

## File structure

- `GLOSSARY.md`: shared domain vocabulary.
- `docs/adr/NNNN-<decision-slug>.md`: architecture decision records.

## Use the glossary's vocabulary

Use defined domain terms in issue titles, proposals, hypotheses, and test
names. Follow any explicitly preferred terms over their synonyms.

If a needed concept is missing, reconsider whether it belongs to the
domain; record real vocabulary gaps for `/domain-modeling`.

## Flag ADR conflicts

When a proposal contradicts an existing ADR, identify that ADR and explain
why the decision should be reconsidered.
