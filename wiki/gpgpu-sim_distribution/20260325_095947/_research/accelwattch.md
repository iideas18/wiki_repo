# AccelWattch — GPU Power Modeling Module

> **Module Path:** `src/accelwattch/`
> **Sub-directories:** `cacti/`, `results/`
> **Language:** C++ (35 source files compiled into `libaccelwattch.a`)
> **Lineage:** Fork of McPAT v0.8β (HP Labs, MICRO 2009) adapted for GPU architectures
> **Key Contributors:** Tor M. Aamodt, Tayler Hetherington, Ahmed ElTantawy, Vijay Kandiah, Nikos Hardavellas, Jingwen Leng, Syed Gilani

---

## 1. Purpose

AccelWattch is the GPU architectural power modeling component of GPGPU-Sim. It estimates **dynamic power**, **leakage power**, and **area** for every major on-chip structure — cores (streaming multiprocessors), caches, register files, execution units, NoC, memory controllers, and I/O controllers — by combining activity counters collected during cycle-level simulation with analytical circuit models derived from CACTI and McPAT. The module is conditionally compiled (`#ifdef GPGPUSIM_POWER_MODEL`) and supports three modes: pure simulation, pure hardware measurement, and a hybrid mode that blends simulated and measured performance counters per-component.

---

## 2. Sub-module Overview

### 2.1 Root Files (McPAT-derived GPU Power Model)

| File | Purpose |
|------|---------|
| `gpgpu_sim_wrapper.h/.cc` | **Integration shim** — bridges GPGPU-Sim's `power_interface` to McPAT. Manages XML config loading, performance-counter ingestion via 20+ `set_*_power()` methods, power computation orchestration, trace file I/O (gzip-compressed), and steady-state detection. |
| `processor.h/.cc` | **Top-level component hierarchy** — instantiates all sub-components (cores, L2/L3 caches, NoC, memory controller, I/O controllers), runs TDP and runtime `computeEnergy()`, and implements power-coefficient scaling (`coefficient_scale`, `nonlinear_scale`, `iterative_lse`). |
| `core.h/.cc` | **GPU Streaming Multiprocessor model** — the largest file (~290 KB). Builds sub-components: InstFetchU, LoadStoreU, MemManU, EXECU (containing RegFU, SchedulerU, FunctionalUnits, bypass interconnects), RENAMINGU, Pipeline, UndiffCore. Each sub-unit calls CACTI for array structures. |
| `XML_Parse.h/.cc` | **Configuration parser** — reads XML files into nested C structs (`root_system → system_core → icache_systemcore`, etc.). Defines 44 performance counter enums (`perf_count_t`) and per-component parameter structs. |
| `xmlParser.h/.cc` | **Low-level XML DOM** — lightweight XML parser providing `XMLNode` tree with parsing, navigation, modification, and serialization. Supports UTF-8, ShiftJIS, GB2312, Big5 encodings. |
| `sharedcache.h/.cc` | **L2/L3 cache power** — models unified cache arrays plus miss/fill/prefetch/write-back buffers and internal interconnect. Supports directory types: ST (shadowed tag), SBT (sparse bit table), DC (directory cache). |
| `memoryctrl.h/.cc` | **DRAM controller hierarchy** — MCFrontEnd (command queue, read/write buffers, page table), MCBackend (protocol engine), MCPHY (SerDes transceiver), DRAM (refresh/sense-amp). Supports DDR2/3/GDDR3/GDDR5 models. |
| `noc.h/.cc` | **Network-on-Chip** — router-based or bus-based interconnect. Router includes VC buffers, crossbar, arbiter. Traffic-pattern modulation (default 0.6). |
| `interconnect.h/.cc` | **Wire/bus modeling** — wraps CACTI Wire class. Supports global/semi-global/local/low-swing wires, auto-pipelining for long buses, process-scaled delay/power. |
| `logic.h/.cc` | **Control logic components** — selection_logic (issue arbitration), dep_resource_conflict_check (register dependency), inst_decoder, DFFCell, Pipeline (stage registers), FunctionalUnit (ALU/FPU/MUL), UndiffCore (undifferentiated core area). |
| `basic_components.h/.cc` | **Enums, parameter structs, utilities** — defines `FU_type`, `Core_type`, `Cache_policy`, `Device_ty`, `Dram_type`; provides `CoreDynParam`, `CacheDynParam`, `MCParam`, `NoCParam`, `DRAMParam`; implements `longer_channel_device_reduction()` and stats operator overloads. |
| `array.h/.cc` | **CACTI array bridge** — `ArrayST` wraps CACTI's `uca_org_t` for SRAM/CAM arrays. `optimize_array()` iteratively relaxes timing constraints to find minimum-energy solution. `InstCache`/`DataCache` compose multiple ArrayST for caches with miss/fill/WB buffers. |
| `iocontrollers.h/.cc` | **I/O controller power** — NIUController (Ethernet MAC+PCS+SerDes), PCIeController (multi-lane PHY), FlashController (NAND/SSD). Empirical area/power models scaled by process node. |
| `arch_const.h` | Default architecture constants (90 nm, 1.2 GHz, 8 cores, cache/TLB sizes). |
| `globalvar.h` | Global `opt_for_clk` flag. |
| `technology_xeon_core.cc` | Technology parameter initialization for 22–90 nm nodes (ITRS-based). Wire resistance/capacitance, device I_on/I_off, SRAM/DRAM cell parameters. |
| `main.cc` | Standalone McPAT entry point (`-infile`, `-print_level`, `-opt_for_clk`). |

### 2.2 `cacti/` Sub-directory (Cache/Memory Analytical Model)

CACTI (Cache Access and Cycle Time model, HP Labs) provides area, timing, and power for any SRAM/DRAM/CAM array given geometry parameters.

