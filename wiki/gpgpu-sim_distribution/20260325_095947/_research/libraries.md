# GPGPU-Sim Supporting Libraries — Research Report

> **Scope**: `libcuda/` (CUDA runtime), `libopencl/` (OpenCL runtime),
> `cuobjdump_to_ptxplus/` (binary translation tool), `aerialvision/` (visualisation).

---

## 1. Project Overview (from README.md)

GPGPU-Sim is a **cycle-level simulator** modelling contemporary GPUs running
CUDA or OpenCL workloads. Key facts:

- Tested with CUDA 4.2 through 11.
- Supports **Accel-Sim** trace-driven simulation via NVBit SASS traces (v4.0+).
- Ships with **AerialVision** (performance visualisation) and **AccelWattch** (power model).
- Interconnect simulated by BookSim.
- Build: `source setup_environment && make`; config in `gpgpusim.config`.
- Supported GPU configs include QuadroFX5800, GTX480, Volta, and more.

---

## 2. libcuda — CUDA Runtime Library

**Location**: `/mnt/disk2/gpgpu-sim_distribution/libcuda/`

### 2.1 Purpose

Implements the **NVIDIA CUDA Runtime API** as a shared library (`libcudart.so`)
that intercepts every CUDA call from the application. Instead of forwarding to
hardware, it translates each call into GPGPU-Sim simulator operations: memory
allocation, data transfer, kernel launch, synchronisation.

When an application is linked against GPGPU-Sim's `libcudart.so` (via
`LD_PRELOAD` or build-time linking), all CUDA calls are redirected here.

### 2.2 Key Files

| File | Role |
|------|------|
| `cuda_runtime_api.cc` (7,260 lines) | Implements 80+ `cuda*()` API functions |
| `cuda_api_object.h` | Declares `cuda_runtime_api` class, `CUctx_st`, `_cuda_device_id`, `kernel_config` |
| `gpgpu_context.h` | Central `gpgpu_context` class tying all sub-systems together |
| `Makefile` | Builds `libcudart.so` |

### 2.3 Key Classes and Structures (10+)

| # | Class / Struct | Description |
|---|----------------|-------------|
| 1 | **`gpgpu_context`** | Master singleton context. Contains pointers to `cuda_runtime_api *api`, `cuda_sim *func_sim`, `GPGPUsim_ctx *the_gpgpusim`, `ptx_cta_info *ptx_cta`, `ptxinfo_data *ptx_parser`, `device_runtime_t *device_runtime`. Owns `synchronize()`, `exit_simulation()`, `start_sim_thread()`, `gpgpu_ptx_sim_init_perf()`, `cuobjdumpParseBinary()`. |
| 2 | **`cuda_runtime_api`** | State for the CUDA runtime layer. Members: `cuobjdumpSectionList`, `fatbinmap` (handle→filename), `name_symtab` (name→symbol_table), `pinned_memory`, `g_mallocPtr_Size`. Key methods: `cuobjdumpInit()`, `extract_code_using_cuobjdump()`, `load_static_globals()`, `load_constants()`, `gpgpu_cuda_ptx_sim_init_grid()`. |
| 3 | **`CUctx_st`** | CUDA context. Links host functions to device implementations via `m_kernel_lookup: map<const void*, function_info*>`. Owns `m_code: map<unsigned, symbol_table*>` for loaded cubins. |
| 4 | **`_cuda_device_id`** | Device abstraction wrapping `gpgpu_sim *m_gpgpu`. Static `num_devices()`, `get_device()` methods. |
| 5 | **`kernel_config`** | Stores pending `cudaConfigureCall` state: `dim3 m_GridDim`, `dim3 m_BlockDim`, `gpgpu_ptx_sim_arg_list_t m_args`, `CUstream_st *m_stream`. |
| 6 | **`CUevent_st`** | Event object (defined in `stream_manager.h`, used extensively here). |
| 7 | **`CUstream_st`** | Stream object (defined in `stream_manager.h`). |
| 8 | **`gpgpu_ptx_sim_arg`** | Kernel argument descriptor: `m_start`, `m_nbytes`, `m_offset`. |
| 9 | **`function_info`** | Decoded PTX kernel (defined in `cuda-sim/ptx_ir.h`), looked up by name or host function pointer. |
| 10 | **`symbol_table`** | PTX symbol table (defined in `cuda-sim/ptx_ir.h`), one per loaded binary. |

