# VoxStella remote rules

Edit the five JSON files in `source/` and commit them to `main`. The
`Publish rule corpus` GitHub Action validates and combines the complete rule
set, publishes an immutable package, and advances `manifest.json`.

The iOS app accepts only the complete set of rule IDs shipped in the reviewed
binary. To turn off a rule, keep its ID and set its condition to `false`.

Do not edit `manifest.json` or `packages/` manually.
