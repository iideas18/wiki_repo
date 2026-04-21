# GPGPU-Sim Core Infrastructure — Research Report

> **Scope**: Root-level source files in `src/` — the hardware abstraction layer,
> simulator entry point, stream management, option parsing, debugging and tracing.

---

## 1. File Inventory (src/ root)

| File | Size | Role |
|------|------|------|
| `abstract_hardware_model.h` | 48 KB | Hardware abstraction: types, enums, base classes |
| `abstract_hardware_model.cc` | 45 KB | Implementations: memory coalescing, SIMT stack, kernel management |
| `gpgpusim_entrypoint.h` | 2.7 KB | Simulator context (`GPGPUsim_ctx`) |
| `gpgpusim_entrypoint.cc` | 15 KB | Simulation threads, init, synchronization |
| `stream_manager.h` | 8.7 KB | CUDA stream / event types |
| `stream_manager.cc` | 17 KB | Stream scheduling, operation dispatch |
| `option_parser.h` | 2.8 KB | C-style option parser API |
| `option_parser.cc` | 17 KB | Template-based option registry, file/cmdline parsing |
| `debug.h` | 3.0 KB | `brk_pt` class (breakpoints/watchpoints) |
| `debug.cc` | 7.9 KB | Interactive PTX debugger loop |
| `trace.h` | 3.6 KB | Tracing macros (`DPRINTF`, `DTRACE`) |
| `trace.cc` | 2.3 KB | Trace stream initialization |
| `trace_streams.tup` | — | X-macro enum: `WARP_SCHEDULER`, `SCOREBOARD`, etc. |
| `statwrapper.h` | 0.3 KB | Statistics wrapper API |
| `statwrapper.cc` | 1.1 KB | Wraps BookSim `Stats` class |
| `tr1_hash_map.h` | 2.2 KB | Portability shim: `unordered_map` / `map` |

---

## 2. Purpose of Each File Group

### 2.1 abstract_hardware_model.h / .cc — Hardware Abstraction Layer

**Purpose**: Defines every data structure that the timing model operates on,
independent of the concrete `gpgpu_sim` implementation. Any class that needs
to talk about warps, instructions, memory accesses, or kernels includes this
header.

### 2.2 gpgpusim_entrypoint.h / .cc — Simulator Entry Point

**Purpose**: Owns the simulation thread(s), GPU object creation,
configuration loading, and the main simulation loop(s). This is where the
simulated GPU is born (`gpgpu_ptx_sim_init_perf`) and where each cycle is
driven.

### 2.3 stream_manager.h / .cc — CUDA Stream Management

**Purpose**: Models CUDA streams and events. Operations (memcpy, kernel
launch, event record, event wait) are queued per stream and dispatched
round-robin by the simulation thread.

### 2.4 option_parser.h / .cc — Configuration Parsing

**Purpose**: A self-contained, type-safe option parser used throughout the
simulator. Supports command-line flags, `.config` files, and delimited
strings. All `-gpgpu_*` knobs pass through this parser.

### 2.5 debug.h / .cc — Interactive PTX Debugger

**Purpose**: Provides GDB-style interactive debugging of PTX execution at
the simulator level — breakpoints by source line, watchpoints on global
memory addresses, pipeline dumping.

### 2.6 trace.h / .cc — Selective Tracing

**Purpose**: gem5-inspired per-subsystem tracing. Streams are defined via
the X-macro `trace_streams.tup` and enabled at runtime through a config
string.

### 2.7 statwrapper.h / .cc — Statistics Collection Wrapper

**Purpose**: Thin C wrapper around BookSim's `Stats` histogram class,
providing `StatCreate`, `StatAddSample`, `StatAverage`, `StatMax`, etc.

---

## 3. Key Classes and Structures (20+)

### From abstract_hardware_model.h