### 2.4 Key Functions (50+)

**Device Management**:
| Function | Purpose |
|----------|---------|
| `cudaGetDeviceCount()` | Returns 1 (simulated GPU) |
| `cudaGetDeviceProperties()` | Fills `cudaDeviceProp` from sim config |
| `cudaDeviceGetAttribute()` | 80+ attributes mapped from config |
| `cudaSetDevice()` / `cudaGetDevice()` | Device selection |

**Memory Management**:
| Function | Purpose |
|----------|---------|
| `cudaMalloc()` | `gpu_malloc()` → increments `m_dev_malloc` from `GLOBAL_HEAP_START` |
| `cudaFree()` | No-op (no GC in simulator) |
| `cudaMemcpy()` | Dispatches to H2D/D2H/D2D memcpy via `stream_operation` |
| `cudaMemcpyAsync()` | Queues memcpy on specified stream |
| `cudaMemset()` | `gpu_memset()` |
| `cudaMallocHost()` / `cudaHostAlloc()` | Pinned memory (host `malloc` + tracking map) |
| `cudaMemcpyToSymbol()` / `FromSymbol()` | Copies to/from global/constant symbols |

**Kernel Execution**:
| Function | Purpose |
|----------|---------|
| `cudaConfigureCall()` | Pushes `kernel_config` onto `g_cuda_launch_stack` |
| `cudaSetupArgument()` | Appends `gpgpu_ptx_sim_arg` to stack top |
| `cudaLaunch()` | Resolves function_info, creates `kernel_info_t`, pushes `stream_kernel_launch` |
| `cudaLaunchKernel()` | Combined configure+args+launch |

**Stream & Event**:
| Function | Purpose |
|----------|---------|
| `cudaStreamCreate()` / `Destroy()` | Manages `CUstream_st` objects |
| `cudaStreamSynchronize()` | Spins on stream empty |
| `cudaEventCreate()` / `Record()` / `Synchronize()` / `ElapsedTime()` | Event timing |
| `cudaDeviceSynchronize()` / `cudaThreadSynchronize()` | Global sync |

**Binary Registration** (called by CUDA runtime init):
| Function | Purpose |
|----------|---------|
| `__cudaRegisterFatBinary()` | Extracts PTX from fat binary using cuobjdump |
| `__cudaRegisterFunction()` | Maps host function pointer → device kernel name |
| `__cudaRegisterVar()` | Registers global/constant variables |
| `__cudaRegisterTexture()` | Registers texture references |
| `__cudaUnregisterFatBinary()` | Cleanup |

### 2.5 Configuration Knobs & Environment Variables

| Variable | Description |
|----------|-------------|
| `CUDA_INSTALL_PATH` | Path to CUDA toolkit (required) |
| `GPGPUSIM_ROOT` | Simulator root directory |
| `PTX_SIM_MODE_FUNC` | `1` = functional simulation only; `0` = performance simulation |
| `CUOBJDUMP_SIM_FILE` | Override binary for cuobjdump extraction |
| `PTX_SIM_USE_PTX_FILE` | Use pre-extracted PTX file |
| `PTX_JIT_PATH` | JIT compilation path |
| `PYTORCH_BIN` | Python/PyTorch binary path |
| `g_cuda_launch_blocking` | Force all launches to be blocking (set via func_sim) |
| `-gpgpu_ptx_use_cuobjdump` | Config knob to enable binary parsing |
| `-gpgpu_ptx_convert_to_ptxplus` | Config knob for PTXPlus mode |
| `-gpgpu_ptx_force_max_capability` | Force a specific SM capability |

### 2.6 Interactions

