# cuda-sim Module — Research Report

> **Module path:** `src/cuda-sim/`
> **Files analysed:** cuda-sim.{h,cc}, ptx_sim.{h,cc}, ptx_ir.{h,cc}, ptx_loader.{h,cc}, instructions.cc, memory.{h,cc}, ptx_parser.h, ptx-stats.{h,cc}, opcodes.{h,def}
> **Total LOC ≈ 13 000** across 7 key source files.

---

## 1. Purpose

The **cuda-sim** module is the **functional simulation engine** for GPGPU-Sim.
It parses PTX/PTXPlus assembly into an internal IR, decodes instructions, and
executes them on a per-thread basis inside warps and CTAs, modelling all CUDA
memory spaces (global, shared, local, constant, texture).  It provides the
ground-truth architectural state that the timing model consults; latencies
attached to instructions are approximations consumed downstream by the
performance simulator.

---

## 2. Key Classes

| # | Class / Struct | File | Role |
|---|----------------|------|------|
| 1 | `cuda_sim` | cuda-sim.h | Top-level simulation context; owns config knobs, global lookup maps, kernel launch entry points |
| 2 | `functionalCoreSim` | cuda-sim.h | Executes one CTA functionally: creates warps, runs the warp-round-robin loop, handles barriers |
| 3 | `ptx_thread_info` | ptx_sim.h | Per-thread execution state: register file, PC, call stack, memory accessors, instruction execution |
| 4 | `ptx_cta_info` | ptx_sim.h | Per-CTA bookkeeping: thread membership, barrier counter, exit tracking |
| 5 | `ptx_warp_info` | ptx_sim.h | Per-warp done-thread counter |
| 6 | `function_info` | ptx_ir.h | Represents one PTX function/kernel: instruction memory, basic blocks, PDOM tree, parameters |
| 7 | `ptx_instruction` | ptx_ir.h | Single PTX instruction (extends `warp_inst_t`): opcode, operands, type, modifiers, cached pre-decode |
| 8 | `operand_info` | ptx_ir.h | Operand descriptor: register, immediate, memory, vector, builtin, with address-space annotation |
| 9 | `symbol` / `symbol_table` | ptx_ir.h | PTX symbol and hierarchical scope table; manages registers, variables, labels, type info |
| 10 | `basic_block_t` | ptx_ir.h | CFG node: predecessor/successor/dominator/postdominator sets |
| 11 | `memory_space` / `memory_space_impl<BSIZE>` | memory.h | Abstract + templated sparse-page memory model (block sizes 32 B – 16 KB) |
| 12 | `mem_storage<BSIZE>` | memory.h | Single memory page of BSIZE bytes backed by `calloc`'d buffer |
| 13 | `ptx_recognizer` | ptx_parser.h | Flex/Bison parser state: scanner handle, directive/instruction builder methods |
| 14 | `ptxinfo_data` | ptx_loader.h | PTX loading pipeline: string→parse→assemble; ptxas integration |
| 15 | `ptx_stats` | ptx-stats.h | Per-source-line profiling: exec count, latency, DRAM traffic, bank conflicts, warp divergence |

---

## 3. Representative Snippets

### 3.1 Instruction dispatch via macro-generated switch (cuda-sim.cc ≈ L1870)

```cpp
switch (inst_opcode) {
#define OP_DEF(OP, FUNC, STR, DST, CLASSIFICATION) \
  case OP:                                         \
    FUNC(pI, this);                                \
    op_classification = CLASSIFICATION;            \
    break;
#define OP_W_DEF(OP, FUNC, STR, DST, CLASSIFICATION) \
  case OP:                                           \
    FUNC(pI, get_core(), inst);                      \
    op_classification = CLASSIFICATION;              \
    break;
#include "opcodes.def"
#undef OP_DEF
#undef OP_W_DEF
  default:
    printf("Execution error: Invalid opcode (0x%x)\n", pI->get_opcode());
    break;
}
```

### 3.2 Per-thread instruction execution entry (cuda-sim.cc ≈ L1793)

