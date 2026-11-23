# Reading every document (OCR, tables, mixed pages)

**What is promised, and what is not.** ALERTE reads every file it finds, never skips one silently, and reads scans with the
strongest practical OCR. No OCR on earth can promise every character correct on every scan: print quality, fonts, stamps,
handwriting and phone photos all limit it. So the system does three things instead of pretending:

1. It uses the exact characters from the file whenever the file has them (digital PDF, Word, Excel, text): no OCR error is possible.
2. For scans it reads each page several ways, measures its own confidence and agreement, and **flags every uncertain page**.
3. It gives you a short proofreading loop. A page that a human has corrected is used as is and marked `human-corrected`. This is
   how a document you care about reaches a verified 100%.

## Which files and folders are read

Everything. The knowledge base is built from:

| Source | How |
| --- | --- |
| Rows of `data/manifest.csv` | by the `file` column (e.g. `CM/official/CM-02_....pdf`) |
| **Every other file** under `data/docs/` | any depth, any name; registered automatically as `AUTO-<name>` |
| Folders in `ALERTE_EXTRA_DOC_DIRS` | same, separate folders with `;` |
| Files uploaded in the interface (Knowledge base > Add documents) | saved to `data/docs/inbox/` |
| The ITU reference corpus, if found | as before |

Identical files (same SHA-256) are indexed once and reported. A file that cannot be read is **listed with its reason** in the
ingest output, in `index/extraction_report.json` and in `index/review_queue.md`; `python -m alerte ingest --strict` exits with an error.

Formats: PDF (digital, scanned, mixed), PNG, JPEG, TIFF (multi-page), BMP, WebP, GIF, Word (.docx), PowerPoint (.pptx), Excel
(.xlsx, .xls), OpenDocument (.odt, .ods, .odp), RTF, EPUB, HTML, CSV/TSV, Markdown, text, JSON, XML, YAML. Legacy `.doc` and `.ppt`
are converted if LibreOffice is installed, otherwise reported with instructions. A file with a wrong or missing extension is
recognised from its first bytes.

## Techniques, in the order a page goes through them

| Situation | What is done |
| --- | --- |
| Digital PDF page | Exact text layer. Tables rebuilt as Markdown, each cell read from its own rectangle (spaces and accents intact). Words broken at line ends are rejoined. |
| Text layer is broken (wrong font encoding, replacement characters, vowel-less gibberish) | Detected by `quality.text_layer_trust`; the layer is ignored and the page is OCR'd. |
| Scanned page | Rendered at 300 dpi, tilt corrected (projection profile), shadows and uneven light removed, denoised. Read by Tesseract 5 with the best-accuracy models for French, English and Arabic. Up to three passes with different clean-ups and segmentation modes; the best is kept and the **agreement between passes** is recorded. Sideways or upside-down pages are tried in the other orientations. |
| Scanned page that also has a text layer (earlier OCR) | Both are read and compared. Agreement of 0.90 or more keeps the exact layer; below that the better reading is chosen and the page is flagged. |
| Ruled table in a scan | Table found from its lines, then **each cell is read separately** (rule remnants erased, single-line mode for short cells) and written as a Markdown table. |
| Table without ruling lines | Read as lines; wide gaps between words are written as ` | `. This is an approximation: check such tables. |
| Digital page with pictures that contain text (charts, stamps, pasted screenshots) | The text layer is kept and each large picture is OCR'd; its text is added as `[Text in image] ...`. |
| Word, PowerPoint | Text and tables in document order, headings, headers/footers, slide notes; embedded pictures OCR'd. |
| Arabic pages | Always cross-checked with OCR (text-layer order and shaping are unreliable); right-to-left word order is restored. |
| Two-column pages | Reading order of the file is kept. |

Each page records how it was read (`text-layer`, `ocr`, `text-layer (verified by OCR)`...), the OCR confidence and the agreement,
and each passage in the index carries a short provenance label (visible in the interface).

## When a page is flagged

A page is flagged when OCR confidence is below `ALERTE_OCR_CONF_OK` (default 88), the passes agree less than
`ALERTE_OCR_AGREE_OK` (default 0.97), the text layer and the OCR disagree, no text was found, or no OCR engine is installed.
Flagged documents appear in `index/review_queue.md`, in the console, and in the interface (Knowledge base > Extraction quality).

## The proofreading loop