| # | Class / Struct | Description |
|---|----------------|-------------|
| 1 | **`kernel_info_t`** | Represents a launched kernel: grid/block dims, UID, stream ID, CTA iteration state, parent/child for CDP, launch latency, texture snapshots. |
| 2 | **`core_config`** | Per-core configuration: `warp_size`, shared-memory bank parameters, coalescing arch, cache line sizes, `gpgpu_max_insn_issue_per_warp`. |
| 3 | **`simt_stack`** | PDOM-based SIMT reconvergence stack per warp. Implements `launch()`, `update()` (branch divergence handling), `get_active_mask()`. |
| 4 | **`inst_t`** | Base decoded instruction: PC, opcode (`op_type`), barrier info, operand types, latency, initiation interval, register file mapping. |
| 5 | **`warp_inst_t`** (extends `inst_t`) | Instruction bound to a warp: active mask, per-thread addresses, memory access queue (`m_accessq`), coalescing logic, atomic callbacks, CDP flag. |
| 6 | **`mem_access_t`** | Single memory access: address, type (`GLOBAL_ACC_R`, etc.), size, byte/sector masks, warp mask. |
| 7 | **`mem_fetch_interface`** | Abstract push interface for memory requests (`full()`, `push()`). |
| 8 | **`mem_fetch_allocator`** | Factory for `mem_fetch` objects (3 overloaded `alloc()` methods). |
| 9 | **`memory_space_t`** | Type-safe memory-space tag: `global_space`, `shared_space`, `local_space`, `const_space`, `tex_space`, etc., with bank index. |
| 10 | **`gpgpu_functional_sim_config`** | PTX-level config: cuobjdump, PTXPlus conversion, forced capability, checkpoint/resume options, debug file. |
| 11 | **`gpgpu_t`** | Base GPU class: global/tex/surf memory spaces, `gpu_malloc`, `memcpy_to/from_gpu`, texture binding maps, `gpu_sim_cycle`/`gpu_tot_sim_cycle`. |
| 12 | **`gpgpu_ptx_sim_info`** | Kernel resource info: `lmem`, `smem`, `cmem`, `regs`, `maxthreads`, `ptx_version`, `sm_target`. |
| 13 | **`gpgpu_ptx_sim_arg`** | Single kernel argument: start pointer, byte count, offset. |
| 14 | **`core_t`** | Abstract SM core: holds SIMT stacks, thread info pointers, reduction storage, `execute_warp_inst_t()`, `updateSIMTStack()`. |
| 15 | **`register_set`** | Multi-slot pipeline register: `has_free()`, `has_ready()`, `move_in()`, `move_out_to()`. Supports sub-core model. |
| 16 | **`checkpoint`** | Checkpoint / resume utility for global memory state. |
| 17 | **`PowerscalingCoefficients`** | Per-operation-type power coefficients (int, fp, dp, tensor, tex, sqrt, etc.). |
| 18 | **`textureReferenceAttr`** | Texture binding metadata passed through `__cudaRegisterTexture()`. |
| 19 | **`dram_callback_t`** | Callback for DRAM access completion (function pointer + instruction + thread). |
| 20 | **`transaction_info`** (nested in `warp_inst_t`) | Per-transaction coalescing state: 32B chunk bitmask, byte mask, active thread mask. |

### From Other Files

| # | Class / Struct | File | Description |
|---|----------------|------|-------------|
| 21 | **`GPGPUsim_ctx`** | `gpgpusim_entrypoint.h` | Top-level sim context: semaphores, GPU config pointer, GPU object, stream manager, simulation flags. |
| 22 | **`CUevent_st`** | `stream_manager.h` | CUDA event: UID, blocking flag, update count, simulated cycle, wallclock. |
| 23 | **`stream_operation`** | `stream_manager.h` | Queued operation (memcpy variants, kernel launch, event, wait-event) with all required addresses/sizes. |
| 24 | **`CUstream_st`** | `stream_manager.h` | Per-stream FIFO of `stream_operation`s, mutex-protected, with pending flag. |
| 25 | **`stream_manager`** | `stream_manager.h` | Global manager: stream list, grid-to-stream map, `stream_zero`, round-robin `front()` selection, `operation()` dispatch. |
| 26 | **`OptionParser`** | `option_parser.cc` | Template `Register<T>()`, `ParseCommandLine()`, `ParseFile()`, `ParseString()`, `Print()`. |
| 27 | **`OptionRegistryInterface`** | `option_parser.cc` | Abstract option record: name, desc, `fromString()`, `toString()`, `isFlag()`. |
| 28 | **`OptionRegistry<T>`** | `option_parser.cc` | Templated concrete registry with `fromString()` specializations for `bool`, `char*`, `string`. |
| 29 | **`brk_pt`** | `debug.h` | Breakpoint/watchpoint: `fileline + thread_uid` or `address + value`. |
| 30 | **`Trace` namespace** | `trace.h` | `enabled`, `sampling_core`, `trace_streams_enabled[]`, `init()`. |