```cpp
void ptx_thread_info::ptx_exec_inst(warp_inst_t &inst, unsigned lane_id) {
  bool skip = false;
  addr_t pc = next_instr();
  assert(pc == inst.pc);  // timing ↔ functional sync check
  const ptx_instruction *pI = m_func_info->get_instruction(pc);
  set_npc(pc + pI->inst_size());

  try {
    clearRPC();
    if (pI->has_pred()) {
      const operand_info &pred = pI->get_pred();
      ptx_reg_t pred_value = get_operand_value(pred, pred, PRED_TYPE, this, 0);
      if (pI->get_pred_mod() == -1)
        skip = (pred_value.pred & 0x0001) ^ pI->get_pred_neg();
      else
        skip = !pred_lookup(pI->get_pred_mod(), pred_value.pred & 0x000F);
    }
    // ... dispatch switch ...
  } catch (int x) {
    printf("GPGPU-Sim PTX: ERROR (%d) ...\n", x);
    abort();
  }
}
```

### 3.3 Templated sparse memory read (memory.h / memory.cc)

```cpp
template <unsigned BSIZE>
class memory_space_impl : public memory_space {
  typedef mem_map<mem_addr_t, mem_storage<BSIZE>> map_t;
  map_t m_data;  // sparse page table

  void read(mem_addr_t addr, size_t length, void *data) const;
  void write(mem_addr_t addr, size_t length, const void *data,
             ptx_thread_info *thd, const ptx_instruction *pI);
};
// Instantiated for block sizes: 32, 64, 8192, 16384 bytes
```

### 3.4 Post-dominator analysis (ptx_ir.cc ≈ L728)

```cpp
void function_info::find_postdominators() {
  // Muchnick's Adv. Compiler Design & Implementation Fig 7.14
  assert(m_basic_blocks.size() >= 2);
  // Seed: exit block post-dominates only itself
  (*m_basic_blocks.rbegin())->postdominator_ids.insert(
      (*m_basic_blocks.rbegin())->bb_id);
  // All others start with full universe set
  for (auto bb = ++m_basic_blocks.rbegin(); bb != m_basic_blocks.rend(); bb++)
    for (unsigned i = 0; i < m_basic_blocks.size(); i++)
      (*bb)->postdominator_ids.insert(i);
  // Fixed-point iteration: intersect successor pdom sets, add self
  bool change = true;
  while (change) { /* ... */ }
}
```

### 3.5 ptx_reg_t union (ptx_sim.h)

```cpp
union ptx_reg_t {
  signed char s8;    signed short s16;   signed int s32;    signed long long s64;
  unsigned char u8;  unsigned short u16;  unsigned int u32;  unsigned long long u64;
  half f16;  float f32;  double f64;
  struct { unsigned ls; unsigned ms; } bits;
  struct { unsigned int lowest, low, high, highest; } u128;
  unsigned pred : 4;

  void mask_and(unsigned ms, unsigned ls);
  void mask_or(unsigned ms, unsigned ls);
  int get_bit(unsigned bit);
};
```

---

## 4. Data Flow — PTX Instruction Lifecycle