| File | Purpose |
|------|---------|
| `cacti_interface.h/.cc` | **Public API** — defines `powerComponents` (dynamic/leakage/gate_leakage/short_circuit), `powerDef` (read/write/search ops), `InputParameter` (cache geometry + optimization weights), `TechnologyParameter` (device/interconnect models), `uca_org_t` (solution struct). Entry point: `cacti_interface()`. |
| `Ucache.h/.cc` | **Unified cache solver** — `solve()` exhaustively searches partition space (Ndwl × Ndbl × Nspd × Ndcm × Ndsam) with multi-threaded evaluation. `filter_data_arr()`/`filter_tag_arr()` prune dominated solutions. Combines tag+data arrays into final `uca_org_t`. |
| `bank.h/.cc` | **Bank-level model** — aggregates Mat objects, calculates bank delay (row decoder → bitline → sense-amp → output mux). |
| `mat.h/.cc` | **Mat (matrix) model** — ~82 KB, largest CACTI file. Models subarray-level timing including wordline/bitline delay, sense-amp, column mux, pre-charge. |
| `subarray.h/.cc` | **Subarray cell array** — physical dimensions from cell size × row × col counts. |
| `parameter.h/.cc` | **DynamicParameter** — runtime-computed partition factors (Ndwl, Ndbl, Nspd, etc.), subarray dimensions, port counts. `InputParameter` validation. |
| `wire.h/.cc` | **Wire delay/power model** — supports Global, Global_5/10/20/30 (delay-penalty trade-offs), Low_swing (differential). Repeater insertion optimization. Static per-technology tables. |
| `area.h/.cc` | **Area accounting** — `Area` class (height × width) with operators for combining sub-component areas. |
| `decoder.h/.cc` | **Row/column decoders** — multi-stage NAND/NOR decoders with pre-decoders. Logical-effort-based gate sizing for minimum delay. |
| `htree2.h/.cc` | **H-tree routing** — hierarchical signal distribution for address, data-in, data-out across banks. Supports repeater insertion. |
| `uca.h/.cc` | **Unified Cache Architecture** — top-level combining tag+data banks with H-tree routing. Access time depends on mode (sequential, parallel, fast). |
| `nuca.h/.cc` | **Non-Uniform Cache Architecture** — mesh-based cache with routers. Models variable-latency access based on distance. |
| `router.h/.cc` | **MCPAT_Router** — 2D mesh router with crossbar, VC buffers, arbiters. |
| `crossbar.h/.cc` | **Crossbar switch** — tri-state buffer matrix (N × M × data_width). Area/power scales with port count. |
| `arbiter.h/.cc` | **Arbiter logic** — VC arbitration, priority encoding, grant signal generation. |
| `basic_circuit.h/.cc` | **Transistor-level primitives** — `cmos_Isub_leakage()`, `cmos_Ig_leakage()`, drain/gate capacitance calculations, logical effort helpers. Supports stacked gates and temperature-dependent leakage. |
| `component.h/.cc` | **Base Component class** — `Area area`, `powerDef power/rt_power`, `double delay/cycle_time`. Common base for all CACTI objects. |
| `const.h` | Array size limits (`MAXDATAN=512`, `MAXSUBARRAYS=1048576`), threshold voltage constants, gate type enums. |
| `technology.cc` | **~130 KB technology database** — complete ITRS device/wire parameters for 22–180 nm nodes. HP/LSTP/LOP device types. SRAM/DRAM cell dimensions. |
| `io.h/.cc` | **I/O and reporting** — cache configuration parsing, result output formatting (~84 KB). |

---

## 3. Key Classes

### 3.1 Root Module Classes

| # | Class | Header | Inherits | Purpose |
|---|-------|--------|----------|---------|
| 1 | `gpgpu_sim_wrapper` | `gpgpu_sim_wrapper.h` | — | Top-level integration shim. Owns `Processor*` and `ParseXML*`. Provides `set_*_power()` API for injecting perf counters, `compute()` to trigger power calculation, trace file management. |
| 2 | `Processor` | `processor.h` | `Component` | Top of McPAT hierarchy. Owns vectors of `Core*`, `SharedCache*` (L2/L3/dir), `NoC*`, `MemoryController*`, I/O controllers. Builds entire component tree in constructor. |
| 3 | `Core` | `core.h` | `Component` | GPU Streaming Multiprocessor. Contains `InstFetchU`, `LoadStoreU`, `MemManU`, `EXECU`, `RENAMINGU`, `Pipeline`, `UndiffCore`. Has 20+ `get_coefficient_*()` methods for per-component power extraction. |
| 4 | `ParseXML` | `XML_Parse.h` | — | Parses XML config into `root_system sys` struct tree. `parse()` loads file; `initialize()` zeros all fields. |
| 5 | `SharedCache` | `sharedcache.h` | `Component` | L2/L3 cache model. Contains `DataCache unicache` (arrays + buffers), supports directory types (ST/SBT/DC). |
| 6 | `MemoryController` | `memoryctrl.h` | `Component` | Complete MC: `MCFrontEnd` (queues), `MCBackend` (protocol), `MCPHY` (transceiver), `DRAM` (refresh). |
| 7 | `NoC` | `noc.h` | `Component` | Network-on-Chip. Contains `MCPAT_Router*` and/or `interconnect*` (link bus). Traffic-pattern-modulated power. |
| 8 | `interconnect` | `interconnect.h` | `Component` | Wire/bus power model. Wraps CACTI `Wire`. Supports pipelining, various wire types (Global/Low_swing), process scaling. |
| 9 | `ArrayST` | `array.h` | `Component` | SRAM/CAM array wrapper over CACTI `uca_org_t`. `optimize_array()` iterative search. Used everywhere for caches, TLBs, register files, BTBs. |
| 10 | `InstFetchU` | `core.h` | `Component` | Instruction fetch unit: `InstCache` (icache + MSHR + IFB + prefetch buffer), `BranchPredictor`, `inst_decoder` ×3, `BTB`. |
| 11 | `EXECU` | `core.h` | `Component` | Execution unit: `RegFU` (register file), `SchedulerU` (instruction window), `FunctionalUnit` ×3 (FPU/ALU/MUL), bypass interconnects ×6. |
| 12 | `LoadStoreU` | `core.h` | `Component` | Load-store unit: `DataCache` ×4 (dcache, ccache, tcache, shared memory), `LSQ`, `Crossbar`, internal `NoC`. |
| 13 | `FunctionalUnit` | `logic.h` | `Component` | ALU/FPU/MUL power. Energy from CACTI area-based estimation scaled by operation type and duty cycle. |
| 14 | `Pipeline` | `logic.h` | `Component` | Pipeline register power. `compute_stage_vector()` builds stage count; `compute()` calculates DFF-based register power per stage. |
| 15 | `RegFU` | `core.h` | `Component` | Register file unit: `ArrayST` ×3 (IRF, FRF, OPC operand collectors), `Crossbar`, `MCPAT_Arbiter`. |

### 3.2 CACTI Classes