---

## 4. Key Enumerations

| Enum | Values (selected) | Used By |
|------|--------------------|---------|
| `_memory_space_t` | `global_space`, `shared_space`, `local_space`, `const_space`, `tex_space`, `param_space_kernel`, `param_space_local`, `generic_space` | `memory_space_t`, coalescing |
| `uarch_op_t` (`op_type`) | `ALU_OP`, `SFU_OP`, `TENSOR_CORE_OP`, `DP_OP`, `SP_OP`, `LOAD_OP`, `STORE_OP`, `BRANCH_OP`, `BARRIER_OP`, `CALL_OPS`, `RET_OPS`, `EXIT_OPS`, `SPECIALIZED_UNIT_*_OP` | `inst_t::op` |
| `special_operations_t` | `INT__OP`, `INT_MUL24_OP`, `FP_MUL_OP`, `FP_DIV_OP`, `FP_SQRT_OP`, `DP_MUL_OP`, `TENSOR__OP`, `TEX__OP` | Power model |
| `operation_pipeline_t` | `SP__OP`, `DP__OP`, `SFU__OP`, `TENSOR_CORE__OP`, `MEM__OP`, `SPECIALIZED__OP` | Pipeline routing |
| `mem_access_type` | `GLOBAL_ACC_R/W`, `LOCAL_ACC_R/W`, `CONST_ACC_R`, `TEXTURE_ACC_R`, `L1_WRBK_ACC`, `L2_WRBK_ACC`, `INST_ACC_R` | Cache/memory subsystem |
| `cache_operator_type` | `CACHE_ALL(.ca)`, `CACHE_LAST_USE(.lu)`, `CACHE_VOLATILE(.cv)`, `CACHE_L1(.nc)`, `CACHE_STREAMING(.cs)`, `CACHE_GLOBAL(.cg)`, `CACHE_WRITE_BACK(.wb)`, `CACHE_WRITE_THROUGH(.wt)` | Load/store cache hints |
| `stream_operation_type` | `stream_memcpy_host_to_device`, `stream_memcpy_device_to_host`, `stream_kernel_launch`, `stream_event`, `stream_wait_event` | Stream scheduling |
| `option_dtype` | `OPT_INT32`, `OPT_UINT32`, `OPT_INT64`, `OPT_UINT64`, `OPT_BOOL`, `OPT_FLOAT`, `OPT_DOUBLE`, `OPT_CHAR`, `OPT_CSTR` | Option parser |
| `divergence_support_t` | `POST_DOMINATOR` | SIMT reconvergence |
| `FuncCache` | `FuncCachePreferNone`, `FuncCachePreferShared`, `FuncCachePreferL1` | Cache config |
| `trace_streams_type` | `WARP_SCHEDULER`, `SCOREBOARD`, `MEMORY_PARTITION_UNIT`, `MEMORY_SUBPARTITION_UNIT`, `INTERCONNECT`, `LIVENESS` | Tracing subsystem |

---

## 5. Code Snippets

### 5.1 Concurrent Simulation Main Loop (`gpgpusim_entrypoint.cc`)

```cpp
void *gpgpu_sim_thread_concurrent(void *ctx_ptr) {
  gpgpu_context *ctx = (gpgpu_context *)ctx_ptr;
  atexit(termination_callback);
  do {
    // Spin until work appears
    while (ctx->the_gpgpusim->g_stream_manager->empty_protected() &&
           !ctx->the_gpgpusim->g_sim_done)
      ;
    ctx->the_gpgpusim->g_sim_active = true;
    ctx->the_gpgpusim->g_the_gpu->init();
    bool active = false;
    bool sim_cycles = false;
    do {
      // 1. Check if a kernel has completed; dispatch next op
      if (ctx->the_gpgpusim->g_stream_manager->operation(&sim_cycles) &&
          !ctx->the_gpgpusim->g_the_gpu->active())
        break;
      // 2. Functional simulation path
      if (ctx->the_gpgpusim->g_the_gpu->is_functional_sim()) { /*...*/ }
      // 3. Performance simulation: one GPU cycle
      if (ctx->the_gpgpusim->g_the_gpu->active()) {
        ctx->the_gpgpusim->g_the_gpu->cycle();
        sim_cycles = true;
        ctx->the_gpgpusim->g_the_gpu->deadlock_check();
      }
      active = ctx->the_gpgpusim->g_the_gpu->active() ||
               !(ctx->the_gpgpusim->g_stream_manager->empty_protected());
    } while (active && !ctx->the_gpgpusim->g_sim_done);
    // Print stats, release lock
    ctx->the_gpgpusim->g_sim_active = false;
  } while (!ctx->the_gpgpusim->g_sim_done);
}
```