```
┌────────────────────────────────────────────────────────────────┐
│  STAGE 1 — PTX STRING LOADING  (ptx_loader.cc)                │
│  gpgpu_ptx_sim_load_ptx_from_string(const char *p)            │
│    → init_parser() → ptx_lex_init() → ptx__scan_string()     │
│    → ptx_parse(scanner)  [Flex/Bison grammar in ptx.l/ptx.y] │
│    → ptx_lex_destroy() → returns symbol_table*                │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  STAGE 2 — IR CONSTRUCTION  (ptx_ir.cc / ptx_parser.h)       │
│  ptx_recognizer builds:                                       │
│    • symbol_table  (variables, labels, types)                 │
│    • function_info (instruction list per kernel)              │
│    • operand_info  per operand                                │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  STAGE 3 — ASSEMBLY  (cuda-sim.cc, function_info::ptx_assemble)│
│  • Assign globally-unique PCs                                  │
│  • Build m_instr_mem[] array  (indexed by PC offset)           │
│  • Resolve branch-target labels → PCs                          │
│  • Populate global g_pc_to_insn[] lookup                       │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  STAGE 4 — CFG + PDOM ANALYSIS  (ptx_ir.cc, do_pdom)          │
│  create_basic_blocks → connect_basic_blocks                   │
│  → find_dominators → find_idominators (loop until stable)     │
│  → find_postdominators → find_ipostdominators                 │
│  → pre_decode() each instruction (opcode classification,      │
│    latency from config, operand parsing, memory-space resolve) │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  STAGE 5 — FETCH  (runtime)                                    │
│  m_func_info->get_instruction(pc) → m_instr_mem[pc - start]   │
│  Returns cached ptx_instruction*                               │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  STAGE 6 — DECODE + EXECUTE  (cuda-sim.cc / instructions.cc)  │
│  ptx_thread_info::ptx_exec_inst()                              │
│    1. Evaluate predicate → skip if false                       │
│    2. switch(opcode) dispatches to *_impl function             │
│       (150+ opcodes via #include "opcodes.def")                │
│    3. *_impl reads operands via get_operand_value()            │
│    4. Computes result, writes via set_operand_value()          │
│    5. Memory ops: resolve space → read/write memory_space_impl │
│    6. Update PC, collect per-line stats                        │
└────────────────────────────────────────────────────────────────┘
```

**Warp-level loop** (`functionalCoreSim::execute`):
```
for each CTA:
  initializeCTA() → create threads, assign tid/ctaid
  while (someOneLive):
    for each warp:
      if not at_barrier and liveThreads > 0:
        fetch warp instruction
        execute_warp_inst_t() → per-lane ptx_exec_inst()
        updateSIMTStack()  (divergence / reconvergence)
```

---

## 5. Config / Knobs

| # | Parameter | Default | What it controls |
|---|-----------|---------|------------------|
| 1 | `-ptx_opcode_latency_int` | `1,1,19,25,145,32` | Integer ALU latencies: ADD, MAX, MUL, MAD, DIV, SHFL |
| 2 | `-ptx_opcode_latency_fp` | `1,1,1,1,30` | FP32 latencies: ADD, MAX, MUL, MAD, DIV |
| 3 | `-ptx_opcode_latency_dp` | `8,8,8,8,335` | FP64 latencies: ADD, MAX, MUL, MAD, DIV |
| 4 | `-ptx_opcode_latency_sfu` | `8` | SFU instruction latency (sin, cos, rcp, …) |
| 5 | `-ptx_opcode_latency_tesnor` | `64` | Tensor-core (WMMA/MMA) instruction latency |
| 6 | `-ptx_opcode_initiation_int` | `1,1,4,4,32,4` | Integer initiation intervals: ADD, MAX, MUL, MAD, DIV, SHFL |
| 7 | `-ptx_opcode_initiation_fp` | `1,1,1,1,5` | FP32 initiation intervals |
| 8 | `-ptx_opcode_initiation_dp` | `8,8,8,8,130` | FP64 initiation intervals |
| 9 | `-ptx_opcode_initiation_sfu` | `8` | SFU initiation interval |
| 10 | `-ptx_opcode_initiation_tensor` | `64` | Tensor initiation interval |
| 11 | `-cdp_latency` | `7200,8000,100,12000,1600` | CDP API latencies (StreamCreate, GetParamBuf init/kernel, LaunchDevice init/kernel) |
| 12 | `-save_embedded_ptx` | `0` | Save PTX files embedded in binary as `<n>.ptx` |
| 13 | `-keep` | `0` | Keep intermediate files from external tool integration |
| 14 | `-gpgpu_ptx_save_converted_ptxplus` | `0` | Save converted PTXPlus to file |
| 15 | `-gpgpu_occupancy_sm_number` | `0` | SM number passed to ptxas for register-usage / occupancy |
| 16 | `-enable_ptx_file_line_stats` | `1` | Enable per-PTX-source-line profiling |
| 17 | `-ptx_line_stats_filename` | `gpgpu_inst_stats.txt` | Output file for source-line statistics |

