# Deep Document Understanding — Design Philosophy & Algorithms

## Why Deep Document Understanding?

RAGFlow's **deepdoc** module tackles the core problem: *how to extract structured information from visually complex documents without losing semantic relationships*.

### The Problem with Simple Text Extraction

Naive PDF text extraction (using libraries like `pdfplumber`) fails on documents with:

- **Scanned images**: OCR required, layout context lost
- **Complex layouts**: Multi-column, nested tables, sidebars, footers
- **Figures and captions**: Spatial relationships need preservation
- **Tables with merged cells**: Structure requires recognition, not just text
- **Text + image blending**: Both must be understood together

Traditional pipeline: *extract all text → try to chunk → lose layout*.

**deepdoc** inverts this: *recognize layout → OCR where needed → chunk by semantic role*.

---

## Architecture Overview

### Design Decisions

#### 1. **Multi-Engine Support (Not Single Pipeline)**

Instead of one monolithic parser, deepdoc offers pluggable engines:

- **Standard**: RAGFlowPdfParser (pdf_parser.py) — layout recognition + bbox-based chunking
- **Docling** (docling_parser.py) — Meta's document understanding model
- **MinerU** (mineru_parser.py) — open-source vision parser
- **PaddleOCR** (paddleocr_parser.py) — Chinese document focus
- **TCADp** (tcadp_parser.py) — table-aware parsing
- **OpenDataLoader** (opendataloader_parser.py) — structured extraction

**Why multi-engine?** Different documents demand different strategies. A scanned resume needs OCR + text layout. A born-digital business report needs table structure. Chinese documents need language-specific OCR.

#### 2. **PaddlePaddle + ONNX, Not Just TensorFlow**

**LayoutRecognizer** uses ONNX-optimized inference for layout detection:

- **PaddlePaddle DLA model** (trained on document datasets)
- **ONNX Runtime** for CPU/GPU inference
- **Fallback**: Remote DLA server via TENSORRT_DLA_SVR environment variable

**Why?** ONNX is framework-agnostic, deployable anywhere. PaddlePaddle was trained on massive document datasets (stronger than general vision models).

#### 3. **BBox-Based Chunking (Not Token-Based)**

Instead of "split text every 512 tokens," deepdoc chunks by **layout bounding boxes**:

```
Page → Layout recognition (12 label classes) → 
       BBox grouping by semantic role (Text, Table, Figure) → 
       OCR fallback for image regions → 
       Spatial-aware chunking
```

**Chunks are**:
- Contiguous spatial regions (not token boundaries)
- Labeled by semantic type (Title, Text, Table, Figure)
- Preservable as Markdown with structure intact

#### 4. **Fallback OCR for Degraded Images**

If `pdfplumber` can't extract text:
1. Render page as image
2. Run layout recognition
3. Run OCR on detected text regions
4. Merge OCR results respecting layout

This preserves spatial relationships even for 100% scanned PDFs.

---

## Core Components

### Parser Layer (parser/)

**File-format handlers** — one class per format:

- **pdf_parser.py** (85KB) — Master PDF parser
  - Text extraction via pdfplumber
  - Layout analysis via LayoutRecognizer + TableStructureRecognizer
  - Figure extraction via VisionFigureParser
  - Page assembly with bbox-based chunking
  
- **docx_parser.py** (6KB) — DOCX via python-docx
  - Preserves heading hierarchy
  - Table extraction via xml parsing
  
- **excel_parser.py** (11KB) — XLSX parsing
  - Sheet iteration
  - Cell type detection (merged cells, formulas)
  
- **html_parser.py** (8KB) — HTML via BeautifulSoup
  - Recursive element traversal
  - Block-level grouping (divs, sections)
  
- **markdown_parser.py** (12KB) — Markdown AST parsing
  - Heading-based sectioning
  - Code block preservation
  
- **figure_parser.py** (12KB) — Image/figure extraction
  - Figure detection in PDFs/DOCX
  - Caption association
  - Vector/raster differentiation

- **Alternative engines**: mineru_parser.py (31KB), docling_parser.py (23KB), paddleocr_parser.py (23KB)

### Vision Layer (vision/)

**Neural recognizers** — layout and table understanding:

- **recognizer.py** (16KB) — Base class for ONNX inference
  - Model loading (local or HuggingFace)
  - Batch inference
  - NMS post-processing