### 5.2 Memory Coalescing (Fermi+) (`abstract_hardware_model.cc`)

```cpp
void warp_inst_t::memory_coalescing_arch(bool is_write,
                                         mem_access_type access_type) {
  // Segment sizes: 32B (sector) or 128B depending on arch & cache op
  bool sector_segment_size = (m_config->gpgpu_coalesce_arch >= 40); // Maxwell+
  unsigned segment_size = /*32, 64, or 128 based on data_size*/;

  for (unsigned subwarp = 0; subwarp < warp_parts; subwarp++) {
    std::map<new_addr_type, transaction_info> subwarp_transactions;
    // Step 1: gather per-thread addresses into transactions
    for (unsigned thread ...) {
      new_addr_type block_address = line_size_based_tag_func(addr, segment_size);
      transaction_info &info = subwarp_transactions[block_address];
      info.chunks.set(chunk);  info.active.set(thread);  info.bytes.set(idx+i);
    }
    // Step 2: reduce transaction sizes (128→64→32 if half unused)
    for (auto &t : subwarp_transactions)
      memory_coalescing_arch_reduce_and_send(is_write, access_type,
                                             t.second, t.first, segment_size);
  }
}
```

### 5.3 SIMT Stack Divergence Handling (`abstract_hardware_model.cc`)

```cpp
void simt_stack::update(simt_mask_t &thread_done, addr_vector_t &next_pc,
                        address_type recvg_pc, op_type next_inst_op, ...) {
  simt_mask_t top_active_mask = m_stack.back().m_active_mask;
  // Group threads by their next PC
  std::map<address_type, simt_mask_t> divergent_paths;
  while (top_active_mask.any()) {
    // Extract a group with same next_pc
    for (int i = m_warp_size - 1; i >= 0; i--) { /* partition */ }
    divergent_paths[tmp_next_pc] = tmp_active_mask;
  }
  // At most 2 divergent paths (branch taken / not-taken)
  assert(num_divergent_paths <= 2);
  // Push reconvergence entry, then divergent entries onto stack
  if (warp_diverged) {
    m_stack.back().m_pc = new_recvg_pc;      // reconvergence point
    m_stack.push_back(simt_stack_entry());    // taken path
  }
}
```

### 5.4 Stream Operation Dispatch (`stream_manager.cc`)

```cpp
bool stream_operation::do_operation(gpgpu_sim *gpu) {
  switch (m_type) {
    case stream_memcpy_host_to_device:
      gpu->memcpy_to_gpu(m_device_address_dst, m_host_address_src, m_cnt);
      m_stream->record_next_done();
      break;
    case stream_kernel_launch:
      if (gpu->can_start_kernel() && m_kernel->m_launch_latency == 0) {
        gpu->set_cache_config(m_kernel->name());
        gpu->launch(m_kernel);        // hand kernel to hardware scheduler
      } else {
        if (m_kernel->m_launch_latency) m_kernel->m_launch_latency--;
        return false;                 // not ready yet
      }
      break;
    case stream_event:
      m_event->update(gpu->gpu_tot_sim_cycle, wallclock);
      m_stream->record_next_done();
      break;
    case stream_wait_event:
      if (m_event->num_updates() >= m_cnt) m_stream->record_next_done();
      else return false;              // keep waiting
      break;
  }
  m_done = true;
  return true;
}
```

### 5.5 Option Parser Registration Pattern (`abstract_hardware_model.cc`)