**Environment variables** (read in `read_sim_environment_variables`):

| Variable | Effect |
|----------|--------|
| `PTX_SIM_MODE_FUNC` | `1` = functional-only, `0` = detailed performance sim |
| `GPGPUSIM_DEBUG` | Enable interactive debugger |
| `PTX_SIM_DEBUG` | Set debug verbosity level (integer) |
| `PTX_SIM_DEBUG_THREAD_UID` | Restrict debug trace to one thread UID |
| `PTX_SIM_DEBUG_PC` | Restrict debug trace to one PC address |
| `PTX_SIM_USE_PTX_FILE` | Override embedded PTX with external `.ptx` file |
| `CUDA_LAUNCH_BLOCKING` | Force synchronous kernel launches |

---

## 6. Interactions

| External Module | Header Included | Interaction |
|-----------------|-----------------|-------------|
| **gpu-sim** (`../gpgpu-sim/gpu-sim.h`) | cuda-sim.cc | GPU top-level: `gpgpu_sim` owns memories, launches kernels, provides `get_config()` |
| **shader core** (`../gpgpu-sim/shader.h`) | cuda-sim.cc (via gpu-sim) | `core_t` / `shader_core_ctx`: warp scheduling, SIMT stack updates, HW CTA/warp IDs |
| **abstract HW model** (`../abstract_hardware_model.h`) | memory.h, ptx_ir.h | `warp_inst_t` base class, `address_type`, `memory_space_t` enum, `kernel_info_t` |
| **libcuda context** (`../../libcuda/gpgpu_context.h`) | cuda-sim.cc | Global `gpgpu_context` singleton: `func_sim`, `ptx_parser`, `stats` sub-objects |
| **stream manager** (`../stream_manager.h`) | cuda-sim.cc | Kernel launch queuing and synchronisation |
| **stat wrapper** (`../statwrapper.h`) | cuda-sim.cc | `StatCreate`, `StatSample` macros for histogram collection |
| **device runtime** (`cuda_device_runtime.h`) | cuda-sim.cc | CUDA Dynamic Parallelism: device-side kernel launch, child grid management |
| **option parser** (`../option_parser.h`) | ptx_loader.cc, ptx-stats.cc, cuda-sim.cc | `option_parser_register` for all config knobs |

---

## 7. Terminology

| Term | Definition |
|------|-----------|
| **PTX** | Parallel Thread Execution — NVIDIA's virtual ISA; text assembly compiled from CUDA C++ |
| **PTXPlus** | Extended PTX dialect used internally by GPGPU-Sim with additional microarchitectural hints |
| **CTA** | Cooperative Thread Array — CUDA thread block; unit of scheduling onto an SM |
| **Warp** | Group of threads (typically 32) executing in lock-step |
| **Lane** | A single thread's position within a warp (0..warp_size-1) |
| **SIMT Stack** | Per-warp stack tracking active masks at divergent branches; uses PDOM reconvergence |
| **PDOM / Immediate Post-Dominator** | Basic block that all paths from a given block must pass through; used as reconvergence point |
| **Reconvergence Point (RPC)** | PC where diverged warp threads rejoin; derived from IPDOM analysis |
| **Active Mask** | Bit-vector indicating which lanes in a warp are active for the current instruction |
| **Predicate** | 4-bit condition register governing conditional execution of individual instructions |
| **SFU** | Special Function Unit — hardware for transcendentals (sin, cos, rsqrt, log2, exp2) |
| **Functional Simulation** | Execution for correctness (computes results); no pipeline timing |
| **Memory Space** | One of: global, shared, local, constant, texture, generic, param — each with distinct address range |
| **Generic Address** | Unified address space; resolved at runtime to shared, local, or global via range checks |
| **Pre-decode** | One-time pass over assembled instructions to classify opcode, set latency, parse operands |
| **Opcode Initiation Interval** | Minimum cycles between issuing consecutive instructions of same type |
| **CDP** | CUDA Dynamic Parallelism — launching kernels from device code |
| **WMMA / MMA** | Warp Matrix Multiply-Accumulate — tensor-core instructions; warp-synchronous |
| **Barrier (BAR)** | CTA-wide synchronisation point; all threads must arrive before any proceed |
| **Register Frame** | Per-function-call register map in the thread's register file stack (`m_regs[]`) |