- **layout_recognizer.py** (18KB) — Document layout detection
  - 12 label classes: Text, Title, Figure, Table, Figure caption, Table caption, Header, Footer, Reference, Equation, Background
  - Input: image (any resolution, auto-scaled)
  - Output: bboxes with class labels
  - Optional remote DLA server support (TensorRT inference)

- **table_structure_recognizer.py** (23KB) — Table cell detection
  - Detects cell boundaries within table regions
  - Outputs grid structure (row/col spans)
  - Post-processes via heuristic-based merging

- **ocr.py** (28KB) — OCR pipeline
  - Detection: CRAFT-based text region detection
  - Recognition: PaddleOCR character-level recognition
  - Supports 80+ languages
  - Parallel processing via semaphores

- **postprocess.py** (13KB) — Result normalization
  - Bbox NMS (non-maximum suppression)
  - Label smoothing
  - Confidence filtering

- **operators.py** (24KB) — Vision utilities
  - Image resizing, rotation correction
  - Perspective transformation
  - Feature extraction for table analysis

- **seeit.py** (2KB) — Visualization helper for debugging

---

## Algorithm Deep-Dives

### 1. Layout Recognizer (DLA Model)

**Input**: Image (PDF page rendered at 3x zoom, or natural image)

**Model**: PaddlePaddle-trained Detectron2-style DLA (Deep Layer Aggregation)
- ResNet50 backbone
- FPN (Feature Pyramid Network) for multi-scale features
- Region proposal network (RPN) → RoI detection
- Trained on 100k+ labeled document images

**Output**: List of `{bbox, class_id, confidence}`

**Inference**: ONNX Runtime
- Batch processing (default 16 images)
- Auto-scaling to 640×640 input
- Threshold-based filtering (default thr=0.2)

**Post-Processing**:
```python
# NMS: keep high-confidence, suppress overlapping boxes
for each class_label:
    sort by confidence (desc)
    for each box:
        if IoU(box, kept_boxes) > 0.5: skip
        else: keep
```

**Output**: Bounding boxes grouped by class, ready for text assignment.

### 2. Table Structure Recognizer (TSR)

**Input**: Image region marked as "Table" by layout recognizer

**Goal**: Decompose table image into cells with row/col indices

**Method**:
1. **Line detection** (Hough transform) → find grid
2. **Cell merging** (post-hoc heuristic) → handle merged cells
3. **Grid inference** → output row/col span for each cell

**Output**: `{cell_bbox, row_idx, col_idx, row_span, col_span}`

**Use**: Reconstruct table as Markdown grid or HTML, not flat text.

### 3. OCR Pipeline

**Entry point**: `ocr.py:OCR.__call__(image_list, lang='en')`

**Two-stage process**:

**Stage 1: Text Detection (CRAFT)**
- Detects word-level regions
- Outputs: list of `{bbox, confidence}`

**Stage 2: Text Recognition (PaddleOCR)**
- Per-region character recognition
- Outputs: `{text, confidence, bbox}`

**Parallelism**:
```python
if settings.PARALLEL_DEVICES > 1:
    use [asyncio.Semaphore(1) for i in range(PARALLEL_DEVICES)]
```

**Result**: OCR aligned to detected regions, preserving spatial order (top-left to bottom-right).

### 4. PDF Parsing Pipeline (pdf_parser.py)

**Input**: PDF file path

**Flow**:
```
1. pdfplumber.open(fnm) → PDF object
2. for each page:
   a. Try pdfplumber text extraction
   b. If text found: use it (fast path)
   c. If no text: render page as image (slow path)
   
3. Render page at 3x zoom (zoomin=3)
   → Input to layout_recognizer
   
4. Layout recognizer → bboxes (12 classes)
   
5. For "Text" bboxes: assign extracted text to bbox regions
   For "Table" bboxes: 
      - Crop image region
      - Run table_structure_recognizer
      - Output cell grid
   For "Figure" bboxes:
      - Crop and save image
      - Extract caption from adjacent text
   
6. OCR fallback for low-confidence text regions
   
7. Assemble page as list of:
   - Text blocks (heading, body)
   - Table blocks (markdown or HTML)
   - Figure blocks (with captions)
   
8. Chunk by blocks (or by token count within blocks)
```

**Output**: List of `{text, type, bbox, page, table_html?, image_path?}`

### 5. BBox-Based Chunking

**Why not token-based?** Tokens don't respect document structure.

