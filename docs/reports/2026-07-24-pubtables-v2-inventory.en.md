# PubTables-v2 Repository Inventory

- Repository: `kensho/PubTables-v2`
- Resolved revision: `aa575e798cb00a296925e2086addb3e3fd9a1903`
- Files: 48
- Bytes: 218471925494
- Extensions: `{".gz": 42, ".md": 1, ".sh": 4, "<none>": 1}`

The JSON manifest is stored outside Git under `artifacts/manifests/`.

## Audit Scope and Provenance

This report is pinned to repository commit
`aa575e798cb00a296925e2086addb3e3fd9a1903` and was reviewed on 2026-07-24.
Evidence came from:

- the Hugging Face dataset card at the resolved revision;
- the 48-file metadata manifest generated with `files_metadata=True`;
- the four repository decompression scripts;
- an HTTP Range audit of at most 1 MiB from each Full Documents public test archive,
  sufficient to inspect the first tar member and a small serialization sample.

No complete dataset archive, PDF corpus, or page-image collection was downloaded.

## License

The dataset card declares **CDLA-Permissive-2.0**. This is the dataset license and must
not be confused with the PubTables-v2 paper license, which is **CC BY 4.0**. Source
article content may also remain subject to the PMC Open Access terms associated with the
original articles; downstream redistribution must preserve that distinction.

## Collections, Splits, and Paths

The repository contains three collections and three public split identifiers:

| Collection | Public split identifiers | Extracted subdirectories |
|---|---|---|
| `Cropped Tables` | `train`, `val`, `test` | `tables`, `images`, `words`, `xml_annotations` |
| `Single Pages` | `train`, `val`, `test` | `images`, `tables`, `words`, `xml_annotations` |
| `Full Documents` | `train`, `val`, `test` | `cross_page_table_pairs`, `images`, `single_page_table_continuations`, `tables`, `words`, `xml_annotations` |

The dataset card reports 135,578 cropped tables, 467,541 single pages with 548,414
tables, and 9,172 full documents containing 9,492 multi-page tables. Some samples remain
in an unreleased private test set. The internal project split name `validation` must map to
the repository identifier `val`; this mapping should be explicit in later manifests.

There is one repository inconsistency to handle defensively: `uncompress.sh` extracts the
Cropped Tables archive named `*_tables.tar.gz` into `tables`, while
`uncompress_cropped_tables.sh` refers to a `grits` directory/archive that is not present in
the resolved 48-file manifest. Later tooling should use manifest names as the source of
truth rather than assuming the collection-specific script is current.

## Serialization Formats

The formats below were verified from archive members at the pinned revision:

| Artifact | Member naming example | Serialization and observed fields |
|---|---|---|
| Page image | `Full Documents/test/images/PMC12259915_page_4.jpg` | JPEG/JFIF rendered page image |
| PDF words | `Full Documents/test/words/PMC11470387_page_0_words.json` | JSON list with `bbox`, `text`, `block_num`, `line_num`, `span_num`, and PDF extraction flags |
| Logical tables | `Full Documents/test/tables/PMC11518671_tables.json` | JSON list with `cells`, `parts`, `grid_top`, `grid_con`, `html`, and `original_markup`; each part includes `page_num`, `page_object_num`, `pdf_bbox`, and rendered-image `bbox` |
| Cross-page pairs | `Full Documents/test/cross_page_table_pairs/PMC11276610.json` | JSON list of `page_A`, `page_B`, and binary `label` records |
| Same-page table parts | `Full Documents/test/single_page_table_continuations/PMC10474523_page_3.json` | JSON object containing table-part `bboxes` and an `adjacency_matrix` |
| XML annotations | `Full Documents/test/xml_annotations/PMC11243142_page_4.xml` | Pascal-VOC-style XML with page filename, image dimensions, database name, and page objects when present |

The table JSON confirms document-level logical structure and page-part boxes, but does not
provide row/column bounding boxes within each multipart table fragment. That limitation is
consistent with the research paper and motivates the planned alignment-label derivation.

## Document Metadata Availability

- **PMCID:** available as the stable prefix of document, page, table, and annotation filenames.
- **DOI:** not exposed in the dataset card, manifest paths, or sampled table JSON fields.
- **Journal/ISSN:** not exposed in the dataset card, manifest paths, or sampled table JSON fields.

Therefore the proposed journal/ISSN-disjoint split cannot be built from PubTables-v2 files
alone. It requires a separately versioned PMC metadata lookup keyed by PMCID. If that lookup
is unavailable or incomplete, template clustering must be the primary disjoint protocol rather
than silently treating PMCID as a journal identifier.

## Compressed Download Budget

All values are exact compressed byte sums from the resolved manifest; approximate binary units
are provided only for planning.

| Download scope | Bytes | Approximate size | Purpose |
|---|---:|---:|---|
| Full Documents test labels only (`tables`, XML, pair and same-page continuation labels) | 9,906,334 | 9.45 MiB | Small metadata/sample audit without images or words |
| All structural metadata archives across collections (same label classes) | 3,812,578,532 | 3.55 GiB | Structure-only preparation |
| All non-image repository files, including PDF words | 16,217,869,144 | 15.10 GiB | Text/structure preparation without rendered pages |
| Complete Full Documents public test split | 3,413,101,914 | 3.18 GiB | First end-to-end sample split |
| All Full Documents splits | 36,333,161,334 | 33.84 GiB | Main document-level experiments |
| Entire repository | 218,471,925,494 | 203.44 GiB | All three collections |

The next task should begin with the 9.45 MiB Full Documents test labels, followed by a
document-targeted range or selective sample download. A 203.44 GiB full download is not
appropriate until schemas, hashes, storage, and the sample audit have passed.

## Audit Conclusions

1. PubTables-v2 is publicly usable under CDLA-Permissive-2.0 and has the required public
   `train`/`val`/`test` archives for all three collections.
2. Full Documents directly provides logical tables, page-part provenance, hard pair labels,
   page images, PDF words, and page annotations, but not fine-grained per-fragment row/column
   boxes.
3. PMCID is available; DOI and journal/ISSN require external enrichment.
4. Manifest-pinned extraction is required because one included helper script is inconsistent
   with the actual Cropped Tables archive name.
5. Metadata-first work can proceed without a bulk download; the full repository should remain
   outside the local CPU workspace until the sample pipeline is verified.
