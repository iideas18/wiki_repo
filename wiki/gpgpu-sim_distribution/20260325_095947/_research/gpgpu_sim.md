# gpgpu-sim Module — Research Report

> **Module path:** `src/gpgpu-sim/`
> **Generated:** 2026-03-25

---

## 1. Purpose

The `gpgpu-sim` module is the **performance-simulation core** of GPGPU-Sim. It models a complete NVIDIA-style GPU micro-architecture at the cycle level, including shader-core pipelines, an L1/L2 cache hierarchy, on-chip interconnect, DRAM controllers with DDR timing, and address decoding. Its role is to accept CUDA kernel launches, distribute Cooperative Thread Arrays (CTAs) to shader cores, and advance every modeled hardware component each cycle, collecting detailed performance and power statistics for architectural research.

---

## 2. Key Classes

| # | Class | File | Role |
|---|-------|------|------|
| 1 | `gpgpu_sim` | gpu-sim.h | Top-level GPU simulator; owns clusters, memory partitions, and the main `cycle()` loop |
| 2 | `shader_core_ctx` | shader.h | Single shader/SM core: fetch → decode → issue → execute → writeback pipeline |
| 3 | `simt_core_cluster` | shader.h | Cluster of shader cores sharing an interconnect injection port |
| 4 | `shd_warp_t` | shader.h | Per-warp state: PC, active-thread mask, instruction buffer, barriers |
| 5 | `scheduler_unit` | shader.h | Abstract warp scheduler (LRR, GTO, RRR, Two-Level, SWL sub-classes) |
| 6 | `ldst_unit` | shader.h | Load/store functional unit managing L1D/L1C/L1T caches and memory requests |
| 7 | `Scoreboard` | scoreboard.h | Per-warp register-dependency tracker preventing RAW hazards at issue |
| 8 | `opndcoll_rfu_t` | shader.h | Operand-collector / register-file-unit with crossbar arbiter |
| 9 | `baseline_cache` / `data_cache` / `l1_cache` / `l2_cache` | gpu-cache.h | Configurable set-associative cache hierarchy (tag array + MSHR + bandwidth model) |
| 10 | `tag_array` | gpu-cache.h | Set-associative tag store with LRU/FIFO replacement and sector support |
| 11 | `mshr_table` | gpu-cache.h | Miss-Status Holding Registers — merges concurrent misses to the same block |
| 12 | `memory_partition_unit` | l2cache.h | One per DRAM channel; houses sub-partitions (L2 slices) and a DRAM controller |
| 13 | `memory_sub_partition` | l2cache.h | Single L2 slice with four FIFO queues (icnt↔L2, L2↔DRAM) |
| 14 | `dram_t` | dram.h | DDR DRAM controller: banks, bank-groups, timing constraints, command scheduling |
| 15 | `frfcfs_scheduler` | dram_sched.h | First-Ready First-Come-First-Served DRAM request scheduler with read/write modes |
| 16 | `mem_fetch` | mem_fetch.h | Memory-request envelope carrying address, access type, timestamps, and status through the hierarchy |
| 17 | `linear_to_raw_address_translation` | addrdec.h | Address decoder mapping linear addresses to (chip, bank, row, col, burst, sub-partition) |
| 18 | `xbar_router` / `LocalInterconnect` | local_interconnect.h | Crossbar interconnect with Round-Robin or iSLIP arbitration |

---

## 3. Representative Snippets

### 3.1 Main simulator class (`gpu-sim.h`)

```cpp
class gpgpu_sim : public gpgpu_t {
 public:
  gpgpu_sim(const gpgpu_sim_config &config, gpgpu_context *ctx);
  void launch(kernel_info_t *kinfo);
  bool can_start_kernel();
  unsigned finished_kernel();
  void set_kernel_done(kernel_info_t *kernel);
  void init();
  void cycle();          // advance every component by one clock tick
  bool active();
  bool cycle_insn_cta_max_hit();
  void deadlock_check();
  // ...
};
```