```
Application
  │ cudaLaunch()
  ▼
cuda_runtime_api.cc
  │ 1. Look up function_info* from host func pointer (CUctx_st::m_kernel_lookup)
  │ 2. Create kernel_info_t(gridDim, blockDim, entry, streamID)
  │ 3. Copy texture binding snapshot into kernel_info_t
  │ 4. stream_manager::push(stream_operation(kernel, sim_mode, stream))
  ▼
stream_manager (src/stream_manager.h)
  │ Enqueue into CUstream_st
  ▼
gpgpu_sim_thread_concurrent (src/gpgpusim_entrypoint.cc)
  │ Picks operation, calls gpu->launch(kernel)
  ▼
gpgpu_sim::cycle() → shader pipeline → memory hierarchy
```

### 2.7 Key Data Structures

```cpp
// GPU memory tracking
std::map<unsigned long long, size_t> g_mallocPtr_Size;  // device ptr → size
std::map<void*, void**>             pinned_memory;       // host ptr → device ptr mapping
std::map<void*, size_t>             pinned_memory_size;  // host ptr → size

// Binary / kernel management
std::map<int, std::string>          fatbinmap;           // fat binary handle → filename
std::map<std::string, symbol_table*> name_symtab;        // filename → symbol table
std::map<const void*, function_info*> m_kernel_lookup;   // host func → device impl

// Pending launch stack
std::list<kernel_config>            g_cuda_launch_stack; // configure → launch chain
```

### 2.8 Terminology

| Term | Definition |
|------|-----------|
| **Fat Binary** | NVIDIA compiled binary containing PTX and/or cubin for multiple architectures |
| **cubin** | Compiled CUDA binary (SASS code) for a specific GPU architecture |
| **Host Function Pointer** | The CPU-side address of `__global__` kernel stub; used as key to find device code |
| **Symbol Table** | Maps PTX symbols (functions, variables) to their definitions and properties |
| **Pinned Memory** | Host memory that cannot be swapped; enables faster DMA transfers |

---

## 3. libopencl — OpenCL Runtime Library

**Location**: `/mnt/disk2/gpgpu-sim_distribution/libopencl/`

### 3.1 Purpose

Implements the **OpenCL 1.x Runtime API**, translating OpenCL calls into the
same underlying simulator infrastructure used by CUDA. OpenCL programs are
compiled to PTX using NVIDIA's `nvopencl_wrapper` tool, then loaded into the
simulator's PTX parser.

### 3.2 Key Files

| File | Role |
|------|------|
| `opencl_runtime_api.cc` (~1,540 lines) | Implements 30+ `cl*()` API functions |
| `Makefile` | Builds `libOpenCL.so` |

### 3.3 Key Classes and Structures (8)

| # | Class / Struct | Description |
|---|----------------|-------------|
| 1 | **`_cl_platform_id`** | OpenCL platform; singleton with static `m_uid=0`. Global instance `g_gpgpu_sim_platform_id`. |
| 2 | **`_cl_device_id`** | Device wrapping `gpgpu_sim *m_gpgpu`. Methods: `next()`, `the_device()`. |
| 3 | **`_cl_context`** | Context holding device reference and memory map `m_hostptr_to_cl_mem`. Methods: `CreateBuffer()`, `lookup_mem()`. |
| 4 | **`_cl_mem`** | Memory object: `m_device_ptr`, `m_host_ptr`, `m_is_on_host`. Supports `CL_MEM_USE_HOST_PTR`, `CL_MEM_ALLOC_HOST_PTR`, `CL_MEM_COPY_HOST_PTR`. |
| 5 | **`_cl_command_queue`** | Command queue: `m_context`, `m_device`. Properties: profiling, out-of-order (warns if used). |
| 6 | **`_cl_program`** | Program from source: `m_pgm` map of `pgm_info` per device. Methods: `Build()` (compiles via nvopencl_wrapper), `CreateKernel()`, `get_ptx()`. |
| 7 | **`pgm_info`** | Per-device program metadata: `m_source`, `m_asm` (compiled PTX), `m_symtab`, `m_kernels: map<string, function_info*>`. |
| 8 | **`_cl_kernel`** | Kernel object: `m_kernel_name`, `m_kernel_impl`, `m_args: map<unsigned, arg_info>`. Methods: `SetKernelArg()`, `bind_args()`, `get_workgroup_size()`. |