| # | Class | Header | Inherits | Purpose |
|---|-------|--------|----------|---------|
| 16 | `Component` | `component.h` | — | Base class with `Area area`, `powerDef power/rt_power`, `double delay/cycle_time`. |
| 17 | `powerComponents` | `cacti_interface.h` | — | `dynamic`, `leakage`, `gate_leakage`, `short_circuit`, `longer_channel_leakage`. |
| 18 | `powerDef` | `cacti_interface.h` | — | `readOp`, `writeOp`, `searchOp` — each a `powerComponents`. |
| 19 | `InputParameter` | `cacti_interface.h` | — | Cache geometry (`cache_sz`, `line_sz`, `assoc`, `nbanks`), ports, technology (`F_sz_nm`, `temp`), optimization weights, wire type, access mode. |
| 20 | `TechnologyParameter` | `cacti_interface.h` | — | Nested `DeviceType` (capacitance, Vth, I_on, I_off, leakage) and `InterconnectType` (pitch, R/C per µm). Global instance `g_tp`. |
| 21 | `uca_org_t` | `cacti_interface.h` | — | Solution struct: `mem_array *tag_array2/data_array2`, combined `access_time`, `cycle_time`, `area`, `power`. |
| 22 | `mem_array` | `cacti_interface.h` | — | Single array partition: `Ndwl`, `Ndbl`, `Nspd`, mux degrees, `access_time`, `cycle_time`, `area`, `power`. |
| 23 | `UCA` | `uca.h` | `Component` | Unified Cache Architecture: combines tag+data banks with H-tree. Calculates aggregate timing for sequential/parallel/fast access modes. |
| 24 | `Bank` | `bank.h` | `Component` | Bank-level aggregation of Mat objects. |
| 25 | `Mat` | `mat.h` | `Component` | Core computational unit — models subarray timing (wordline, bitline, sense-amp, column mux). |
| 26 | `Wire` | `wire.h` | `Component` | Wire delay/power with repeater optimization. Static tables per technology. Types: Global, Global_5/10/20/30, Low_swing. |
| 27 | `Htree2` | `htree2.h` | `Component` | H-tree signal distribution: address, data-in, data-out across banks. |
| 28 | `Decoder` | `decoder.h` | `Component` | Multi-stage NAND/NOR decoders with pre-decoders. Logical-effort gate sizing. |
| 29 | `MCPAT_Router` | `router.h` | `Component` | Mesh router: crossbar + VC buffers + arbiter. Used by NoC and NUCA. |
| 30 | `Crossbar` | `crossbar.h` | `Component` | N×M tri-state buffer switch matrix. |

### 3.3 Parameter / Config Structs

| # | Struct/Class | Header | Purpose |
|---|-------------|--------|---------|
| 31 | `CoreDynParam` | `basic_components.h` | Per-core dynamic parameters: widths (fetch/decode/issue/commit), pipeline stages, ALU/FPU counts, duty cycles, register dimensions. |
| 32 | `CacheDynParam` | `basic_components.h` | Cache parameters: capacity, block width, associativity, banks, throughput, latency, directory type. |
| 33 | `MCParam` | `basic_components.h` | Memory controller: clock, channels, bus widths, access counts, LVDS/PHY flags. |
| 34 | `DRAMParam` | `basic_components.h` | DRAM timing (tRCD, tRAS, tRP, tCL, tRC, etc.), IDD current parameters, voltage, command coefficients. |
| 35 | `NoCParam` | `basic_components.h` | NoC: flit size, ports, VC count, buffer entries, node topology, link properties. |
| 36 | `root_system` | `XML_Parse.h` | Complete system config tree: `system_core[]`, `system_L2[]`, `system_L3[]`, `system_NoC[]`, `system_mc`, `system_mem`. |

---

## 4. Representative Snippets

### 4.1 gpgpu_sim_wrapper — Integration API

```cpp
// gpgpu_sim_wrapper.h (simplified)
class gpgpu_sim_wrapper {
public:
  gpgpu_sim_wrapper(bool power_simulation_enabled, char* xmlfile,
                    int power_simulation_mode, bool dvfs_enabled);
  void init_mcpat(char* xmlfile, char* powerfile, char* power_trace_file,
                  char* metric_trace_file, char* steady_state_file,
                  bool power_sim_enabled, bool trace_enabled, ...);
  // Performance counter injection (called each sampling interval)
  void set_inst_power(bool clk_gated_lanes, double tot_cycles, double busy_cycles,
                      double tot_inst, double int_inst, double fp_inst,
                      double load_inst, double store_inst, double committed_inst);
  void set_regfile_power(double reads, double writes, double ops);
  void set_l1cache_power(double rd_acc, double rd_miss, double wr_acc, double wr_miss);
  void set_l2cache_power(double rd_acc, double rd_miss, double wr_acc, double wr_miss);
  void set_mem_ctrl_power(double reads, double writes, double dram_precharge);
  void set_exec_unit_power(double fpu_acc, double ialu_acc, double sfu_acc);
  void set_NoC_power(double noc_tot_acc);
  // Trigger power calculation and output
  void compute();
  void update_components_power();
  void power_metrics_calculations();
  void dump();

private:
  Processor* proc;                                  // McPAT processor model
  ParseXML* p;                                      // Parsed XML configuration
  std::vector<avg_max_min_counters<double>> kernel_cmp_pwr;   // 33 components
  std::vector<avg_max_min_counters<double>> kernel_cmp_perf_counters; // 44 counters
};
```

### 4.2 Processor — Component Hierarchy

```cpp
// processor.h (simplified)
class Processor : public Component {
public:
  ParseXML *XML;
  vector<Core *> cores;
  vector<SharedCache *> l2array;
  vector<SharedCache *> l3array;
  vector<NoC *> nocs;
  MemoryController *mc;
  NIUController *niu;
  PCIeController *pcie;
  FlashController *flashcontroller;
  int numCore, numL2, numL3, numNOC;

  Processor(ParseXML *XML_interface);
  void compute();                  // Runtime power from activity counters
  void set_proc_param();           // Extract config from XML
  void displayEnergy(uint32_t indent = 0, int plevel = 100, bool is_tdp = true);
  // Power coefficient extraction for the wrapper
  double get_const_dynamic_power();
  double get_coefficient_l2_read_hits();
  double get_coefficient_mem_reads();
  void coefficient_scale();
  void nonlinear_scale(int, double, int);
  void iterative_lse(double*, double*);
};
```

### 4.3 Core — Streaming Multiprocessor