```cpp
void gpgpu_functional_sim_config::reg_options(class OptionParser *opp) {
  option_parser_register(opp, "-gpgpu_ptx_use_cuobjdump", OPT_BOOL,
                         &m_ptx_use_cuobjdump,
                         "Use cuobjdump to extract ptx and sass from binaries",
                         "1");
  option_parser_register(opp, "-gpgpu_ptx_force_max_capability", OPT_UINT32,
                         &m_ptx_force_max_capability,
                         "Force maximum compute capability", "0");
  option_parser_register(opp, "-gpgpu_ptx_convert_to_ptxplus", OPT_BOOL,
                         &m_ptx_convert_to_ptxplus,
                         "Convert SASS to ptxplus and run ptxplus", "0");
  // ... 15+ more options
}
```

---

## 6. Data Flow

### 6.1 Kernel Launch → Simulation Cycle

```
Application calls cudaLaunch()
  → libcuda creates kernel_info_t (grid/block dims, function_info*, streamID)
  → stream_manager::push(stream_operation(kernel, sim_mode, stream))
  → enqueued into CUstream_st::m_operations

Simulation thread (gpgpu_sim_thread_concurrent):
  → stream_manager::operation() → stream_manager::front()
      → round-robin across streams, picks next non-busy, non-empty stream
      → stream_operation::do_operation() → gpu->launch(kernel)
  → gpgpu_sim::cycle()            // one clock tick
      → shader cores fetch/decode/execute warp_inst_t
      → warp_inst_t::generate_mem_accesses() → memory coalescing
      → mem_access_t pushed to interconnect
  → gpgpu_sim::deadlock_check()
  → when kernel done: stream_manager::register_finished_kernel()
      → CUstream_st::record_next_done() → pops operation
```

### 6.2 Configuration Loading

```
gpgpu_ptx_sim_init_perf()
  → option_parser_create()                  // new OptionParser
  → ptx_reg_options(opp)                    // PTX-level options
  → func_sim->ptx_opcocde_latency_options() // instruction latencies
  → icnt_reg_options(opp)                   // interconnect options
  → gpgpu_sim_config::reg_options(opp)      // all GPU microarch options
  → option_parser_cmdline(opp, argc=3, argv=["","-config","gpgpusim.config"])
      → OptionParser::ParseCommandLine()
          → encounters "-config" → ParseFile("gpgpusim.config")
              → strips comments (#), tokenizes, calls ParseCommandLine again
  → option_parser_print(opp, stdout)        // dump all resolved values
  → gpgpu_sim_config::init()                // validate and derive config
```

### 6.3 Memory Access Coalescing

```
warp_inst_t::generate_mem_accesses()
  → Classify by memory_space_t
  │
  ├─ shared_space:
  │   → Count bank conflicts per subwarp (WORD_SIZE=4B banks)
  │   → cycles = max bank conflicts (models serialization)
  │
  ├─ tex_space / const_space:
  │   → Group thread addresses by cache-line-sized blocks
  │   → One mem_access_t per unique block address
  │
  └─ global_space / local_space:
      → memory_coalescing_arch():
          for each subwarp (warp_parts):
            Step 1: Map thread addresses → segment-aligned block addresses
                    Record which 32B chunk & byte within 128B accessed
            Step 2: Reduce (128B→64B→32B if half unused)
            Step 3: Push one mem_access_t per reduced transaction
```

---

## 7. Configuration Knobs (20+)

### From `gpgpu_functional_sim_config::reg_options()`

| Knob | Type | Default | Description |
|------|------|---------|-------------|
| `-gpgpu_ptx_use_cuobjdump` | BOOL | 1 | Use cuobjdump for PTX/SASS extraction |
| `-gpgpu_experimental_lib_support` | BOOL | 0 | Try extracting code from CUDA libraries |
| `-gpgpu_ptx_convert_to_ptxplus` | BOOL | 0 | Convert SASS to PTXPlus |
| `-gpgpu_ptx_force_max_capability` | UINT32 | 0 | Force compute capability |
| `-gpgpu_ptx_inst_debug_to_file` | BOOL | 0 | Dump instruction debug to file |
| `-gpgpu_ptx_inst_debug_file` | CSTR | `inst_debug.txt` | Debug output filename |
| `-gpgpu_ptx_inst_debug_thread_uid` | INT32 | 1 | Thread UID for debug output |
| `-checkpoint_option` | INT32 | 0 | Enable checkpointing (0=off) |
| `-checkpoint_kernel` | INT32 | 1 | Checkpoint during which kernel |
| `-checkpoint_CTA` | INT32 | 0 | Checkpoint after N CTAs |
| `-resume_option` | INT32 | 0 | Enable resume (0=off) |
| `-resume_kernel` | INT32 | 0 | Resume from which kernel |
| `-resume_CTA` | INT32 | 0 | Resume from which CTA |
| `-checkpoint_CTA_t` | INT32 | 0 | Checkpoint CTA threshold |
| `-checkpoint_insn_Y` | INT32 | 0 | Instruction-based checkpoint |