### 3.4 Key Functions

| Function | Purpose |
|----------|---------|
| `clGetPlatformIDs()` | Returns 1 platform (GPGPU-Sim) |
| `clGetDeviceIDs()` | Returns simulated GPU |
| `clGetDeviceInfo()` | 80+ attributes from sim config |
| `clCreateContext()` | Creates `_cl_context` wrapping device |
| `clCreateCommandQueue()` | Creates `_cl_command_queue` |
| `clCreateBuffer()` | Allocates on simulated GPU (`gpu_malloc`) |
| `clCreateProgramWithSource()` | Stores OpenCL source |
| `clBuildProgram()` | Compiles via `nvopencl_wrapper` → PTX; loads into simulator |
| `clCreateKernel()` | Extracts `function_info*` by name |
| `clSetKernelArg()` | Sets argument by index |
| `clEnqueueNDRangeKernel()` | Maps OpenCL work dims to CUDA grid/block, creates `kernel_info_t`, calls `gpgpu_opencl_ptx_sim_main_perf()` |
| `clEnqueueReadBuffer()` / `WriteBuffer()` | Memory transfers via `memcpy_to/from_gpu()` |
| `clEnqueueCopyBuffer()` | `memcpy_gpu_to_gpu()` |
| `clFinish()` | Synchronizes command queue |
| `clReleaseMemObject()` | Frees GPU allocation |

### 3.5 OpenCL → CUDA Mapping

```
OpenCL                          CUDA / Simulator
─────────────────────────────   ─────────────────────────
cl_platform_id                  (singleton, no equivalent)
cl_device_id                    _cuda_device_id
cl_context                      CUctx_st
cl_command_queue                CUstream_st (partial)
cl_mem                          device pointer (size_t)
cl_program                      FAT binary + symbol_table
cl_kernel                       function_info*
global_work_size / local_work   gridDim × blockDim
clEnqueueNDRangeKernel          gpgpu_opencl_ptx_sim_main_perf()
```

Work-dimension mapping:
```cpp
GridDim.x  = global_work_size[0] / local_work_size[0]
GridDim.y  = global_work_size[1] / local_work_size[1]
GridDim.z  = global_work_size[2] / local_work_size[2]
BlockDim   = local_work_size[0..2]
```

### 3.6 Build Process for OpenCL Programs

```
1. clCreateProgramWithSource() stores source string
2. clBuildProgram() →
   a. Write source to temp file
   b. Invoke nvopencl_wrapper (calls NVIDIA's OpenCL compiler)
      - Supports OPENCL_REMOTE_GPU_HOST for remote compilation
   c. Read compiled PTX from output
   d. gpgpu_ptx_sim_load_ptx_from_string(ptx)
   e. Build symbol_table, populate m_kernels
3. clCreateKernel() → lookup in pgm_info::m_kernels
```

### 3.7 Configuration / Environment

| Variable | Description |
|----------|-------------|
| `OPENCL_REMOTE_GPU_HOST` | Hostname for remote OpenCL compilation |
| `NVOPENCL_LIBDIR` | Path to NVIDIA's OpenCL compiler library |
| `LD_LIBRARY_PATH` | Must include NVIDIA OpenCL driver libs |

### 3.8 Terminology

| Term | Definition |
|------|-----------|
| **NDRange** | N-Dimensional Range — OpenCL's equivalent of CUDA grid + block |
| **Work Group** | OpenCL equivalent of CUDA thread block (CTA) |
| **Work Item** | OpenCL equivalent of CUDA thread |
| **nvopencl_wrapper** | GPGPU-Sim wrapper script that invokes NVIDIA's OpenCL compiler |

---

## 4. cuobjdump_to_ptxplus — Binary Translation Tool