```cpp
// core.h (simplified)
class Core : public Component {
public:
  InstFetchU *ifu;     // Instruction fetch: icache, BTB, branch predictor, decoders
  LoadStoreU *lsu;     // Load-store: dcache, ccache, tcache, shared memory, LSQ
  MemManU    *mmu;     // Memory management: iTLB, dTLB
  EXECU      *exu;    // Execution: RegFU, SchedulerU, FPU, ALU, MUL, bypass nets
  RENAMINGU  *rnu;     // Register renaming: FRAT, RRAT, free lists
  Pipeline   *corepipe;
  UndiffCore *undiffCore;

  Core(ParseXML *XML_interface, int ithCore_, InputParameter *interface_ip_);
  void set_core_param();
  void computeEnergy(bool is_tdp = true);
  void compute();              // Runtime power update

  // Per-sub-component power coefficients (33 total)
  float get_coefficient_icache_hits();
  float get_coefficient_dcache_readhits();
  float get_coefficient_fpu_accesses();
  float get_coefficient_duty_cycle();
};
```

### 4.4 CACTI powerDef — Power Decomposition

```cpp
// cacti/cacti_interface.h
class powerComponents {
public:
  double dynamic;                  // Switching power (0.5 × C × V² × f × α)
  double leakage;                  // Sub-threshold leakage (I_off × V_dd)
  double gate_leakage;             // Gate oxide tunneling current
  double short_circuit;            // Short-circuit (crowbar) current
  double longer_channel_leakage;   // Reduced leakage for long-channel devices
};

class powerDef {
public:
  powerComponents readOp;          // Read operation power breakdown
  powerComponents writeOp;         // Write operation power breakdown
  powerComponents searchOp;        // CAM search operation power (if applicable)
};
```

### 4.5 ArrayST — CACTI Array Wrapper with Iterative Optimization

```cpp
// array.h / array.cc (simplified)
class ArrayST : public Component {
public:
  InputParameter l_ip;
  uca_org_t local_result;          // CACTI solution (timing, area, power)
  statsDef tdp_stats, rtp_stats;   // TDP and runtime access statistics
  powerDef power_t;

  ArrayST(const InputParameter* configure_interface, string _name,
          enum Device_ty device_ty_, bool opt_local_ = true,
          enum Core_type core_ty_ = Inorder, bool _is_default = true);

  // Iteratively relax timing to find minimum-energy array configuration
  virtual void optimize_array() {
    while ((throughput_overflow || latency_overflow) && cycle_time_dev > 10) {
      compute_base_power();        // Calls CACTI solver
      cycle_time_dev -= 10;        // Relax by 10%
      if (meets_timing) candidates.push_back(local_result);
    }
    local_result = *min_energy(candidates);
  }

  void leakage_feedback(double temperature);  // Re-run CACTI at new temperature
};
```

### 4.6 MemoryController — DRAM Controller Hierarchy

```cpp
// memoryctrl.h (simplified)
class MemoryController : public Component {
public:
  MCFrontEnd *frontend;        // Command queue, read/write/page buffers
  MCBackend  *transecEngine;   // DDR protocol engine
  MCPHY      *PHY;             // Physical layer (SerDes)
  DRAM       *dram;            // DRAM die model (refresh, sense amp)
  Pipeline   *pipeLogic;
  MCParam mcp;

  MemoryController(ParseXML *XML_interface, InputParameter *interface_ip_,
                   enum MemoryCtrl_type mc_type_, enum Dram_type dram_type_);
  void set_mc_param();
  void computeEnergy(bool is_tdp = true);
};
```

---

## 5. Data Flow

### 5.1 Initialization Flow

```
gpgpu-sim startup (gpu-sim.cc)
  │  if GPGPUSIM_POWER_MODEL defined:
  ├─→ new gpgpu_sim_wrapper(enabled, xmlfile, mode, dvfs)
  │     ├─→ new ParseXML()
  │     │     └─→ p->parse(xmlfile)          // XML → root_system struct tree
  │     └─→ new Processor(p)
  │           ├─→ set_proc_param()            // Extract counts: numCore, numL2, ...
  │           ├─→ For i in 0..numCore-1:
  │           │     new Core(XML, i, &ip)
  │           │       ├─→ set_core_param()    // Extract CoreDynParam from XML
  │           │       ├─→ new InstFetchU(...)  // icache, BTB, BPT, decoders
  │           │       ├─→ new LoadStoreU(...)  // dcache, ccache, tcache, shmem
  │           │       ├─→ new MemManU(...)     // iTLB, dTLB
  │           │       ├─→ new EXECU(...)       // RegFU, Scheduler, FPU, ALU, MUL
  │           │       └─→ computeEnergy(true)  // TDP power (peak at max utilization)
  │           ├─→ For i in 0..numL2-1:
  │           │     new SharedCache(XML, i, &ip, L2)
  │           │       └─→ ArrayST::optimize_array() → CACTI solver
  │           ├─→ new MemoryController(XML, &ip, MC, GDDR5)
  │           ├─→ For i in 0..numNOC-1:
  │           │     new NoC(XML, i, &ip, M_traffic=0.6)
  │           └─→ new NIUController / PCIeController / FlashController
  └─→ init_mcpat(xmlfile, powerfile, tracefile, ...)
        └─→ Open output files (gzip compressed trace files)
```

### 5.2 Runtime Power Calculation Flow