### From `core_config` (set via `gpgpu_sim_config`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `warp_size` | unsigned | Threads per warp (typically 32) |
| `gpgpu_coalesce_arch` | int | Coalescing architecture (13=GT200, 20=Fermi, 40=Maxwell+) |
| `num_shmem_bank` | unsigned | Shared memory banks (default 16) |
| `shmem_limited_broadcast` | bool | Limited broadcast mode |
| `mem_warp_parts` | unsigned | Warp partitions for memory |
| `gpgpu_shmem_size` | unsigned | Shared memory per SM |
| `gpgpu_cache_texl1_linesize` | unsigned | Texture L1 cache line size |
| `gpgpu_cache_constl1_linesize` | unsigned | Constant L1 cache line size |
| `gpgpu_max_insn_issue_per_warp` | unsigned | Max issues per warp per cycle |
| `gmem_skip_L1D` | bool | Global memory bypasses L1 |
| `adaptive_cache_config` | bool | Enable adaptive cache config |
| `mem_unit_ports` | unsigned | Memory unit ports |

### Implicit Config / Environment

| Variable | Description |
|----------|-------------|
| `gpgpusim.config` | Main config file (hardcoded in `sg_argv`) |
| `g_debug_execution` | Debug verbosity level (global) |
| `g_cuda_launch_blocking` | Force blocking kernel launches |
| `PTX_SIM_MODE_FUNC` | Environment variable: 1=functional, 0=performance |

---

## 8. Interactions Between Files

```
                    ┌─────────────────────────────┐
                    │   libcuda / libopencl        │
                    │  (CUDA/OpenCL runtime API)   │
                    └──────────┬──────────────────┘
                               │ creates kernel_info_t
                               │ calls stream_manager::push()
                               ▼
┌──────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│ option_parser.h  │◄───│ gpgpusim_        │───►│  stream_manager.h │
│ option_parser.cc │    │ entrypoint.h/.cc │    │  stream_manager.cc│
│                  │    │                  │    │                   │
│ • Parses config  │    │ • Creates GPU    │    │ • Queues ops      │
│ • All -gpgpu_*   │    │ • Sim threads    │    │ • Round-robin     │
│   knobs          │    │ • Synchronize    │    │   dispatch        │
└──────────────────┘    └────────┬─────────┘    └────────┬──────────┘
                                 │                       │
                                 ▼                       ▼
                    ┌──────────────────────────────────────────┐
                    │       abstract_hardware_model.h/.cc       │
                    │                                          │
                    │  kernel_info_t  ←──── stream_operation    │
                    │  warp_inst_t    ←──── core_t::execute()  │
                    │  mem_access_t   ←──── coalescing logic   │
                    │  simt_stack     ←──── core_t::update()   │
                    │  gpgpu_t        ←──── memory subsystem   │
                    │  core_config    ←──── option_parser       │
                    └──────────────────────────┬───────────────┘
                                               │
                          ┌────────────────────┼────────────────┐
                          ▼                    ▼                ▼
                    ┌──────────┐      ┌──────────────┐   ┌──────────┐
                    │ debug.h  │      │   trace.h    │   │statwrap  │
                    │ debug.cc │      │   trace.cc   │   │  per.h   │
                    │          │      │              │   │          │
                    │ PTX DBG  │      │ DPRINTF()    │   │ Stats    │
                    │ watchpts │      │ per-subsys   │   │ histos   │
                    └──────────┘      └──────────────┘   └──────────┘
```

**Key interaction chains:**