### 3.2 Scoreboard — register-dependency tracking (`scoreboard.h`)

```cpp
class Scoreboard {
 public:
  Scoreboard(unsigned sid, unsigned n_warps, class gpgpu_t *gpu);
  void reserveRegisters(const warp_inst_t *inst);
  void releaseRegisters(const warp_inst_t *inst);
  void releaseRegister(unsigned wid, unsigned regnum);
  bool checkCollision(unsigned wid, const inst_t *inst) const;
  bool pendingWrites(unsigned wid) const;
 private:
  std::vector<std::set<unsigned>> reg_table;   // warp → pending-write registers
  std::vector<std::set<unsigned>> longopregs;  // long-latency (mem) registers
};
```

### 3.3 DRAM controller constructor & interface (`dram.h`)

```cpp
class dram_t {
 public:
  dram_t(unsigned int partition_id, const memory_config *config,
         class memory_stats_t *stats, class memory_partition_unit *mp,
         class gpgpu_sim *gpu);
  bool full(bool is_write) const;
  void push(class mem_fetch *data);
  void cycle();
  class mem_fetch *return_queue_pop();
  class mem_fetch *return_queue_top();
 private:
  void scheduler_fifo();
  void scheduler_frfcfs();
  bool issue_col_command(int j);
  bool issue_row_command(int j);
  bank_t **bk;
  frfcfs_scheduler *m_frfcfs_scheduler;
  fifo_pipeline<dram_req_t> *rwq, *mrqq;
  fifo_pipeline<mem_fetch>  *returnq;
};
```

### 3.4 FR-FCFS scheduler (`dram_sched.h`)

```cpp
class frfcfs_scheduler {
 public:
  frfcfs_scheduler(const memory_config *config, dram_t *dm, memory_stats_t *stats);
  void add_req(dram_req_t *req);
  dram_req_t *schedule(unsigned bank, unsigned curr_row);
  unsigned num_pending() const;
 private:
  std::list<dram_req_t *> *m_queue;           // per-bank request list
  std::map<unsigned, std::list<...>> *m_bins;  // requests binned by row
  enum memory_mode m_mode;                     // READ_MODE / WRITE_MODE
};
```

### 3.5 Cache access result enum (`gpu-cache.h`)

```cpp
enum cache_request_status {
  HIT = 0, HIT_RESERVED, MISS, RESERVATION_FAIL, SECTOR_MISS, MSHR_HIT,
  NUM_CACHE_REQUEST_STATUS
};

enum cache_block_state { INVALID = 0, RESERVED, VALID, MODIFIED };
```

---

## 4. Data Flow

### 4.1 Overall cycle-level pipeline

```
┌───────────────┐   icnt_push()   ┌───────────────┐   push()   ┌──────────────┐
│  Shader Core  │ ──────────────► │  Interconnect  │ ────────► │  L2 Sub-Part │
│  (ldst_unit)  │                 │  (xbar/booksim)│           │  (L2 cache)  │
└───────┬───────┘   icnt_pop()    └───────────────┘           └──────┬───────┘
        ▲           ◄──────────────────────────────────────────────── │ (hit reply)
        │                                                             │ (miss)
        │                                                     ┌──────▼───────┐
        │                                                     │  DRAM Latency │
        │          return_queue_pop()  ┌───────────────┐      │    Queue      │
        └─────────────────────────────│  DRAM Ctrl     │◄─────┘              │
                                      │  (dram_t)      │  dram_cycle()       │
                                      │  FR-FCFS sched │──────────────────────┘
                                      └───────────────┘
```

### 4.2 `mem_fetch` status progression (FSM)