```
Every gpu_stat_sample_freq cycles (in power_interface.cc):
  │
  ├─1─ Collect performance counters from simulator
  │     shader_cores → {instructions, cache hits/misses, reg accesses, ALU/FPU/SFU ops}
  │     memory_ctrl  → {DRAM reads, writes, precharges}
  │     interconnect → {NoC flits}
  │
  ├─2─ Inject counters into wrapper via set_*_power() methods
  │     wrapper->set_inst_power(clk_gated, tot_cyc, busy_cyc, tot_inst, int_inst, ...)
  │     wrapper->set_regfile_power(reads, writes, ops)
  │     wrapper->set_icache_power(accesses, misses)
  │     wrapper->set_l1cache_power(rd_acc, rd_miss, wr_acc, wr_miss)
  │     wrapper->set_l2cache_power(...)
  │     wrapper->set_exec_unit_power(fpu_acc, ialu_acc, sfu_acc)
  │     wrapper->set_int_accesses(ialu, imul24, imul32, imul, idiv)
  │     wrapper->set_fp_accesses(fpu, fpmul, fpdiv)
  │     wrapper->set_dp_accesses(dpu, dpmul, dpdiv)
  │     wrapper->set_trans_accesses(sqrt, log, sin, exp)
  │     wrapper->set_tensor_accesses(tensor)
  │     wrapper->set_tex_accesses(tex)
  │     wrapper->set_mem_ctrl_power(reads, writes, precharge)
  │     wrapper->set_NoC_power(noc_acc)
  │
  ├─3─ wrapper->compute()
  │     └─→ Processor::compute()
  │           ├─→ For each core[i]:
  │           │     Update XML stats from injected counters
  │           │     core[i]->computeEnergy(false)    // Runtime power
  │           │       ├─→ Each sub-unit: stats_t = actual_accesses
  │           │       ├─→ ArrayST.computeEnergy()    // CACTI: accesses × energy_per_access
  │           │       └─→ rt_power = Σ(sub-unit.rt_power)
  │           ├─→ For each l2[i]:
  │           │     l2->computeEnergy(false)
  │           ├─→ For each noc[i]:
  │           │     noc->computeEnergy(false)
  │           └─→ mc->computeEnergy(false)
  │
  ├─4─ wrapper->update_components_power()
  │     Extract per-component power into sample_cmp_pwr[0..32]
  │     Components: IBP, ICP, DCP, TCP, CCP, SHRDP, RFP, INTP, FPUP, DPUP,
  │                 INT_MUL24P, INT_MUL32P, INT_MULP, INT_DIVP, FP_MULP,
  │                 FP_DIVP, FP_SQRTP, FP_LGP, FP_SINP, FP_EXP, DP_MULP,
  │                 DP_DIVP, TENSORP, TEXP, SCHEDP, L2CP, MCP, NOCP, DRAMP,
  │                 PIPEP, IDLE_COREP, CONSTP, STATICP
  │
  ├─5─ wrapper->power_metrics_calculations()
  │     Update kernel_cmp_pwr[].avg/max/min
  │     Update gpu_tot_power.avg/max/min
  │
  └─6─ wrapper->dump() / print_trace_files()
        Write to power_trace.gz, metric_trace.gz
```

### 5.3 Power Formula at Each Component

```
Per-access dynamic energy:
  E_dynamic = 0.5 × C_load × V_dd² × activity_factor

Runtime dynamic power:
  P_dynamic = (num_accesses / total_cycles) × E_per_access × clock_rate

Leakage power:
  P_leakage = I_off × V_dd × num_transistors × long_channel_reduction

Total component power:
  P_total = P_dynamic + P_leakage + P_gate_leakage

Scaling to chip level:
  P_chip = Σ(P_component_i × pppm_t[i])
  where pppm_t = {dynamic_scale, leakage_scale, gate_leak_scale, area_scale}
```

---

## 6. Configuration Knobs

### 6.1 System-Level (XML)

| Parameter | XML Path | Example | Description |
|-----------|----------|---------|-------------|
| `number_of_cores` | `system` | 30 | SM count |
| `number_of_L2s` | `system` | 4 | L2 cache partitions |
| `number_of_L3s` | `system` | 0 | L3 cache count |
| `number_of_NoCs` | `system` | 1 | On-chip network count |
| `number_of_MCs` | `system.mc` | 4 | Memory controller count |
| `homogeneous_cores` | `system` | 1 | Whether all cores are identical |
| `core_tech_node` | `system` | 45 | Technology node (nm) |
| `target_core_clockrate` | `system` | 1300 | Target frequency (MHz) |
| `temperature` | `system` | 380 | Junction temperature (K) |
| `device_type` | `system` | 0 | 0=HP, 1=LSTP, 2=LOP |
| `interconnect_projection_type` | `system` | 0 | 0=aggressive, 1=conservative |

### 6.2 Core-Level (XML)

| Parameter | XML Path | Example | Description |
|-----------|----------|---------|-------------|
| `clock_rate` | `system.core0` | 1300 | Core clock (MHz) |
| `machine_type` | `system.core0` | 1 | 0=OOO, 1=Inorder |
| `number_hardware_threads` | `system.core0` | 32 | Warps per SM |
| `pipeline_depth` | `system.core0` | 6,6 | Int, FP pipeline stages |
| `issue_width` | `system.core0` | 1 | Instructions issued/cycle |
| `ALU_per_core` | `system.core0` | 1 | Integer ALU count |
| `FPU_per_core` | `system.core0` | 1 | Floating-point unit count |
| `MUL_per_core` | `system.core0` | 1 | Multiplier count |
| `instruction_length` | `system.core0` | 32 | ISA width (bits) |
| `opcode_width` | `system.core0` | 9 | Opcode field width |
| `SIMD_width` | `system.core0` | 8 | SIMD lane count |
| `warp_size` | `system.core0` | 32 | Threads per warp |
| `RF_banks` | `system.core0` | 4 | Register file bank count |
| `collector_units` | `system.core0` | 4 | Operand collector units |

### 6.3 Cache-Level (XML)

| Parameter | XML Path | Example | Description |
|-----------|----------|---------|-------------|
| `icache_config` | `system.core0.icache` | 16384,32,4,1,1,3 | Size,block,assoc,banks,throughput,latency |
| `dcache_config` | `system.core0.dcache` | 16384,32,4,1,1,3 | L1 data cache config |
| `L2_config` | `system.L20` | 786432,64,16,1,1,23 | L2 cache config |
| `buffer_sizes` | `system.L20` | 16,16,16,16 | MSHR,fill,prefetch,WB buffer sizes |
| `cache_policy` | `system.core0.dcache` | 0 | 0=write-through, 1=write-back |
| `directory_type` | `system.L20` | 1 | 0=NonDir, 1=ST, 2=SBT |
| `duty_cycle` | `system.L20` | 0.5 | Cache activity factor |

### 6.4 Memory (XML)

| Parameter | XML Path | Example | Description |
|-----------|----------|---------|-------------|
| `mem_tech_node` | `system.mem` | 32 | DRAM technology (nm) |
| `device_clock` | `system.mem` | 200 | DRAM clock (MHz) |
| `peak_transfer_rate` | `system.mem` | 3200 | Peak BW (MB/s) |
| `capacity_per_channel` | `system.mem` | 4096 | MB per channel |
| `number_ranks` | `system.mem` | 2 | DRAM ranks |
| `block_width` | `system.mc` | 128 | Cache line width (bits) |
| `databus_width` | `system.mc` | 128 | Data bus width (bits) |
| `addressbus_width` | `system.mc` | 51 | Address bus width (bits) |

### 6.5 Simulation Control (gpgpu-sim config)

