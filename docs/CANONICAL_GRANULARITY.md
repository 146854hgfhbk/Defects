# Canonical bug-level granularity

This report applies a Defects4J-style unit policy to the 850 active Defects4X bugs.
The output is one row per bug in `metadata/canonical-bugs-with-granularity.csv`.
The source-level variant audit remains in `metadata/defects4j-granularity-classified.csv`.

## Patch selection

`metadata/active-bugs.csv` is the one-row-per-bug selection authority. For each bug,
the selector chooses the first available production patch in this order:

1. `canonical_patch`, when the manifest provides it;
2. `minimized_patch`, when it is available and has a source-audited row;
3. `upstream_patch` as the fallback.

The selected patch is never formed by taking the union of several variants. The other
variants remain in `variant_paths`, `variant_labels`, and `variant_disagreement` for
auditing and sensitivity analysis. A disagreement means that the variants should not be
silently treated as one patch.

This follows the useful Defects4J convention: a bug is identified by one pinned buggy/fixed
revision pair and one reviewed production source patch. Tests, documentation, build files,
and compatibility patches are outside this granularity calculation.

## Labels

The labels preserve the hierarchy requested for single-function changes:

- `SL`: exactly one changed production line; implies `SH` and `SF`.
- `SH`: multiple changed production lines in one hunk and one function; implies `SF`.
- `SF`: one function with multiple hunks, or an included `SL`/`SH` patch.
- `MF`: multiple changed functions; disjoint region class from `SF` and `OR`.
- `OR`: a confirmed changed production line outside function bodies; disjoint primary region class.
- `mapping_method=manual_context`: a human-reviewed function boundary override for a selected canonical patch.
- Variant-only mapping gaps use `mapping_method=fallback_outside` with `mapping_confidence=low`; they never create a missing primary bug label.

The CSV stores `region_class` as the disjoint primary class (`SF`, `MF`, or `OR`) and
stores `sl`, `sh`, and `sf` as overlapping Boolean properties. A patch containing both
function-internal and function-external changes keeps `region_class=OR` and records
`mixed_function_outside=true`.

## Current canonical result

The selected patch distribution is:

| Region class | Bugs |
|---|---:|
| `SF` | 400 |
| `MF` | 159 |
| `OR` | 291 |
| **Total** | **850** |

The nested membership counts are `SL=28`, `SH=333`, and `SF=400`; these overlap by
design and must not be added. The selected patch kinds are `canonical=108` and
`minimized=742`; no bug required the upstream fallback. The report separately records exact-label variation and region-class variation across retained variants;
`variant_region_disagreement` is the condition that changes the disjoint SF/MF/OR region interpretation.
In this output, 74 bugs have exact-label variation and 49 have region-class variation. Six selected rows use manual context review.

These are bug-level counts. They must not be combined with the 2,191 patch-variant rows
in `metadata/defects4j-granularity-summary.json`.