---

## 8. Algorithms & Mechanisms

### 8.1 Post-Dominator-Based Reconvergence

**Purpose:** Determine where diverged warp threads should re-converge.

**Algorithm (Muchnick Fig 7.14 / 7.15):**
1. Build CFG via `create_basic_blocks()` + `connect_basic_blocks()`.
2. Compute dominator sets (iterative fixed-point intersection over predecessors).
3. Compute post-dominator sets (same, but traversing successors in reverse).
4. Extract immediate post-dominators: for each block *n*, the unique block in
   `pdom(n) \ {n}` that does not post-dominate any other member of that set.
5. At each branch instruction, the IPDOM of the branch block becomes the
   **reconvergence PC** pushed onto the SIMT stack.
6. Cached in `function_info` (`pdom_done` flag) so analysis runs once per kernel.

### 8.2 Macro-Driven Instruction Dispatch

**Purpose:** Map 150+ PTX opcodes to implementation functions without a giant hand-written switch.

**Mechanism:**
- `opcodes.def` defines `OP_DEF(OP, FUNC, STR, DST, CLASSIFICATION)` entries.
- Included three ways:
  - In `opcodes.h` with `#define OP_DEF(OP,...) OP,` → builds `enum opcode_t`.
  - In `cuda-sim.cc` with `#define OP_DEF(OP,FUNC,...) case OP: FUNC(pI,this); break;` → builds dispatch switch.
  - `OP_W_DEF` variant passes `(pI, core, inst)` for warp-synchronous ops (MMA).
- Classification field (1–11) drives pipeline-unit assignment downstream.

### 8.3 Sparse Paged Memory Model

**Purpose:** Simulate CUDA memory spaces with low host-memory overhead.

**Design:**
- `memory_space_impl<BSIZE>` uses a hash-map (`tr1_hash_map`) keyed by page index.
- Pages (`mem_storage<BSIZE>`) are `calloc`'d on first access → zero-initialized, sparse.
- **Fast path:** access fits in one block → single `memcpy`.
- **Slow path:** access spans blocks → loop over page boundaries.
- Block sizes chosen per space: 32 B (shared), 64 B, 8 KB, 16 KB (local).
- Watchpoint support: `set_watch(addr, id)` triggers notification on matching writes.

### 8.4 Predicated Execution & Warp Divergence Handling

**Purpose:** Execute PTX's per-thread predicated instructions correctly within SIMT.

**Mechanism:**
1. Each instruction may carry a predicate register (`@p` / `@!p`).
2. In `ptx_exec_inst`, predicate is evaluated; if false, `skip = true` and
   `inst.set_not_active(lane_id)` clears the lane's active-mask bit.
3. For branch instructions (`BRA_OP`), each lane computes taken/not-taken.
4. The SIMT stack splits the warp: pushes two entries (taken-mask, not-taken-mask)
   with the IPDOM as reconvergence PC.
5. Warp executes each path in turn; when PC reaches the reconvergence PC, the
   stack is popped and masks merged.
6. Tensor-core ops (`MMA_OP`) **assert** all lanes active — no divergence allowed.

---

## 9. State Machines

### 9.1 Thread Lifecycle FSM

```
  ┌──────┐   set_info()   ┌────────────┐  ptx_exec_inst()  ┌─────────┐
  │ NEW  │ ──────────────→ │ INITIALIZED│ ────────────────→ │ RUNNING │
  └──────┘                 └────────────┘                   └────┬────┘
                                                                 │
                                                    BAR_OP       │  EXIT_OP /
                                                 ┌───────────┐   │  set_done()
                                                 │AT_BARRIER │ ←─┤
                                                 └─────┬─────┘   │
                                                       │ all     ▼
                                                       │ arrive ┌──────┐
                                                       └──────→ │ DONE │
                                                                └──────┘
```