| Parameter | Source | Description |
|-----------|--------|-------------|
| `power_simulation_enabled` | gpgpusim.config | Enable/disable power model |
| `power_simulation_mode` | gpgpusim.config | 0=sim only, 1=HW only, 2=hybrid |
| `gpu_stat_sample_freq` | gpgpusim.config | Sampling interval (cycles) |
| `steady_power_deviation` | gpgpusim.config | Threshold for steady-state detection |
| `steady_min_period` | gpgpusim.config | Minimum samples before steady-state |
| `power_trace_zlevel` | gpgpusim.config | Gzip compression level for traces |
| `accelwattch_hybrid_configuration[]` | gpgpusim.config | 30+ boolean flags for per-component HW/sim selection |

---

## 7. Interactions with GPGPU-Sim Core

### 7.1 Integration Points

| File | Role |
|------|------|
| `src/gpgpu-sim/power_interface.h/.cc` | **Bridge layer** — aggregates perf stats from shader cores, memory partitions, and interconnect; calls `gpgpu_sim_wrapper` methods each sampling interval. |
| `src/gpgpu-sim/gpu-sim.h/.cc` | **Owner** — holds `gpgpu_sim_wrapper *m_gpgpusim_wrapper` member. Calls `init_mcpat()` at first kernel launch. Triggers `mcpat_cycle()` every N cycles. Handles hybrid mode via `calculate_hw_mcpat()`. |
| `src/gpgpu-sim/power_stat.h/.cc` | **Statistics collector** — `power_stat_t` accumulates per-SM and per-partition counters fed to the power interface. |

### 7.2 Build Integration

```cmake
# Top-level CMakeLists.txt
set(GPGPUSIM_USE_POWER_MODEL OFF)   # Disabled by default

# src/accelwattch/CMakeLists.txt
add_library(accelwattch STATIC
  XML_Parse.cc processor.cc core.cc sharedcache.cc memoryctrl.cc
  noc.cc interconnect.cc logic.cc basic_components.cc array.cc
  iocontrollers.cc gpgpu_sim_wrapper.cc xmlParser.cc
  technology_xeon_core.cc
  cacti/Ucache.cc cacti/parameter.cc cacti/wire.cc cacti/area.cc
  cacti/bank.cc cacti/mat.cc cacti/subarray.cc cacti/uca.cc
  cacti/nuca.cc cacti/decoder.cc cacti/htree2.cc cacti/router.cc
  cacti/crossbar.cc cacti/arbiter.cc cacti/basic_circuit.cc
  cacti/component.cc cacti/cacti_interface.cc cacti/io.cc
  cacti/technology.cc cacti/highradix.cc
)

# Conditional compilation guard
target_compile_definitions(gpgpusim PRIVATE GPGPUSIM_POWER_MODEL)
target_link_libraries(cudart ... accelwattch)
```

### 7.3 Call Sequence During Simulation

```
gpu_sim_cycle() [every cycle in gpu-sim.cc]
  └─→ if (cycle % stat_sample_freq == 0)
        mcpat_cycle(gpu_sim)                    // power_interface.cc
          ├─→ Collect stats from all shader_cores[i]
          │     total_inst, int_inst, fp_inst, load_inst, store_inst
          │     icache_hit/miss, dcache_rh/rm/wh/wm
          │     regfile_reads/writes
          │     alu_accesses, fpu_accesses, sfu_accesses
          │     tensor_accesses, tex_accesses
          ├─→ Collect stats from memory_partition_unit[i]
          │     l2_read_hit/miss, l2_write_hit/miss
          │     dram_reads, dram_writes, dram_precharges
          ├─→ Collect stats from interconnect
          │     noc_total_flits
          ├─→ Call wrapper->set_*_power() for each stat
          ├─→ wrapper->compute()
          ├─→ wrapper->update_components_power()
          ├─→ wrapper->power_metrics_calculations()
          └─→ wrapper->dump() / print_trace_files()
```

### 7.4 Hybrid Mode

When `power_simulation_mode == 2`, AccelWattch can selectively use hardware performance counter measurements instead of simulated values. The `accelwattch_hybrid_configuration[]` array contains 30+ boolean flags (e.g., `HW_L1_RH`, `HW_L2_WM`, `HW_DRAM_RD`, `HW_VOLTAGE`) that control which components use real hardware data vs. simulation data. This enables validation and calibration of the power model against real GPU silicon.

---

## 8. Terminology

| Term | Definition |
|------|-----------|
| **Dynamic Power** | Power consumed during transistor switching: `P = 0.5 × C × V² × f × α`. Proportional to activity (access counts). |
| **Leakage Power** | Static power from sub-threshold current flow when transistors are off: `P = I_off × V_dd`. Temperature-dependent. |
| **Gate Leakage** | Current tunneling through ultra-thin gate oxide. Significant at ≤45 nm nodes. |
| **TDP (Thermal Design Power)** | Peak power at maximum sustained utilization. Computed with `is_tdp=true` using theoretical max access rates. |
| **McPAT** | Multicore Power, Area, and Timing framework (HP Labs, MICRO 2009). AccelWattch is built on McPAT v0.8β. |
| **CACTI** | Cache Access and Cycle Time model (HP Labs). Analytical model for SRAM/DRAM/CAM array area, timing, and power. |
| **ITRS** | International Technology Roadmap for Semiconductors. Source of device parameters for each technology node. |
| **Streaming Multiprocessor (SM)** | GPU core equivalent. Modeled as McPAT `Core` with GPU-specific extensions (warps, SIMD, shared memory). |
| **pppm_t** | Power/Performance/Power/Metric scaling tuple `{dynamic_scale, leakage_scale, gate_leak_scale, area_scale}`. |
| **Longer Channel Device** | Transistors with longer-than-minimum gate length to reduce leakage. Applied selectively: 56% of OOO core, 80% of Inorder core, 82% of uncore. |
| **uca_org_t** | CACTI solution structure containing optimal tag/data array partitions with combined timing, area, and power. |
| **Ndwl / Ndbl / Nspd** | CACTI partition parameters: word-line division, bit-line division, subarrays per disk. Key search dimensions. |
| **Activity Factor (α)** | Fraction of transitions per clock cycle. `duty_cycle` in config. Modulates dynamic power. |
| **Socket Coefficient** | `sckt_co_eff` — board-level power overhead factor applied to all dynamic power. |
| **Wire Type** | Interconnect model: Global (full-swing repeaters), Low_swing (differential, lower power), Semi_global. |
| **H-tree** | Hierarchical tree routing topology for distributing signals to banks in a cache array. O(log N) delay. |
| **NUCA** | Non-Uniform Cache Architecture — cache where access latency depends on physical distance (mesh-routed). |
| **GDDR5** | Graphics DDR5 memory. Modeled with specific timing parameters (tRCD, tRAS, tCL) and IDD current parameters. |
| **Operand Collector** | GPU-specific register file access mechanism modeled as ArrayST banks with crossbar. |
| **Power Coefficient** | Per-component multiplier relating one access count to power. Extracted by `get_coefficient_*()` methods for linear power model. |