1. **Config → Everything**: `option_parser` feeds into `core_config`, `gpgpu_functional_sim_config`, `gpgpu_sim_config`.
2. **Entrypoint → GPU object**: `gpgpu_ptx_sim_init_perf()` creates `gpgpu_sim_config` → `exec_gpgpu_sim` / `sst_gpgpu_sim`.
3. **Stream → GPU**: `stream_manager::operation()` calls `stream_operation::do_operation()` which calls `gpu->launch()` / `gpu->memcpy_to_gpu()`.
4. **abstract_hardware_model → cuda-sim**: `core_t::execute_warp_inst_t()` calls `ptx_thread_info::ptx_exec_inst()`.
5. **abstract_hardware_model → gpgpu-sim**: `warp_inst_t` flows through pipeline stages in `shader_core_ctx`.
6. **Trace → Shader/Memory**: `DPRINTF(WARP_SCHEDULER, ...)` used inside timing model classes.
7. **Debug → Shader**: `gpgpu_sim::gpgpu_debug()` reads from `m_global_mem`, `m_sc[]`.

---

## 9. Algorithms

### 9.1 PDOM-Based SIMT Reconvergence (simt_stack::update)

The post-dominator reconvergence algorithm from MICRO'07:

1. **Partition** active threads by their `next_pc` into at most 2 groups (taken / not-taken).
2. **If divergent** (2 groups):
   - Set top-of-stack entry's PC to the reconvergence PC (post-dominator).
   - Push a new entry for the taken path.
   - The not-taken path remains on the stack below reconvergence.
3. **On reconvergence**: when both paths reach `recvg_pc`, entries merge.
4. **CALL/RET handling**: CALL pushes `STACK_ENTRY_TYPE_CALL`; RET pops it and restores the caller's PC.

### 9.2 Memory Coalescing (warp_inst_t::memory_coalescing_arch)

Models NVIDIA's memory coalescing from Fermi onward:

1. **Segment selection**: Choose segment size (32B sector or 128B/64B line) based on `gpgpu_coalesce_arch` and `data_size`.
2. **Transaction gathering**: For each subwarp, map thread addresses to aligned segments; record which 32B chunks and bytes are accessed.
3. **Transaction reduction** (`memory_coalescing_arch_reduce_and_send`):
   - 128B → 64B if only upper or lower half used.
   - 64B → 32B if only one 32B half used.
4. **Atomics**: Use per-transaction conflict detection (`test_bytes`) to split conflicting atomics into separate transactions.

### 9.3 Shared Memory Bank Conflict Counting

1. For each subwarp, compute `bank_accs[bank][word_address] → count`.
2. **Limited broadcast**: If one word is accessed by multiple threads in the same bank, count it once (broadcast).
3. **Default**: Count distinct words per bank; max across banks = number of serialized accesses.
4. `cycles = total_accesses` (models serialization as increased initiation interval).

### 9.4 Stream Round-Robin Scheduling (stream_manager::front)

1. Try `m_stream_zero` first (default stream / blocking mode).
2. If stream zero is empty or busy, iterate from `m_last_stream` through all named streams.
3. Pick the first non-busy, non-empty stream; record its position for next round.
4. For kernel launches, record `grid_uid → stream` mapping for completion tracking.

### 9.5 Option Parsing Strategy

1. `ParseCommandLine()` iterates argv; `-config <file>` triggers `ParseFile()`.
2. `ParseFile()` strips `#` comments, concatenates lines, feeds to `ParseStringStream()`.
3. `ParseStringStream()` tokenizes on whitespace, handles quoted strings, calls `ParseCommandLine()` recursively.
4. Template specializations handle `bool` (0/1), `char*` (NULL default), `string` types.

---

## 10. Constants and Limits