```bash
python -m alerte review CM-02                       # or part of the file name
# opens review/CM-02/: page-003.png ... (only the flagged pages) and draft.md (the whole document, pages marked ok / CHECK)
# correct draft.md, then save it next to the source as:  <file name>.corrected.md
python -m alerte ingest
```

A `<file name>.corrected.md` (or `.corrected.txt`) beside a source file always wins over the machine reading; `<!-- comments -->`
in it are ignored. Nothing is lost: the original file stays where it is.

## Commands

| Command | Purpose |
| --- | --- |
| `python -m alerte ocr-setup` | check Tesseract; download the French, English and Arabic models into `ocr/tessdata` |
| `python -m alerte ingest` | read everything and rebuild the index (`--strict`, `--thorough`, `--no-cache`) |
| `python -m alerte extract FILE` | read one file and print the per-page quality report and text |
| `python -m alerte review ID` | proofreading pack for a flagged document |
| `python -m alerte ocr-eval` | measure accuracy on generated test documents |
| `python -m alerte doctor` | shows whether OCR is ready |

Results are cached by file hash in `index/extract_cache`, so a second `ingest` is fast.

## Measured accuracy (generated test documents, Tesseract 5.3.4, `python -m alerte ocr-eval`)

| Case | Character accuracy |
| --- | --- |
| Digital PDF, French; two columns; ruled table | 100% (exact text layer) |
| Scanned PDF, French, tilted, noisy, uneven light | 100% |
| Scanned PDF, English | 100% |
| Scanned PDF with ruled table | 100% |
| Sideways low-resolution image | 100% |
| Text mixed with a picture of text | 100% |
| Scan carrying a corrupt hidden text layer | 100% |
| Word with heading, table and picture | 100% |
| Scanned PDF, Arabic | 100% |

**Read this honestly.** These are generated pages in clean fonts with realistic tilt, noise and uneven light. They prove the
pipeline works end to end and protect against regressions (`tests/test_extraction.py` fails if accuracy drops). They do not prove
100% on your files. Real laws are often photocopies with stamps, faint print, fax artefacts, small fonts and handwriting in the
margins, where OCR makes errors. Those pages are exactly what the flags and the proofreading loop are for.

## Speed, timeouts and what the console shows

`ingest` prints one line per OCR'd page (`page 5/60: ocr 93% in 7s`). Design choices that keep long documents practical:

- **One thread per Tesseract process** (`OMP_THREAD_LIMIT=1`), because several pages are read in parallel. Letting each Tesseract use all
  cores while several run at once oversubscribes the machine and pages hit the time limit.
- **Plain greyscale first.** The first pass keeps light text on dark or busy backgrounds (brochures, slides), which shadow-removal would
  erase. Clean-up and binarised passes are second opinions on uncertain pages. Pages that are not text (graphics, photos) stop after two passes.
- **A page with a good exact text layer is cross-checked by OCR only if pictures cover 85% or more of it** (a scan with an earlier OCR layer),
  or if it is Arabic. A brochure with background pictures keeps its exact text without OCR.
- **Sideways pages** are detected from the direction of the text lines, then confirmed with quick OCR on small copies.
- **A timed-out call is retried** smaller and in sparse-text mode (`ALERTE_OCR_TIMEOUT`, `ALERTE_OCR_MAX_SIDE`). Only if that also fails is the
  page flagged `OCR-FAILED`; for a page with an exact text layer the layer is kept.

If you still see `Tesseract process timeout`, lower `ALERTE_OCR_WORKERS` (try 1 or 2), raise `ALERTE_OCR_TIMEOUT`, delete `index/extract_cache`, and run
`python -m alerte extract <file> --no-text` on one failing page range to see the per-page report.

## Known limits

- Handwriting is not read reliably. Stamps or signatures over text can corrupt the words beneath them.
- Tables with merged cells are read cell by cell but not merged back; borderless tables are approximate.
- Very small print (under about 8 pt at 300 dpi) and photos taken at an angle lose accuracy.
- Mathematical formulas and diagrams are not transcribed.
- Tested here on Linux with Tesseract 5.3.4. Windows and macOS use the same code paths (the setup scripts install Tesseract with
  winget or Homebrew), but I have not run them there.
- Without the Tesseract program, scanned pages are reported as `NEEDS-OCR-ENGINE` (never skipped silently). A pure-pip fallback
  (`pip install rapidocr-onnxruntime`) is used automatically but its default models are weak on French accents and Arabic.