---

## 9. Algorithms & Mechanisms

### 9.1 CACTI Partition Space Search

The core CACTI algorithm in `Ucache.cc::solve()` exhaustively searches the array configuration space:

```
Input: cache_sz, line_sz, assoc, nbanks, ports, technology_node
Output: optimal uca_org_t (area, timing, power)

1. FOR Nspd ∈ {0.125, 0.25, 0.5, 1, 2, ..., 256}:      // subarrays per bank
   FOR Ndwl ∈ {1, 2, 4, ..., 512}:                        // wordline divisions
     FOR Ndbl ∈ {1, 2, 4, ..., 512}:                      // bitline divisions
       FOR Ndcm ∈ {1, 2, 4, ..., 256}:                    // column mux degree
         FOR Ndsam_lev_1 ∈ {1, 2, 4, ..., 256}:           // sense-amp mux L1
           FOR Ndsam_lev_2 ∈ {1, 2, 4, ..., 256}:         // sense-amp mux L2
             IF valid_partition(params):
               result = calculate_time(Ndwl, Ndbl, Nspd, ...)
               IF result.meets_constraints:
                 candidates.add(result)

2. filter_data_arr(candidates)    // Remove dominated solutions
3. filter_tag_arr(candidates)

4. FOR each (tag_soln, data_soln) ∈ tag_candidates × data_candidates:
     combined = combine(tag_soln, data_soln)
     IF combined.objective < best.objective:
       best = combined

5. RETURN best  // uca_org_t with min weighted cost
```

The search is multi-threaded (NTHREADS partitions) and filtering removes Pareto-dominated solutions.

### 9.2 ArrayST Iterative Timing Relaxation

```
Input: target throughput, target latency
Output: minimum-energy array meeting relaxed timing

cycle_time_dev = 100%
WHILE (timing_violated AND cycle_time_dev > 10%):
  l_ip.throughput *= (1 + cycle_time_dev/100)
  l_ip.latency   *= (1 + cycle_time_dev/100)
  compute_base_power()              // Full CACTI solve
  IF solution.meets_timing:
    candidates.add(solution)
    break
  cycle_time_dev -= 10%             // Relax by 10% each iteration

RETURN min_dynamic_energy(candidates)
```

### 9.3 Power Coefficient Extraction

The `Processor` extracts per-activity-type power coefficients for linear power modeling:

```
For each component type (icache, dcache, regfile, ALU, ...):
  1. Set XML stats to 1 access for target component, 0 for all others
  2. Call computeEnergy(false)
  3. coefficient[component] = resulting_power_delta

Power estimation:
  P_total ≈ P_const + Σ(coefficient[i] × access_count[i])
```

### 9.4 Steady-State Detection

```
WHILE collecting power samples:
  samples.add(current_power)
  IF samples.size >= steady_min_period:
    recent_avg = mean(samples[-window:])
    recent_stddev = stddev(samples[-window:])
    IF recent_stddev / recent_avg < steady_power_deviation:
      DECLARE steady_state
      RECORD steady-state power value
```

### 9.5 Wire Delay with Repeater Insertion

```
// CACTI Wire model
unit_delay = R_wire × C_wire × (spacing/2)² + repeater_delay
total_delay = unit_delay × wire_length

// Auto-pipelining for long buses
IF pipelinable AND delay > throughput:
  num_stages = ceil(delay / throughput)
  delay = delay/num_stages + num_stages × 0.05 × delay  // register overhead
```

### 9.6 Longer Channel Leakage Reduction

```
Input: device_type (Core/Uncore/LLC), core_type (OOO/Inorder)
Output: leakage_reduction_factor

IF Core_device:
  percentage = (OOO) ? 0.56 : 0.80     // 56% OOO, 80% Inorder use long-channel
ELIF Uncore_device:
  percentage = 0.82
ELIF LLC_device:
  percentage = 1.0                       // All long-channel for LLC

factor = (1 - percentage) + percentage × g_tp.long_channel_leakage_reduction
// Example: OOO → (1-0.56) + 0.56 × 0.5 = 0.44 + 0.28 = 0.72 (28% reduction)
```

### 9.7 DRAM Power Model

```
// Empirical model with per-command coefficients (from DRAMParam)
P_dram = cmd_coeff × commands_per_sec
       + activity_coeff × row_activations
       + nop_coeff × idle_cycles
       + rd_coeff × reads + wr_coeff × writes
       + pre_coeff × precharges
       + const_coeff

// Detailed model (IDD-based, from JEDEC datasheets)
P_active = (IDD0 - IDD3N) × tRC × V_dd × ranks
P_read   = (IDD4R - IDD3N) × burst_length/tCK × V_dd
P_write  = (IDD4W - IDD3N) × burst_length/tCK × V_dd
P_refresh = IDD5 × tRFC/tREFI × V_dd
P_standby = IDD2N × V_dd
```

---

## 10. State Machines / Lifecycle

### 10.1 Power Model Lifecycle

```
┌──────────────┐
│  UNINITIALIZED │   Power model not yet created
└──────┬───────┘
       │  Constructor: gpgpu_sim_wrapper(enabled, xml, mode, dvfs)
       │  → ParseXML::parse() → Processor() → TDP computeEnergy(true)
       ▼
┌──────────────┐
│  INITIALIZED   │   XML parsed, component tree built, TDP power computed
└──────┬───────┘
       │  init_mcpat(files, flags, ...)
       │  → Open output files, configure sampling
       ▼
┌──────────────┐
│    ACTIVE      │   Accepting performance counter updates
│                │   ←── set_*_power() called each sample interval
└──────┬───────┘
       │  compute() → update_components_power() → dump()
       ▼
┌──────────────┐
│  SAMPLING      │◄─── Repeats every gpu_stat_sample_freq cycles
│                │   Accumulates kernel_cmp_pwr, checks steady-state
└──────┬───────┘
       │  Kernel completes → print_power_kernel_stats()
       │  → reset_counters()
       ▼
┌──────────────┐
│  KERNEL_DONE   │   Per-kernel power stats printed
│                │   Counters reset for next kernel
└──────┬───────┘
       │  Next kernel launches → back to ACTIVE
       │  or
       │  Simulation ends → close_files()
       ▼
┌──────────────┐
│   FINISHED     │   All files closed, destructor cleans up
└──────────────┘
```