- **NEW → INITIALIZED:** `ptx_sim_init_thread()` creates `ptx_thread_info`, calls `set_info(func)` to bind function and symbol table.
- **INITIALIZED → RUNNING:** First call to `ptx_exec_inst()`.
- **RUNNING → AT_BARRIER:** Thread executes `BAR_OP`; `m_at_barrier = true`, CTA barrier counter incremented.
- **AT_BARRIER → RUNNING:** When all CTA threads arrive at barrier, counter resets, `m_at_barrier` cleared.
- **RUNNING → DONE:** Thread executes `EXIT_OP` or falls off function end; `set_done()`, `m_thread_done = true`.

### 9.2 Warp Barrier State (in `functionalCoreSim`)

```
  ┌─────────┐  BAR_OP hit   ┌────────────────┐  all warps at barrier
  │ RUNNING │ ────────────→  │ m_warpAtBarrier│ ────────────────────→  RUNNING
  └─────────┘    [i]=true    │     [i]=true   │   reset all [i]=false
                             └────────────────┘
```

Each warp has `m_warpAtBarrier[warp_id]` — skipped in the round-robin loop
until all warps reach the barrier, then all flags are cleared.

### 9.3 Function Call Stack

```
  CALL_OP → callstack_push(npc, rpc, ret_var_src, ret_var_dst, call_uid)
            → m_regs.push_back(new_frame)     // new register frame
            → m_callstack.push_back(entry)     // save return state

  RET_OP  → callstack_pop()
            → m_regs.pop_back()                // restore caller frame
            → restore m_PC, m_RPC from stack_entry
```

---

## 10. Error / Edge Cases

### 10.1 Timing ↔ Functional Sync Assertion

```cpp
assert(pc == inst.pc);  // cuda-sim.cc:1797
```
Fires if the timing model's PC diverges from the functional model's PC,
indicating a desync between the two simulation layers.

### 10.2 Execution on Done Thread

```cpp
if (is_done()) {
    printf("attempted to execute instruction on a thread that is already done.\n");
    assert(0);
}
```

### 10.3 Unaligned Cross-Block Memory Access

```cpp
// memory.cc — slow path
throw 1;  // on unaligned inter-block memory access
```
Caught by `ptx_exec_inst`'s `catch(int x)` handler, which prints the faulting
instruction's source location and calls `abort()`.

### 10.4 Tensor Core Active-Mask Check

```cpp
if ((inst_opcode == MMA_OP || ...) && inst.active_count() != MAX_WARP_SIZE) {
    printf("Tensor Core operation are warp synchronous ... All threads needs to be active.");
    assert(0);
}
```
MMA/WMMA instructions must execute with a full warp — divergence is illegal.

### 10.5 CTA Cleanup Validation

```cpp
void ptx_cta_info::check_cta_thread_status_and_reset() {
    if (m_threads_that_have_exited.size() != m_threads_in_cta.size()) {
        printf("Execution error: Some threads still running...\n");
        abort();
    }
}
```
Fires if a CTA is torn down while threads are still live — indicates a
simulation bug.

### 10.6 PDOM Block Count Assertion

```cpp
assert(m_basic_blocks.size() >= 2);  // must have distinguished entry + exit blocks
```
Both dominator and post-dominator algorithms require at least an entry and exit
block; failing this indicates malformed PTX.

### 10.7 Invalid Opcode Fallthrough

```cpp
default:
    printf("Execution error: Invalid opcode (0x%x)\n", pI->get_opcode());
    break;
```
Graceful message (but no abort) for unknown opcodes in the dispatch switch.

### 10.8 Parser Error Recovery

PTX parser errors (`ptx_loader.cc`) trigger extraction of the PTX source to a
file for debugging, followed by `abort()`.  Duplicate-symbol conflicts are
detected and patched via string processing before re-parsing.

### 10.9 Watchpoint Triggered Notification

`memory_space_impl::set_watch()` registers address watchpoints.  On any write
to a watched address, the simulator prints the thread UID, instruction, old
value, and new value — useful for debugging data races.

---

*Generated for internal wiki documentation.*