```
MEM_FETCH_INITIALIZED
  → IN_L1D_MISS_QUEUE  (or L1I/L1T/L1C)
  → IN_ICNT_TO_MEM
  → IN_PARTITION_ROP_DELAY
  → IN_PARTITION_ICNT_TO_L2_QUEUE
  → (L2 HIT) → IN_PARTITION_L2_TO_ICNT_QUEUE
  → (L2 MISS) → IN_PARTITION_L2_TO_DRAM_QUEUE
  → IN_PARTITION_DRAM_LATENCY_QUEUE
  → IN_PARTITION_MC_INPUT_QUEUE
  → IN_PARTITION_MC_BANK_ARB_QUEUE
  → IN_PARTITION_DRAM
  → IN_PARTITION_MC_RETURNQ
  → IN_PARTITION_DRAM_TO_L2_QUEUE
  → IN_PARTITION_L2_FILL_QUEUE
  → IN_PARTITION_L2_TO_ICNT_QUEUE
  → IN_ICNT_TO_SHADER
  → IN_CLUSTER_TO_SHADER_QUEUE
  → IN_SHADER_LDST_RESPONSE_FIFO
  → IN_SHADER_FETCHED
  → MEM_FETCH_DELETED
```

### 4.3 Clock domains

`gpgpu_sim::cycle()` runs four independent clock domains per tick. The smallest-period domain fires first:

| Domain | Default | Mask | What runs |
|--------|---------|------|-----------|
| CORE | 500 MHz | 0x01 | Shader clusters, CTA issue, power |
| ICNT | 2 GHz | 0x08 | Interconnect transfer, shader←→mem response routing |
| L2 | 2 GHz | 0x02 | L2 cache cycles, icnt→mem pushes |
| DRAM | 2 GHz | 0x04 | DRAM controller scheduling & timing |

### 4.4 CTA distribution

1. `gpgpu_sim::launch(kernel_info_t*)` — kernel enqueued in `m_running_kernels[]`
2. `issue_block2core()` — round-robin across clusters via `m_last_cluster_issue`
3. `shader_core_ctx::issue_block2core()` — allocates threads, warps, shared memory, barriers, initialises SIMT stacks

---

## 5. Config / Knobs

| Parameter | Default | Controls |
|-----------|---------|----------|
| `gpgpu_n_clusters` | 10 | Number of SIMT core clusters |
| `gpgpu_n_cores_per_cluster` | 3 | Shader cores per cluster |
| `gpgpu_shader_core_pipeline` | `"1024:32"` | Threads-per-core : warp-size |
| `gpgpu_shader_registers` | 8192 | Architectural registers per core |
| `gpgpu_shmem_size` | 16384 | Shared memory bytes per core |
| `gpgpu_scheduler` | `"gto"` | Warp scheduler type (lrr/gto/rrr/two_level/warp_limiting/oldest) |
| `gpgpu_num_sched_per_core` | 1 | Scheduler units per core |
| `gpgpu_cache:dl2` | `"64:128:8,L:B:m:N,A:16:4,4"` | L2 config — sets:line_sz:assoc, replacement:write:alloc:walloc, mshr:entries:merge, miss_q |
| `gpgpu_dram_scheduler` | 1 | 0 = FIFO, 1 = FR-FCFS |
| `gpgpu_dram_timing_opt` | `"nbk:tCCD:tRRD:tRCD:tRAS:tRP:tRC:CL:WL:tCDLR:tWR:nbkgrp:tCCDL:tRTPL"` | DDR timing parameter string |
| `gpgpu_dram_buswidth` | 4 | DRAM bus width (bytes) |
| `gpgpu_dram_burst_length` | 4 | Burst length in cycles |
| `seperate_write_queue_enable` | 0 | Split read/write DRAM queues (enables watermark mode-switching) |
| `write_high_watermark` | — | Pending writes threshold to switch READ→WRITE mode |
| `write_low_watermark` | — | Pending writes threshold to switch WRITE→READ mode |
| `gpgpu_frfcfs_dram_sched_queue_size` | 0 (unlimited) | FR-FCFS request queue limit per bank |
| `gpgpu_dram_return_queue_size` | 0 (unlimited) | DRAM return queue limit |
| `gpgpu_flush_l1_cache` | 0 | Flush L1 after each kernel |
| `gpgpu_flush_l2_cache` | 0 | Flush L2 after each kernel |
| `gpu_deadlock_detect` | 1 | Enable deadlock detection (every 50 K cycles) |
| `max_concurrent_kernel` | 32 | Max kernels executing simultaneously |
| `gpgpu_memlatency_stat` | 0 | Bitfield enabling memory-latency stats |
| `network_mode` | 1 | 1 = BookSim (INTERSIM), 2 = Local crossbar (LOCAL_XBAR) |
| `dram_bnk_indexing_policy` | 0 | 0 = LINEAR, 1 = BITWISE_XOR, 2 = IPOLY, 3 = CUSTOM |