### 10.2 computeEnergy Two-Phase Pattern

Every component follows the same two-phase pattern:

```
Phase 1: TDP (is_tdp = true) — called once during initialization
  - stats_t set to theoretical maximum utilization
  - e.g., stats_t.readAc.access = 0.67 × ports × duty_cycle
  - Result: power.readOp = peak_power (used as baseline)

Phase 2: Runtime (is_tdp = false) — called each sample interval
  - stats_t set to actual access counts from simulator
  - e.g., stats_t.readAc.access = XML->sys.core[i].dcache.read_accesses
  - Result: rt_power.readOp = actual_power (used for reporting)
```

---

## 11. Error Handling & Edge Cases

### 11.1 Sanity Checks

- **`gpgpu_sim_wrapper::sanity_check(a, b)`** — validates that performance counter values are within expected ranges before feeding to McPAT.
- **Division by zero protection** — `executionTime = total_cycles / (clock_rate × 1e6)`; if `total_cycles == 0`, power defaults to TDP.
- **Zero-access components** — if a component has zero accesses in a sample, `rt_power.dynamic = 0` but `leakage` remains non-zero.

### 11.2 CACTI Solution Failures

- **No valid partition** — if CACTI cannot find a valid array configuration (too small, too aggressive timing), `optimize_array()` progressively relaxes timing by 10% steps down to 10% of target.
- **Timing overflow flags** — `throughput_overflow` and `latency_overflow` track whether the best solution exceeds timing constraints; the wrapper accepts the least-bad solution.

### 11.3 Technology Node Boundaries

- **Supported nodes**: 22, 32, 45, 65, 90 nm (ITRS-based parameters in `technology.cc`).
- **Out-of-range nodes** — requesting unsupported technology nodes falls back to nearest supported node or produces undefined behavior.

### 11.4 Temperature-Dependent Leakage

- **`leakage_feedback(temperature)`** — recalculates leakage at new temperature (quantized to nearest 10K). Called when thermal modeling indicates temperature change.
- **Exponential sensitivity** — leakage approximately doubles per 10°C increase; the model captures this via `cmos_Isub_leakage()` temperature coefficients.

### 11.5 Clock Gating

- **Clock-gated lanes** — `set_inst_power(clk_gated_lanes=true, ...)` reduces dynamic power for inactive SIMD lanes.
- **Idle cores** — `set_idle_core_power(num_idle_core)` applies leakage-only power for inactive SMs.

### 11.6 DVFS Support

- **`set_model_voltage(voltage)`** — dynamically adjusts V_dd for DVFS scenarios.
- **Voltage scaling** — dynamic power scales as V², leakage scales approximately linearly with voltage.
- **`g_dvfs_enabled`** flag controls whether voltage scaling is active.

### 11.7 Hybrid Mode Fallbacks

- **Missing HW counters** — if hardware performance counter data is unavailable for a component flagged as HW in hybrid mode, falls back to simulated value.
- **`accelwattch_hybrid_configuration[]`** — 30+ individual flags allow fine-grained control over which components use HW vs. simulated data.

---

## Appendix: File Index

### Root (`src/accelwattch/`)

| File | Lines (approx) | Role |
|------|----------------|------|
| `gpgpu_sim_wrapper.h` | 170 | Integration API header |
| `gpgpu_sim_wrapper.cc` | 1000 | Integration implementation |
| `processor.h` | 120 | Processor hierarchy header |
| `processor.cc` | 1200 | Component tree builder |
| `core.h` | 450 | Core/SM sub-components header |
| `core.cc` | 5000+ | Core implementation (largest) |
| `XML_Parse.h` | 700 | Config struct definitions |
| `XML_Parse.cc` | 4500 | XML parsing implementation |
| `xmlParser.h` | 600 | XML DOM parser header |
| `xmlParser.cc` | 4000+ | XML DOM implementation |
| `sharedcache.h` | 80 | Shared cache header |
| `sharedcache.cc` | 1200 | L2/L3 cache power |
| `memoryctrl.h` | 200 | Memory controller header |
| `memoryctrl.cc` | 1200 | MC/DRAM power |
| `noc.h` | 80 | NoC header |
| `noc.cc` | 455 | Router/bus power |
| `interconnect.h` | 80 | Wire header |
| `interconnect.cc` | 200 | Wire power |
| `logic.h` | 300 | Control logic header |
| `logic.cc` | 1340 | Logic component power |
| `basic_components.h` | 350 | Enums/structs/utilities header |
| `basic_components.cc` | 117 | Utility implementations |
| `array.h` | 80 | CACTI array bridge header |
| `array.cc` | 310 | Array optimization |
| `iocontrollers.h` | 80 | I/O controller header |
| `iocontrollers.cc` | 450 | NIU/PCIe/Flash power |
| `main.cc` | 96 | Standalone entry point |
| `technology_xeon_core.cc` | 1500+ | Technology parameters |

### `cacti/`

| File | Lines (approx) | Role |
|------|----------------|------|
| `cacti_interface.h` | 650 | Public CACTI API and structs |
| `cacti_interface.cc` | 200 | Interface implementation |
| `Ucache.h` | 80 | Solver header |
| `Ucache.cc` | 1000 | Partition search solver |
| `bank.h/.cc` | 80/250 | Bank-level model |
| `mat.h/.cc` | 150/2800 | Matrix-level timing (largest CACTI) |
| `subarray.h/.cc` | 70/250 | Cell array model |
| `parameter.h/.cc` | 300/900 | Dynamic parameter computation |
| `wire.h/.cc` | 120/1000 | Wire delay/power model |
| `area.h/.cc` | 60/60 | Area calculation |
| `decoder.h/.cc` | 200/2000 | Decoder model |
| `htree2.h/.cc` | 100/800 | H-tree routing |
| `uca.h/.cc` | 90/650 | Unified cache top-level |
| `nuca.h/.cc` | 90/550 | Non-uniform cache |
| `router.h/.cc` | 100/350 | Mesh router |
| `crossbar.h/.cc` | 80/250 | Crossbar switch |
| `arbiter.h/.cc` | 70/180 | Arbitration logic |
| `basic_circuit.h/.cc` | 160/700 | Transistor primitives |
| `component.h/.cc` | 80/250 | Base Component class |
| `const.h` | 300 | Constants and limits |
| `technology.cc` | 4300 | Complete technology database |
| `io.h/.cc` | 60/2800 | Configuration I/O |