**Algorithm**:
```
blocks = parsed page blocks (already grouped by layout)

for each block:
    if type == "table":
        keep whole table as one chunk (or split by rows)
    elif type == "figure":
        keep caption + figure together
    elif type == "text":
        if token_count(block) < chunk_size:
            keep as-is
        else:
            split by heading hierarchy or sentence boundaries
            (preserving markdown structure)
```

**Result**: Chunks respect semantic boundaries, enabling better RAG retrieval.

---

## Error Philosophy

### Fallback Strategy

**Principle**: *Partial extraction is better than failure.*

1. **Text extraction fails** → Render + OCR (slower but works)
2. **OCR confidence low** → Keep text anyway (with confidence flag)
3. **Table detection fails** → Output raw text (not structured)
4. **Figure caption lost** → Keep figure without caption
5. **Layout recognition errors** → Merge overlapping regions heuristically

### Robustness Mechanisms

- **Confidence thresholds**: Configurable per component (layout thr=0.2, OCR thr=0.5)
- **Parallel device limiting**: Prevent OOM on large batches
- **Model downloading**: Auto-fetch from HuggingFace if local model missing
- **Remote DLA fallback**: If local ONNX inference fails, use remote TensorRT server

---

## Design Rationale

### Why ONNX over TensorFlow/PyTorch?

- Framework-agnostic (works with TensorFlow-trained, PyTorch-trained, PaddlePaddle models)
- CPU inference fast enough for typical documents
- Lightweight runtime (no deep learning framework needed)
- Easy deployment (single .onnx file)

### Why Multiple Parsers?

- **Trade-off space**: Accuracy vs speed vs language support vs table handling
- Users choose based on their document corpus
- Fallback if one fails

### Why BBox Chunking?

- **Preserves structure** (tables stay tables, figures stay with captions)
- **Enables spatial search** (locate text by page coordinates)
- **Respects semantic boundaries** (don't split headings from content)

### Why Layout Recognition First?

- **Semantic understanding before text assignment**
- Detect regions that need OCR (vs. already-digital text)
- Group text blocks (e.g., multi-column layout)
- Identify non-text elements (figures, tables)

---

## Key Files by Size & Complexity

| File | Size | Purpose | Complexity |
|------|------|---------|-----------|
| pdf_parser.py | 85KB | Master PDF handler | High (main pipeline) |
| mineru_parser.py | 31KB | Alternative vision parser | High |
| docling_parser.py | 23KB | Meta's parser integration | High |
| ocr.py | 28KB | OCR pipeline | High |
| table_structure_recognizer.py | 23KB | Table decomposition | Medium |
| paddleocr_parser.py | 23KB | Chinese-focused parser | High |
| operators.py | 24KB | Vision utilities | Medium |
| layout_recognizer.py | 18KB | Layout detection | Medium |
| recognizer.py | 16KB | ONNX base class | Low |
| postprocess.py | 13KB | NMS + filtering | Low |
| markdown_parser.py | 12KB | Markdown AST | Low |
| excel_parser.py | 11KB | XLSX handling | Low |
| figure_parser.py | 12KB | Figure extraction | Medium |
| html_parser.py | 8KB | HTML traversal | Low |
| docx_parser.py | 6KB | DOCX extraction | Low |

---

## Testing & Validation

### Unit Test Entry Points

- **OCR tests**: Verify CRAFT detection + PaddleOCR recognition alignment
- **Layout tests**: Check 12-class detection on synthetic/real documents
- **Parser tests**: Round-trip (PDF → parsed blocks → markdown) format preservation
- **Table tests**: Grid reconstruction from table images
- **Integration tests**: End-to-end PDF → chunks pipeline

### Common Gotchas

1. **DPI mismatch**: PDFs render at different DPIs; use zoomin factor to normalize
2. **OCR model loading**: First run fetches from HuggingFace (can be slow)
3. **Parallel limits**: Semaphore count must match GPU availability
4. **Confidence thresholds**: Too high → missed content; too low → noise

---

## Future Directions

1. **Video parsing** → Extract text from frames (deepdoc roadmap)
2. **Handwriting recognition** → Extend OCR to cursive documents
3. **Layout-aware retrieval** → Use bboxes for spatial search (page coordinates)
4. **Cross-modal fusion** → Better figure-text associations via CLIP embeddings
5. **Streaming parsing** → Process multi-gigabyte PDFs without loading into memory