---

## 6. Interactions

| Peer module | Direction | Mechanism |
|-------------|-----------|-----------|
| `abstract_hardware_model` (PTX/SASS front-end) | ← kernels, thread state | `kernel_info_t`, `warp_inst_t`, `mem_access_t` |
| `intersim2` / BookSim (NoC) | ↔ packets | Function-pointer table `icnt_push/icnt_pop` in `icnt_wrapper.h` |
| `cuda-sim` (functional simulator) | ← functional execution | `func_exec_inst()` called from `issue_warp()` |
| Power model (AccelWattch / McPAT) | → stats | `mcpat_cycle()` called every CORE tick; `power_config` struct |
| SST / Balar co-simulation | ↔ memory | `sst_gpgpu_sim`, `sst_simt_core_cluster`, `sst_memory_interface` |
| `stream_manager` | ← kernel dispatch | `launch()` API receiving `kernel_info_t` |
| Trace/visualizer subsystem | → events | `g_visualizer_enabled`, `shader_trace.h`, `l2cache_trace.h` |

---

## 7. Terminology

| Term | Meaning |
|------|---------|
| **CTA** | Cooperative Thread Array — a.k.a. thread block; the unit of work distributed to a core |
| **Warp** | Group of threads (typically 32) executing in SIMT lock-step |
| **SIMT Stack** | Stack tracking thread divergence/reconvergence at branch points |
| **SM / Shader Core** | Streaming Multi-processor — one pipeline instance (`shader_core_ctx`) |
| **Cluster** | Group of SMs sharing an interconnect port (`simt_core_cluster`) |
| **MSHR** | Miss-Status Holding Register — tracks pending cache misses and merges requests |
| **Scoreboard** | Per-warp set of registers with pending writes; used to detect RAW hazards |
| **Operand Collector** | Hardware unit that reads source operands from banked register files before execution |
| **FR-FCFS** | First-Ready First-Come-First-Served — DRAM scheduling that prioritises row-buffer hits |
| **Bank / Bank Group** | DRAM organisational units; bank groups have tighter CAS-to-CAS timing (tCCDL) |
| **Row Buffer** | Sense-amp row in a DRAM bank; an open row allows column commands without re-activation |
| **Sector Cache** | Cache where a line is divided into sectors; individual sectors can be valid/invalid independently |
| **ROP** | Raster Operations Pipeline — introduces a fixed delay for memory requests before L2 |
| **mem_fetch** | Envelope object that tracks a single memory request through all hierarchy stages |
| **Flit** | Flow-control unit on the interconnect; a mem_fetch may span multiple flits |
| **Watermark** | Threshold on pending writes that triggers READ↔WRITE mode switching in the DRAM scheduler |
| **Sub-partition** | One L2 cache slice within a memory partition; multiple sub-partitions share one DRAM channel |
| **Pipeline Register** | Array slot between two pipeline stages holding a `warp_inst_t` in flight |
| **Instruction Buffer (ibuffer)** | 2-entry FIFO per warp holding decoded instructions before issue |