| Constant | Value | Meaning |
|----------|-------|---------|
| `MAX_CTA_PER_SHADER` | 32 | Max concurrent CTAs per SM |
| `MAX_BARRIERS_PER_CTA` | 16 | Max barriers per CTA |
| `MAX_INPUT_VALUES` | 24 | Max input operands per instruction |
| `MAX_OUTPUT_VALUES` | 8 | Max output operands per instruction |
| `MAX_WARP_SIZE` | 32 | Maximum warp size |
| `MAX_REG_OPERANDS` | 32 | Max register operands |
| `MAX_MEMORY_ACCESS_SIZE` | 128 | Bytes; for byte mask bitset |
| `SECTOR_CHUNCK_SIZE` | 4 | Number of sectors per cache line |
| `SECTOR_SIZE` | 32 | Bytes per sector |
| `MAX_ACCESSES_PER_INSN_PER_THREAD` | 8 | Max memory accesses per thread per instruction |
| `SPECIALIZED_UNIT_NUM` | 8 | Number of specialized execution units |
| `GLOBAL_HEAP_START` | 0xC0000000 | Start address for GPU malloc |
| `SHARED_MEM_SIZE_MAX` | 96 KB | Volta max shared memory |
| `LOCAL_MEM_SIZE_MAX` | 16 KB | Volta max local memory per thread |
| `MAX_STREAMING_MULTIPROCESSORS` | 80 | Volta Titan V SM count |
| `MAX_THREAD_PER_SM` | 2048 | Max threads per SM |
| `MAX_WARP_PER_SM` | 64 | Max warps per SM |

---

## 11. Terminology Glossary (25+)

| Term | Definition |
|------|-----------|
| **CTA** | Cooperative Thread Array — CUDA thread block; group of threads sharing shared memory and synchronization barriers. |
| **Warp** | Group of 32 threads executing in lockstep (SIMD). The fundamental scheduling unit. |
| **SIMT** | Single Instruction, Multiple Threads — NVIDIA's execution model allowing threads in a warp to diverge. |
| **PDOM** | Post-Dominator — the reconvergence point where divergent branches must rejoin. Used by `simt_stack`. |
| **PTX** | Parallel Thread Execution — NVIDIA's virtual ISA, input to the simulator's functional model. |
| **PTXPlus** | Extended PTX that preserves SASS-level scheduling; enables native ISA simulation. |
| **SASS** | Shader Assembly — NVIDIA's native GPU instruction set. |
| **Coalescing** | Combining per-thread memory requests in a warp into fewer, wider transactions. |
| **Sector** | A 32-byte portion of a cache line; used in Maxwell+ architectures. |
| **SM** | Streaming Multiprocessor — the GPU compute core containing warp schedulers, execution units, caches. |
| **Grid** | Collection of CTAs forming a kernel launch, dimensioned by `gridDim`. |
| **Block** | Synonym for CTA; dimensioned by `blockDim`. |
| **Stream** | CUDA stream — ordered sequence of operations (memcpy, kernel, event) that execute in order within the stream. |
| **Event** | Synchronization marker recorded in a stream; can be waited on from other streams. |
| **kernel_info_t** | Simulator's representation of a launched kernel, tracking CTA iteration, running core count, parent/child relationships. |
| **warp_inst_t** | A decoded instruction bound to a specific warp, carrying per-thread state and memory access info. |
| **mem_access_t** | A single coalesced memory transaction generated from a warp instruction. |
| **mem_fetch** | A memory request packet traveling through the cache/interconnect hierarchy. |
| **Active Mask** | 32-bit mask indicating which threads in a warp are active for an instruction. |
| **Reconvergence PC** | The PC where divergent threads rejoin; computed by PDOM analysis. |
| **Register Set** | Pipeline register holding warp instructions between stages (e.g., ID→EX). |
| **Functional Simulation** | Executes PTX instructions for correctness; no timing. |
| **Performance Simulation** | Cycle-accurate timing model of the GPU microarchitecture. |
| **CDP** | CUDA Dynamic Parallelism — launching kernels from within GPU kernels. Tracked via parent/child `kernel_info_t`. |
| **Deadlock Check** | Periodic check that the GPU is making forward progress (not stalled forever). |
| **Initiation Interval** | Number of cycles between successive issues of the same instruction type to a pipeline. |
| **Launch Latency** | Simulated cycles for CPU→GPU kernel transfer; modeled by `m_launch_latency`. |
| **BookSim** | Academic interconnection network simulator; used for on-chip network and wrapped by `statwrapper`. |
| **SST** | Structural Simulation Toolkit — external simulator that can drive GPGPU-Sim cycle-by-cycle via `SST_Cycle()`. |
| **Checkpoint** | Dump/restore of global memory state for long-running simulations. |
| **cuobjdump** | NVIDIA tool to extract PTX and SASS from compiled CUDA binaries. |