**Location**: `/mnt/disk2/gpgpu-sim_distribution/cuobjdump_to_ptxplus/`

### 4.1 Purpose

Converts NVIDIA `cuobjdump` output (PTX + ELF + SASS) into **PTXPlus**
format — an extended PTX that preserves SASS-level instruction scheduling.
This enables GPGPU-Sim to model the native ISA more accurately than pure PTX.

### 4.2 Key Files

| File | Role |
|------|------|
| `cuobjdump_to_ptxplus.cc` (143 lines) | Main driver: reads 3 input files, runs parsers, outputs PTXPlus |
| `cuobjdumpInst.h` / `.cc` | `cuobjdumpInst` and `cuobjdumpInstList` classes |
| `elf.y` / `elf.l` | Bison/Flex parser for ELF binary sections |
| `ptx.y` / `ptx.l` | Bison/Flex parser for PTX source |
| `sass.y` / `sass.l` | Bison/Flex parser for SASS disassembly |
| `header.y` / `header.l` | Bison/Flex parser for header directives |
| `Makefile` | Builds `cuobjdump_to_ptxplus` executable |

### 4.3 Key Classes (2)

| Class | Description |
|-------|-------------|
| **`cuobjdumpInst`** | Single instruction with: `m_label`, `m_base` (mnemonic), `m_predicate`, `m_baseModifiers`, `m_typeModifiers`, `m_operands`, `m_predicateModifiers`. Method `printCuobjdumpPtxPlus()` emits PTXPlus format. |
| **`cuobjdumpInstList`** | Container for instruction sequences. Methods: `setRealTexList()` (map texture refs), `printHeaderInstList()` (header directives), `printCuobjdumpPtxPlusList()` (full output). |

### 4.4 Translation Pipeline

```
Input Files:
  ├── PTX file  (.ptx)    ← cuobjdump --dump-ptx
  ├── ELF file  (.elf)    ← cuobjdump --dump-elf
  └── SASS file (.sass)   ← cuobjdump --dump-sass

         │
    ┌────┴────┐
    │ Parsing │  (Bison/Flex)
    ├─────────┤
    │ elf_parse()  → Extract ELF structure & sections
    │ ptx_parse()  → Parse PTX instructions & directives
    │ sass_parse() → Parse SASS instructions & schedules
    └────┬────┘
         │
    ┌────┴────┐
    │ Merging │
    ├─────────┤
    │ Map texture references from PTX into instruction list
    │ Match SASS instructions with PTX operations
    │ Attach scheduling info from SASS to PTX instructions
    └────┬────┘
         │
         ▼
    PTXPlus output file
    (PTX + native scheduling)
```

### 4.5 Usage

```bash
cuobjdump_to_ptxplus <ptx_file> <elf_file> <sass_file>
```

The tool is invoked automatically by the simulator when
`-gpgpu_ptx_convert_to_ptxplus 1` is set and CUDA ≥ 4.0 is available.

### 4.6 Interactions

- Called by `libcuda`'s `extract_code_using_cuobjdump()` during `__cudaRegisterFatBinary()`.
- Output PTXPlus is loaded by `gpgpu_ptx_sim_load_ptx_from_filename()` into the PTX parser.
- Requires `cuobjdump` from the CUDA toolkit (`$CUDA_INSTALL_PATH/bin/cuobjdump`).

### 4.7 Terminology

| Term | Definition |
|------|-----------|
| **PTXPlus** | Extended PTX format preserving native instruction scheduling from SASS |
| **SASS** | Streaming Assembler — NVIDIA's native GPU ISA |
| **ELF** | Executable and Linkable Format — binary format containing compiled GPU code |
| **cuobjdump** | NVIDIA tool to dump PTX/SASS/ELF sections from compiled CUDA binaries |

---

## 5. aerialvision — Performance Visualization Tool

**Location**: `/mnt/disk2/gpgpu-sim_distribution/aerialvision/`

### 5.1 Purpose