---

## 8. Algorithms & Mechanisms

### 8.1 FR-FCFS DRAM Scheduling (`dram_sched.cc`)

The FR-FCFS scheduler prioritises **row-buffer hits** (First-Ready) over older requests to different rows (FCFS). Requests are binned per-bank into per-row lists (`m_bins[bank][row]`). When `schedule(bank, curr_row)` is called, it first checks if the current row's bin has pending requests; if so it returns the front entry (back-to-back row-hit service). When that row's list is exhausted, it falls through to the oldest waiting request's row. An optional separate write queue with READ/WRITE mode switching is controlled by high/low watermarks: when pending writes exceed `write_high_watermark` the scheduler switches to WRITE_MODE, draining writes until the count drops below `write_low_watermark`.

### 8.2 Cache Tag Probe & Replacement (`gpu-cache.cc`)

The `tag_array::probe()` function implements a fully-associative search within the target set. For each way it compares the stored tag and checks sector-mask validity, returning HIT, HIT_RESERVED, SECTOR_MISS, or MISS. If no match is found, it selects a victim: invalid lines are preferred; among valid lines, **LRU** picks the line with the oldest `last_access_time` and **FIFO** picks the oldest allocation time (differs from LRU in that hits do not update the timestamp). If every line in the set is RESERVED (outstanding fill), `RESERVATION_FAIL` is returned to prevent deadlock. Eviction of modified lines generates a write-back `mem_fetch` to the next level.

### 8.3 Shader Core Pipeline & Warp Scheduling (`shader.cc`)

Each `shader_core_ctx` executes a **5-stage pipeline in reverse order** each cycle: writeback → execute → issue → decode → fetch. The **fetch** stage round-robins across warps looking for an empty instruction buffer and a valid L1I cache line. The **issue** stage iterates scheduler units (GTO, LRR, etc.); each scheduler sorts its supervised warps by priority, checks the scoreboard for RAW hazards (`checkCollision`), and issues up to one instruction per cycle into the appropriate functional-unit pipeline register. **GTO** (Greedy-Then-Oldest) sticks with the last-issued warp until it stalls, then falls back to the oldest ready warp — this favours memory-level parallelism by keeping one warp's requests in-flight.

### 8.4 Address Decoding & Partition Mapping (`addrdec.cc`)

`linear_to_raw_address_translation::addrdec_tlx()` maps a 64-bit linear address to the tuple `(chip, bank, row, column, burst, sub_partition)` using configurable bit-field masks. Multiple partition-indexing functions are supported: `CONSECUTIVE` (simple modulo), `BITWISE_PERMUTATION` (XOR-based), `IPOLY` (irreducible polynomial hashing), and `CUSTOM`. The choice of indexing function determines how memory traffic is distributed across channels; poor choices can cause hot-spotting. A `sweep_test()` validates that the configured masks cover the entire address space without aliasing.

---

## 9. State Machines

### 9.1 DRAM Bank State Machine (`dram.cc`)

```
        issue_row_command (ACTIVATE)
  IDLE ─────────────────────────────► ACTIVE
   ▲   guards: !RRDc, !RPc, !RCc      │
   │                                    │ issue_col_command (READ/WRITE)
   │                                    │ while curr_row matches
   │   issue_row_command (PRECHARGE)    │
   └────────────────────────────────────┘
        guards: !RASc, !WTPc, !RTPc
        (triggered when new row needed)
```

- **IDLE (`'I'`)**: Bank row buffer closed. Accepts ACTIVATE if global `RRDc` and per-bank `RPc`, `RCc` counters are zero.
- **ACTIVE (`'A'`)**: Row open. Column READ/WRITE commands issued when `CCDc=0`, `RCDc=0` (or `RCDWRc`), row matches, and `rwq` not full. When a new row is needed, PRECHARGE returns bank to IDLE after `tRP` cycles.

### 9.2 DRAM Read/Write Mode Machine (`dram_sched.cc`)

```
              write_pending ≥ high_watermark
  READ_MODE ──────────────────────────────► WRITE_MODE
       ◄──────────────────────────────────
              write_pending < low_watermark
```

Hysteresis prevents thrashing between modes. In WRITE_MODE the scheduler drains the write queue; in READ_MODE it services reads.

### 9.3 Cache Block State Machine (`gpu-cache.h / gpu-cache.cc`)

```
  INVALID ──(allocate on miss)──► RESERVED ──(fill arrives)──► VALID
                                                                 │
                                                     (write hit, WB policy)
                                                                 ▼
                                                              MODIFIED
                                                                 │
                                                     (eviction / flush)
                                                                 ▼
                                                              INVALID
```

- **INVALID**: Line not present.
- **RESERVED**: Miss outstanding; MSHR allocated; further accesses see `HIT_RESERVED`.
- **VALID**: Clean data present.
- **MODIFIED**: Dirty — requires write-back on eviction.

### 9.4 `mem_fetch` Status FSM (`mem_fetch_status.tup`)

A `mem_fetch` object carries an `enum mem_fetch_status` that is updated via `set_status()` as it traverses the hierarchy (see §4.2 for the full state list with 26 states from `MEM_FETCH_INITIALIZED` through `MEM_FETCH_DELETED`). Key transitions:

- `IN_L1D_MISS_QUEUE → IN_ICNT_TO_MEM` — L1 miss injected into interconnect
- `IN_PARTITION_ICNT_TO_L2_QUEUE → IN_PARTITION_L2_TO_ICNT_QUEUE` — L2 hit fast-path
- `IN_PARTITION_L2_TO_DRAM_QUEUE → IN_PARTITION_DRAM → IN_PARTITION_MC_RETURNQ` — DRAM service path
- `IN_ICNT_TO_SHADER → IN_SHADER_FETCHED` — response delivered to shader core

---

## 10. Error / Edge Cases

| Scenario | Handling |
|----------|----------|
| **Deadlock detection** | Every 50 000 cycles, `deadlock_check()` compares `gpu_sim_insn` to previous snapshot. If no progress, dumps full core/memory/interconnect state and aborts simulation. |
| **CTA resource exhaustion** | `can_issue_1block()` checks threads, registers, shared memory, max-CTA limit, and HW thread IDs. Returns false if any resource is insufficient — CTA launch is retried next cycle. |
| **All cache ways RESERVED** | `tag_array::probe()` returns `RESERVATION_FAIL`; the request is retried next cycle to avoid deadlock from evicting a line with an outstanding fill. |
| **MSHR full** | `mshr_table::full()` returns true when per-entry merge limit or total entry count is reached. The miss is stalled (`RESERVATION_FAIL`) until an MSHR entry frees. |
| **DRAM queue full** | `dram_t::full()` prevents new pushes. L2-to-DRAM arbitration backs off; `gpu_stall_dramfull` counter incremented. |
| **Interconnect back-pressure** | `icnt_has_buffer()` checked before `icnt_push()`; if false, the response is held and `gpu_stall_icnt2sh` is incremented. |
| **Write-back deadlock prevention** | L1 write-back requests (`L1_WRBK_ACC`) bypass the L2→ICNT queue to avoid circular stalls in the write-back path. |
| **Read-after-write in MSHR** | `mshr_table::is_read_after_write_pending()` scans merged entries for a write followed by a read to prevent reordering violations. |
| **Cache configuration validation** | `cache_config::init()` rejects write-back with ON_FILL allocation (deadlock risk) and enforces sector-size divisibility for sector caches. |
| **Address-space sweep test** | `linear_to_raw_address_translation::sweep_test()` validates that configured bit masks cover the full address space without aliasing. |