Post-simulation **interactive visualization** tool written in Python. Parses
GPGPU-Sim statistics output files and creates graphs / annotated source views
for performance analysis, debugging bottlenecks, and publication figures.

### 5.2 Key Files

| File | Role |
|------|------|
| `startup.py` | Application entry point; creates GUI tabs |
| `guiclasses.py` | GUI components: `formEntry`, `subplotInstance`, `graphManager`, `newTextTab` |
| `variableclasses.py` | Data structures: `variable`, `bookmark`, `cudaLineNo`, `ptxLineNo` |
| `configs.py` | Configuration management (`AerialVisionConfig`) |
| `lexyacc.py` | PLY-based parser for GPGPU-Sim stat output (lex + yacc rules) |
| `lexyaccbookmark.py` | Bookmark / line-number parser |
| `lexyacctexteditor.py` | Source annotation parser |
| `organizedata.py` | Data aggregation and organisation |

### 5.3 Key Classes / Components (8+)

| # | Class / Module | Description |
|---|----------------|-------------|
| 1 | **`variable`** | Named statistical value: `value`, `name`, `category`. Methods: `get_value()`, `format_value()`. |
| 2 | **`bookmark`** | Navigation marker: `name`, `lineno`. Used to jump to specific stats sections. |
| 3 | **`cudaLineNo`** | CUDA source line → statistics mapping. |
| 4 | **`ptxLineNo`** | PTX instruction line → statistics mapping. |
| 5 | **`formEntry`** (GUI) | Tab form for graph configuration: X/Y axis variable dropdowns, filter options. Generates matplotlib plots. |
| 6 | **`subplotInstance`** | Multiple subplots in one matplotlib figure. |
| 7 | **`graphManager`** | Orchestrates graph rendering, export to PNG/PDF. |
| 8 | **`newTextTab`** | Source code viewer with per-line statistics annotations. |
| 9 | **`PlotFormatInfo`** | Graph formatting: font sizes for title, labels, ticks. |
| 10 | **`AerialVisionConfig`** | INI-style config parser for AerialVision settings. |

### 5.4 Parsing Pipeline

```
GPGPU-Sim simulation run
  → Generates stdout with statistics blocks
  → Redirect to file: sim_output.txt

AerialVision startup:
  1. lexyacc.py parses sim_output.txt
     - PLY lexer tokenizes "variable = value" pairs
     - PLY parser groups by categories (GPU, L1, L2, etc.)
     - Creates `variable` objects
  2. lexyaccbookmark.py parses line-number mappings
     - Links CUDA source lines to PTX instructions
  3. organizedata.py aggregates:
     - By kernel name
     - By block/thread ID
     - By instruction type
     - By memory location
  4. GUI displays tabs for graph creation & source viewing
```

### 5.5 Visualization Capabilities

| Graph Type | Metric |
|-----------|--------|
| Cache hit rate over time | L1/L2 data cache, texture cache, constant cache |
| IPC (Instructions Per Cycle) | Per-SM and aggregate |
| Memory bandwidth | DRAM reads/writes, per partition |
| Warp efficiency | Active threads / warp_size |
| Occupancy | Active warps / max warps |
| Power consumption | Via AccelWattch integration |
| Pipeline stalls | Issue stall reasons |
| Bank conflicts | Shared memory conflict counts |
| Custom expressions | User-defined formulas over any stat variable |

### 5.6 Dependencies

```
python-pmw         # Python MegaWidgets (GUI framework)
python-ply         # Python Lex-Yacc (parser generator)
python-numpy       # Numerical computation
libpng12-dev       # PNG image generation
python-matplotlib  # Graph rendering
```

### 5.7 Configuration

AerialVision reads an optional configuration file for:
- Default graph types and variables
- Font sizes and formatting
- Output directory for generated figures
- Window size and layout preferences

### 5.8 Interactions

```
gpgpu_sim::print_stats()
  → Writes statistics to stdout in parseable format
  → Format: "variable_name = value"  grouped by category headers
  → Repeated at end of each kernel and at simulation end

AerialVision reads this output and creates interactive visualizations.
It does NOT connect to the simulator at runtime — it is a post-processing tool.
```

### 5.9 Terminology

| Term | Definition |
|------|-----------|
| **PLY** | Python Lex-Yacc — parser generator library used to parse stat output |
| **PMW** | Python MegaWidgets — Tkinter extension for complex GUI widgets |
| **stat block** | Group of related statistics printed together (e.g., per-kernel, per-SM) |
| **matplotlib** | Python plotting library used for all graph rendering |

---

## 6. Cross-Library Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                CUDA / OpenCL Application                     │
└──────────┬─────────────────────────────┬────────────────────┘
           │                             │
     ┌─────▼─────┐                ┌─────▼──────┐
     │  libcuda   │                │ libopencl  │
     │ (CUDA RT)  │                │ (OpenCL RT)│
     │            │                │            │
     │ cudaMalloc │                │ clCreateBuf│
     │ cudaLaunch │                │ clEnqueue  │
     │ cudaMemcpy │                │ NDRange    │
     └─────┬──────┘                └──────┬─────┘
           │                              │
           │  Both create kernel_info_t   │
           │  and push stream_operations  │
           └──────────┬───────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │ cuobjdump_to_ptxplus   │ ← invoked during
         │ (binary translation)    │   __cudaRegisterFatBinary
         │                        │   when ptxplus mode enabled
         │ PTX+ELF+SASS → PTXPlus│
         └────────────┬───────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │     GPGPU-Sim Core     │
         │  (src/ infrastructure) │
         │                        │
         │  abstract_hardware_    │
         │    model.h/.cc         │
         │  gpgpusim_entrypoint   │
         │  stream_manager        │
         │  option_parser         │
         └────────────┬───────────┘
                      │
                      │ simulation output
                      ▼
         ┌────────────────────────┐
         │    aerialvision/       │
         │ (post-processing viz)  │
         │                        │
         │  Parse stats → Graphs  │
         │  Source annotation     │
         │  Interactive analysis  │
         └────────────────────────┘
```

---

## 7. Comprehensive Terminology

| Term | Definition |
|------|-----------|
| **FAT Binary** | Compiled CUDA binary containing PTX and/or cubin for multiple GPU architectures |
| **PTX** | Parallel Thread Execution — NVIDIA's virtual ISA; the simulator's primary input |
| **PTXPlus** | Extended PTX preserving native instruction scheduling from SASS assembly |
| **SASS** | Streaming Assembler — NVIDIA's native GPU instruction set architecture |
| **cuobjdump** | NVIDIA tool for extracting PTX/SASS/ELF sections from compiled binaries |
| **cubin** | Compiled binary for a specific GPU compute capability |
| **ELF** | Executable and Linkable Format — standard binary container format |
| **CTA** | Cooperative Thread Array — CUDA thread block |
| **Warp** | 32 threads executing in lockstep |
| **NDRange** | N-Dimensional Range — OpenCL's grid+block launch specification |
| **Work Group** | OpenCL's thread block (equivalent to CTA) |
| **Work Item** | OpenCL's thread |
| **Stream** | Ordered sequence of GPU operations (memcpy, kernel, event) |
| **Event** | Synchronization marker in a stream |
| **Pinned Memory** | Non-pageable host memory for faster DMA |
| **Symbol Table** | Maps function/variable names to definitions in PTX |
| **AccelWattch** | Power modelling framework integrated into GPGPU-Sim |
| **BookSim** | Interconnection network simulator used for on-chip networks |
| **Accel-Sim** | Trace-driven simulation framework extending GPGPU-Sim 4.0 |
| **NVBit** | NVIDIA's dynamic binary instrumentation tool for generating SASS traces |
| **PLY** | Python Lex-Yacc library used by AerialVision |
| **nvopencl_wrapper** | Script that invokes NVIDIA's OpenCL-to-PTX compiler |
| **Functional Simulation** | Execute instructions for correctness; no timing |
| **Performance Simulation** | Cycle-accurate timing model |
| **CDP** | CUDA Dynamic Parallelism — device-side kernel launches |
