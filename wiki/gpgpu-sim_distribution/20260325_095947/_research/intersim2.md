# InterSim2 — Interconnection Network Simulator (Research Report)

> **Module path**: `src/intersim2/`
> **Origin**: BookSim 2.0 (Stanford), adapted for GPGPU-Sim by UBC (Tor M. Aamodt, Dongdong Li, Ali Bakhoda)
> **Date**: 2026-03-25

---

## 1. Purpose

InterSim2 is a cycle-accurate interconnection network (NoC) simulator integrated into GPGPU-Sim. It models the on-chip network that connects shader cores (SMs) to memory partition units, faithfully simulating flit-level routing, virtual-channel flow control, switch allocation, and crossbar traversal. Based on Stanford's BookSim 2.0, it has been extended with a GPU-specific traffic manager (`GPUTrafficManager`) and an adapter layer (`InterconnectInterface`) that bridges GPGPU-Sim's memory system to the NoC simulation.

---

## 2. Sub-module Overview

### 2.1 allocators/ — Switch & VC Allocators

**Purpose**: Implements allocator algorithms that resolve contention when multiple input VCs compete for the same output port or output VC during switch allocation and VC allocation stages.

**Key Classes**:

| Class | File | Role |
|-------|------|------|
| `Allocator` | `allocator.hpp` | Abstract base; defines `AddRequest()`, `Allocate()`, `OutputAssigned()` interface; factory `NewAllocator()` |
| `DenseAllocator` | `allocator.hpp` | Stores full NxM request matrix; used by Wavefront |
| `SparseAllocator` | `allocator.hpp` | Stores requests in sparse maps (`_in_req`, `_out_req`); used by iSLIP, Separable, PIM, LOA, SelAlloc |
| `iSLIP_Sparse` | `islip.hpp` | Iterative round-robin matching (iSLIP algorithm); `_gptrs`/`_aptrs` grant/accept pointers |
| `Wavefront` | `wavefront.hpp` | Diagonal-sweep matching on the dense request matrix |
| `SeparableAllocator` | `separable.hpp` | Two-phase separable allocation using per-input and per-output `Arbiter` objects |
| `SeparableInputFirst` | `separable_input_first.hpp` | Input-first variant of separable allocation |
| `SeparableOutputFirst` | `separable_output_first.hpp` | Output-first variant of separable allocation |
| `PIM` | `pim.hpp` | Parallel Iterative Matching allocator |
| `LOA` | `loa.hpp` | Lonely Output Allocator — prioritizes outputs with few requests |
| `SelAlloc` | `selalloc.hpp` | Selection-based allocator |
| `MaxSizeMatch` | `maxsize.hpp` | Maximum-size matching allocator |

**Key Algorithms**: iSLIP (iterative round-robin), Wavefront (diagonal sweep), Separable (input-first/output-first decomposition), PIM (randomized parallel matching).

---

### 2.2 arbiters/ — Arbiter Primitives

**Purpose**: Low-level arbitration building blocks used by separable allocators. Each arbiter selects one winner from a set of competing requests on a single resource.

**Key Classes**:

| Class | File | Role |
|-------|------|------|
| `Arbiter` | `arbiter.hpp` | Abstract base; `AddRequest(input, id, pri)`, `Arbitrate()`, `UpdateState()` |
| `RoundRobinArbiter` | `roundrobin_arb.hpp` | Classic round-robin priority rotation |
| `MatrixArbiter` | `matrix_arb.hpp` | Matrix-based priority arbiter (NxN priority matrix, winner demotes losers) |
| `PriorityArbiter` | `prio_arb.hpp` | Strict-priority arbiter (highest priority wins) |
| `TreeArbiter` | `tree_arb.hpp` | Tree-structured arbiter for scalability |

**Key Algorithms**: Round-robin rotation, matrix arbitration (fair with O(1) convergence), strict priority, hierarchical tree arbitration.

---

### 2.3 routers/ — Router Microarchitectures

**Purpose**: Implements the router pipeline models. Each router reads input flits, performs routing computation, allocates VCs and switch bandwidth, traverses the crossbar, and sends flits on output channels.

**Key Classes**:

| Class | File | Role |
|-------|------|------|
| `Router` | `router.hpp` | Abstract base; `ReadInputs()`, `Evaluate()`, `WriteOutputs()`; factory `NewRouter()` |
| `IQRouter` | `iq_router.hpp` | **Primary router** — Input-Queued with virtual channels. Pipeline stages: `_RouteEvaluate`, `_VCAllocEvaluate`, `_SWAllocEvaluate`, `_SwitchEvaluate` + corresponding `Update` methods. Supports speculative switch allocation, NOQ (Next-hop Output Queuing), hold-switch-for-packet. |
| `ChaosRouter` | `chaos_router.hpp` | Chaos routing — adaptive, deflection-based with multi-queue buffers. States: `empty`, `filling`, `full`, `leaving`, `cut_through`, `shared`. |
| `EventRouter` | `event_router.hpp` | Event-driven router; uses `EventNextVCState` for VC tracking, `PriorityArbiter` for arbitration, arrival/transport event queues. |

**Key Mechanisms**: IQ router pipeline (RC→VA→SA→ST), speculative allocation, switch hold, crossbar delay modeling.

---

### 2.4 networks/ — Network Topologies

**Purpose**: Defines network topology classes, each computing its own size (number of routers, channels) and building the router/channel graph.

**Key Classes**:

| Class | File | Role |
|-------|------|------|
| `Network` | `network.hpp` | Abstract base; `_ComputeSize()`, `_BuildNet()`, `WriteFlit()`, `ReadFlit()` |
| `KNCube` | `kncube.hpp` | k-ary n-cube — implements both **mesh** and **torus** topologies |
| `FatTree` | `fattree.hpp` | Fat-tree network topology |
| `CMesh` | `cmesh.hpp` | Concentrated mesh (multiple nodes per router) |
| `FlatFlyOnChip` | `flatfly_onchip.hpp` | Flattened butterfly (on-chip optimized) |
| `Fly` | `fly.hpp` | Butterfly (multi-stage interconnection network) |
| `AnyNet` | `anynet.hpp` | Arbitrary topology specified via file |
| `DragonFly` | `dragonfly.hpp` | Dragonfly network topology |
| `QTree` | `qtree.hpp` | Quad-tree topology |
| `Tree4` | `tree4.hpp` | 4-ary tree topology |

**Supported topologies**: mesh, torus, cmesh, fattree, flatfly_onchip, fly (butterfly), anynet, dragonfly, qtree, tree4.

---

### 2.5 power/ — Power & Activity Monitoring

**Purpose**: Tracks buffer and crossbar activity to estimate dynamic and leakage power using analytical models parameterized by technology files.

**Key Classes**:

| Class | File | Role |
|-------|------|------|
| `Power_Module` | `power_module.hpp` | Top-level power model; `calcChannel()`, `calcBuffer()`, `calcSwitch()`; computes wire, buffer read/write, crossbar, and leakage power. Technology parameters (Vdd, Cg, Rw, etc.) loaded from `techfile.txt`. |
| `SwitchMonitor` | `switch_monitor.hpp` | Records crossbar traversal events (input→output per class); provides activity factors |
| `BufferMonitor` | `buffer_monitor.hpp` | Records buffer read/write events per input per class; provides activity factors |

---

## 3. Key Root-Level Classes

| # | Class | File(s) | Role |
|---|-------|---------|------|
| 1 | `InterconnectInterface` | `interconnect_interface.hpp/cpp` | **Primary entry point**: bridges GPGPU-Sim ↔ BookSim. `Push()` injects packets, `Pop()` retrieves them, `Advance()` steps simulation. Manages boundary/ejection buffers and node ID mapping. |
| 2 | `GPUTrafficManager` | `gputrafficmanager.hpp/cpp` | GPU-specific traffic manager extending `TrafficManager`. Overrides `_GeneratePacket()` to accept `void*` data payloads and subnet routing. Manages `_input_queue` per subnet/node/class. Friend of `InterconnectInterface`. |
| 3 | `TrafficManager` | `trafficmanager.hpp/cpp` | Base traffic manager. Orchestrates injection, network stepping, flit retirement, statistics collection. Maintains `_partial_packets`, `_total_in_flight_flits`, `_buf_states`. Factory: `TrafficManager::New()`. |
| 4 | `BatchTrafficManager` | `batchtrafficmanager.hpp` | Batch-mode traffic manager for closed-loop simulations with fixed batch sizes. |
| 5 | `Flit` | `flit.hpp/cpp` | **Fundamental data unit**. Types: `READ_REQUEST`, `READ_REPLY`, `WRITE_REQUEST`, `WRITE_REPLY`, `ANY_TYPE`. Fields: `vc`, `src`, `dest`, `head`, `tail`, `id`, `pid`, `data`, `la_route_set`. Pool-allocated (`New()`/`Free()`). |
| 6 | `Credit` | `credit.hpp/cpp` | Flow-control token. Contains `set<int> vc` (VCs being freed). Pool-allocated. |
| 7 | `Buffer` | `buffer.hpp/cpp` | Input buffer at a router port; contains a `vector<VC*>` — one VC per virtual channel. Delegates operations to individual `VC` objects. |
| 8 | `BufferState` | `buffer_state.hpp/cpp` | **Downstream buffer state tracker** — models the credit count for the next router's buffers. Contains nested policy hierarchy: `BufferPolicy` → `PrivateBufferPolicy`, `SharedBufferPolicy` → `LimitedShared`, `DynamicLimitedShared`, `ShiftingDynamicLimitedShared`, `FeedbackShared`, `SimpleFeedbackShared`. Methods: `ProcessCredit()`, `SendingFlit()`, `TakeBuffer()`, `IsFullFor()`, `AvailableFor()`. |
| 9 | `VC` | `vc.hpp/cpp` | Virtual Channel state machine. States: `idle` → `routing` → `vc_alloc` → `active`. Contains a `deque<Flit*>` buffer, output port/vc assignment, priority. Priority types: `local_age_based`, `queue_length_based`, `hop_count_based`, `none`. |
| 10 | `Channel<T>` | `channel.hpp` | Template for a pipelined channel with configurable latency. Uses a `_wait_queue` of `(time, data)` pairs. `Send()` → `ReadInputs()` → delay → `WriteOutputs()` → `Receive()`. |
| 11 | `FlitChannel` | `flitchannel.hpp/cpp` | Specialization of `Channel<Flit>` that tracks source/sink router and port, plus per-class activity counters for power modeling. |
| 12 | `OutputSet` | `outputset.hpp/cpp` | Result of routing computation — a set of `{output_port, vc_start, vc_end, priority}` elements. Used by routing functions to express valid output port + VC ranges. |
| 13 | `Configuration` | `config_utils.hpp/cpp` | Key-value config store with string/int/float maps. Supports file parsing (`config.l`/`config.y` lexer/parser), vector fields. |
| 14 | `BookSimConfig` | `booksim_config.hpp/cpp` | Derived from `Configuration`; sets all BookSim default parameters (topology, VCs, buffers, allocators, routing, simulation, power). |
| 15 | `IntersimConfig` | `intersim_config.hpp/cpp` | Derived from `BookSimConfig`; adds GPU-specific parameters: `perfect_icnt`, `fixed_lat_per_hop`, `use_map`, `flit_size`, `input_buffer_size`, `ejection_buffer_size`, `boundary_buffer_size`, `network_count`. |
| 16 | `Module` | `module.hpp/cpp` | Base class for all named, hierarchical simulation modules. Provides `Name()`, `FullName()`, `Error()`, `Debug()`, child management. |
| 17 | `TimedModule` | `timed_module.hpp` | Extends `Module` with `ReadInputs()` / `Evaluate()` / `WriteOutputs()` interface for cycle-based simulation. |
| 18 | `Stats` | `stats.hpp/cpp` | Statistics accumulator: `AddSample()`, `Average()`, `Variance()`, `Min()`, `Max()`, histogram bins. |
| 19 | `TrafficPattern` | `traffic.hpp/cpp` | Abstract traffic destination generator. Subclasses: `UniformRandom`, `BitComp`, `Transpose`, `BitRev`, `Shuffle`, `Tornado`, `Neighbor`, `HotSpot`, `Diagonal`, `Asymmetric`, etc. |
| 20 | `InjectionProcess` | `injection.hpp/cpp` | Controls packet injection timing. `BernoulliInjectionProcess` (Poisson-like), `OnOffInjectionProcess` (bursty). |
| 21 | `PacketReplyInfo` | `packet_reply_info.hpp` | Tracks pending request→reply associations. Pool-allocated. |
| 22 | `PipelineFIFO<T>` | `pipefifo.hpp` | Multi-lane pipeline FIFO with configurable depth; used in ChaosRouter and EventRouter for crossbar/credit pipes. |
| 23 | `PowerConfig` | `booksim_config.hpp` | Configuration for power modeling parameters. |

---

## 4. Representative Snippets

### 4.1 Flit Class Declaration
```cpp
class Flit {
public:
  const static int NUM_FLIT_TYPES = 5;
  enum FlitType { READ_REQUEST=0, READ_REPLY=1, WRITE_REQUEST=2, WRITE_REPLY=3, ANY_TYPE=4 };
  FlitType type;
  int vc, cl;
  bool head, tail;
  int ctime, itime, atime;       // creation, injection, arrival times
  unsigned long long id, pid;     // flit ID, packet ID
  bool record;
  int src, dest, pri, hops;
  mutable int intm, ph;          // intermediate dest, phase (multi-phase routing)
  void* data;                     // payload pointer (e.g., mem_fetch*)
  OutputSet la_route_set;         // lookahead routing result
  static Flit * New();
  void Free();
private:
  static stack<Flit *> _all, _free;  // pool allocator
};
```

### 4.2 VC State Machine
```cpp
class VC : public Module {
public:
  enum eVCState { state_min=0, idle=state_min, routing, vc_alloc, active, state_max=active };
  // idle → routing → vc_alloc → active → (tail departs) → idle
  void AddFlit(Flit *f);
  Flit *RemoveFlit();
  void SetState(eVCState s);
  void Route(tRoutingFunction rf, const Router* router, const Flit* f, int in_channel);
  void SetOutput(int port, int vc);
private:
  deque<Flit *> _buffer;
  eVCState _state;
  OutputSet *_route_set;
  int _out_port, _out_vc;
};
```

### 4.3 InterconnectInterface (GPGPU-Sim Bridge)
```cpp
class InterconnectInterface {
public:
  static InterconnectInterface* New(const char* const config_file);
  virtual void CreateInterconnect(unsigned n_shader, unsigned n_mem);
  virtual void Push(unsigned input_deviceID, unsigned output_deviceID, void* data, unsigned int size);
  virtual void* Pop(unsigned output_deviceID);
  virtual void Advance();
  virtual bool Busy() const;
  virtual bool HasBuffer(unsigned deviceID, unsigned int size) const;
protected:
  vector<vector<vector<_BoundaryBufferItem>>> _boundary_buffer;  // [subnet][node][vc]
  vector<vector<vector<_EjectionBufferItem>>> _ejection_buffer;  // [subnet][node][vc]
  GPUTrafficManager* _traffic_manager;
  vector<Network *> _net;
  map<unsigned, unsigned> _node_map;      // deviceID → icntID
  map<unsigned, unsigned> _reverse_node_map;
};
```

### 4.4 Router Base & IQRouter Pipeline
```cpp
class Router : public TimedModule {
protected:
  int _id, _inputs, _outputs, _classes;
  vector<FlitChannel *> _input_channels, _output_channels;
  vector<CreditChannel *> _input_credits, _output_credits;
  virtual void _InternalStep() = 0;
public:
  static Router *NewRouter(const Configuration& config, Module *parent,
                           const string & name, int id, int inputs, int outputs);
  virtual void ReadInputs() = 0;
  virtual void WriteOutputs() = 0;
};

class IQRouter : public Router {
  // Pipeline stages:
  void _RouteEvaluate();     // RC: compute route for head flits
  void _VCAllocEvaluate();   // VA: allocate output VC
  void _SWHoldEvaluate();    // SA-hold: maintain switch for multi-flit packets
  void _SWAllocEvaluate();   // SA: allocate crossbar switch
  void _SwitchEvaluate();    // ST: traverse crossbar
  // + corresponding _*Update() methods
  Allocator *_vc_allocator, *_sw_allocator, *_spec_sw_allocator;
  vector<Buffer *> _buf;
  vector<BufferState *> _next_buf;
};
```

### 4.5 Allocator Hierarchy
```cpp
class Allocator : public Module {
public:
  struct sRequest { int port, label, in_pri, out_pri; };
  virtual void AddRequest(int in, int out, int label=1, int in_pri=0, int out_pri=0);
  virtual void Allocate() = 0;
  int OutputAssigned(int in) const;
  int InputAssigned(int out) const;
  static Allocator *NewAllocator(Module *parent, const string& name,
                                  const string &alloc_type, int inputs, int outputs,
                                  Configuration const * const config = NULL);
};
// Concrete: DenseAllocator, SparseAllocator, iSLIP_Sparse, Wavefront,
//           SeparableInputFirst, SeparableOutputFirst, PIM, LOA, MaxSizeMatch, SelAlloc
```

---

## 5. Data Flow — Flit Lifecycle

```
GPGPU-Sim Memory System
         │
         ▼
┌─────────────────────────────────┐
│  InterconnectInterface::Push()  │  ← Converts mem_fetch to flits
│  • Maps deviceID → icntID       │
│  • Computes n_flits = size/flit_size
│  • Calls GPUTrafficManager::_GeneratePacket()
│    → Creates Flit objects (head/body/tail)
│    → Pushes to _input_queue[subnet][node][class]
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  GPUTrafficManager::_Step()     │  ← Called by Advance() each cycle
│  1. _Inject(): move flits from  │
│     _input_queue → _partial_packets → network injection channels
│  2. Network::ReadInputs()       │
│  3. Network::Evaluate()         │  ← All routers + channels step
│  4. Network::WriteOutputs()     │
│  5. _RetireFlit() for arrived   │
│     flits → WriteOutBuffer()    │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Inside Each IQRouter (per cycle):
│                                 │
│  ┌──────────┐                   │
│  │ ReadInputs│ Receive flits    │
│  │           │ from input       │
│  │           │ channels         │
│  └────┬─────┘                   │
│       ▼                         │
│  ┌──────────┐                   │
│  │Route Comp│ RC stage:         │
│  │(head flit)│ Compute output   │
│  │          │ port + VC range   │
│  │          │ via tRoutingFunc  │
│  └────┬─────┘                   │
│       ▼                         │
│  ┌──────────┐                   │
│  │VC Alloc  │ VA stage:         │
│  │          │ Allocate output   │
│  │          │ VC from available │
│  │          │ set (iSLIP/etc)   │
│  └────┬─────┘                   │
│       ▼                         │
│  ┌──────────┐                   │
│  │SW Alloc  │ SA stage:         │
│  │          │ Allocate crossbar │
│  │          │ (iSLIP/wavefront) │
│  │          │ + speculative SA  │
│  └────┬─────┘                   │
│       ▼                         │
│  ┌──────────┐                   │
│  │Switch    │ ST stage:         │
│  │Traversal │ Flit crosses the  │
│  │          │ crossbar, placed  │
│  │          │ in output buffer  │
│  └────┬─────┘                   │
│       ▼                         │
│  ┌───────────┐                  │
│  │WriteOutputs│ Send flit on    │
│  │           │ output channel + │
│  │           │ send credits back│
│  └───────────┘                  │
└─────────────┬───────────────────┘
              │  (flit traverses channel with latency)
              ▼
┌─────────────────────────────────┐
│  At Destination Router:         │
│  • Flit ejected to ejection     │
│    channel                      │
│  • TrafficManager::_RetireFlit()│
│    collects statistics          │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  InterconnectInterface          │
│  ::WriteOutBuffer()             │
│  → Transfer2BoundaryBuffer()    │
│  → _boundary_buffer[s][n][vc]   │
│    reassembles packet (waits    │
│    for tail flit)               │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  InterconnectInterface::Pop()   │  ← GPGPU-Sim memory system calls
│  • Round-robin across VCs       │
│  • Returns reassembled void*    │
│    (original mem_fetch pointer) │
└─────────────────────────────────┘
```

### Credit Flow (Reverse Direction)
1. When a downstream router consumes a flit from its input buffer, it sends a `Credit` back upstream.
2. The upstream router's `BufferState::ProcessCredit()` increments the credit count for that VC.
3. During SA, the upstream router checks `BufferState::IsFullFor(vc)` before granting switch allocation.

---

## 6. Configuration Knobs

### 6.1 Topology & Network Structure

| Parameter | Default | Description |
|-----------|---------|-------------|
| `topology` | `"torus"` | Network topology: `torus`, `mesh`, `cmesh`, `fly`, `fattree`, `flatfly_onchip`, `anynet`, `dragonfly`, `qtree`, `tree4` |
| `k` | 8 | Network radix (nodes per dimension) |
| `n` | 2 | Network dimension |
| `c` | 1 | Concentration (nodes per router) |
| `x` / `y` | 8 / 8 | Router grid dimensions |
| `xr` / `yr` | 1 / 1 | Nodes per router in X/Y (when c>1) |
| `subnets` | 1 | Number of independent physical sub-networks |
| `network_count` | 2 | Number of independent interconnection networks (typically 2: shader→mem, mem→shader) |
| `routing_function` | `"none"` | Routing algorithm name (see §12 for full list) |

### 6.2 Router Architecture

| Parameter | Default | Description |
|-----------|---------|-------------|
| `router` | `"iq"` | Router type: `iq` (input-queued), `chaos`, `event` |
| `num_vcs` | 16 | Number of virtual channels per port |
| `vc_buf_size` | 8 | Buffer slots per VC |
| `buf_size` | -1 | Shared buffer size (-1 = unlimited) |
| `buffer_policy` | `"private"` | Buffer sharing: `private`, `shared`, `limited`, `dynamic`, `shifting`, `feedback`, `simplefeedback` |
| `routing_delay` | 1 | Cycles for route computation |
| `vc_alloc_delay` | 1 | Cycles for VC allocation |
| `sw_alloc_delay` | 1 | Cycles for switch allocation |
| `st_prepare_delay` | 0 | Cycles for switch traversal preparation |
| `st_final_delay` | 1 | Cycles for switch traversal completion |
| `credit_delay` | 0 | Additional credit channel delay |
| `input_speedup` | 1 | Input port expansion into crossbar |
| `output_speedup` | 1 | Output port expansion into crossbar |
| `internal_speedup` | 1.0 | Internal clock multiplier |
| `output_buffer_size` | -1 | Output buffer depth (-1 = unlimited) |

### 6.3 Allocation & Arbitration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `vc_allocator` | `"islip"` | VC allocator algorithm: `islip`, `separable_input_first`, `separable_output_first`, `wavefront`, `pim`, `loa`, `maxsize`, `selalloc` |
| `sw_allocator` | `"islip"` | Switch allocator algorithm (same options) |
| `arb_type` | `"round_robin"` | Arbiter type for separable allocators: `round_robin`, `matrix`, `prio`, `tree` |
| `alloc_iters` | 1 | Number of allocator iterations per cycle |
| `speculative` | 0 | Enable speculative switch allocation |
| `spec_check_elig` | 1 | Check VC eligibility during speculation |
| `spec_check_cred` | 1 | Check credit availability during speculation |
| `hold_switch_for_packet` | 0 | Hold switch configuration for entire packet |
| `noq` | 0 | Enable Next-hop Output Queuing |

### 6.4 Flow Control

| Parameter | Default | Description |
|-----------|---------|-------------|
| `wait_for_tail_credit` | 0 | Wait for tail credit before reallocating VC |
| `vc_busy_when_full` | 0 | Mark VCs as busy when no credits available |
| `vc_prioritize_empty` | 0 | Prioritize empty VCs in allocation |
| `vc_shuffle_requests` | 0 | Randomize VC allocation requests for fairness |

### 6.5 GPU-Specific (IntersimConfig)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `perfect_icnt` | 0 | Bypass NoC simulation entirely (zero-latency) |
| `fixed_lat_per_hop` | 0 | Fixed latency per hop (non-zero bypasses detailed simulation) |
| `flit_size` | 32 | Flit size in bytes |
| `input_buffer_size` | 0 | Input injection buffer capacity (0 = default 9) |
| `ejection_buffer_size` | 0 | Ejection buffer capacity (0 = use `vc_buf_size`) |
| `boundary_buffer_size` | 16 | Boundary buffer capacity at interface |
| `use_map` | 1 | Enable SM/memory node mapping |

### 6.6 VC Ranges for Read/Write Separation

| Parameter | Default | Description |
|-----------|---------|-------------|
| `read_request_begin_vc` / `end_vc` | 0 / 5 | VC range for read requests |
| `write_request_begin_vc` / `end_vc` | 2 / 7 | VC range for write requests |
| `read_reply_begin_vc` / `end_vc` | 8 / 13 | VC range for read replies |
| `write_reply_begin_vc` / `end_vc` | 10 / 15 | VC range for write replies |

### 6.7 Traffic & Simulation

| Parameter | Default | Description |
|-----------|---------|-------------|
| `traffic` | `"uniform"` | Traffic pattern for standalone mode |
| `injection_rate` | 0.1 | Injection rate |
| `injection_process` | `"bernoulli"` | Injection process type |
| `packet_size` | 1 | Packet size in flits |
| `sim_type` | `"latency"` | Simulation type: `latency`, `throughput`, `gpgpusim` |
| `deadlock_warn_timeout` | 256 | Cycles before deadlock warning |
| `sample_period` | 1000 | Statistics sampling interval |
| `seed` | 0 | Random seed |

### 6.8 Power

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sim_power` | 0 | Enable power simulation |
| `channel_width` | 128 | Channel width in bits for power model |
| `tech_file` | `""` | Technology parameter file path |

---

## 7. Interactions — How InterSim2 Connects to GPGPU-Sim

### 7.1 Entry Points

The **sole interface** between GPGPU-Sim and InterSim2 is `InterconnectInterface`, accessed via the global pointer `g_icnt_interface` (declared in `globals.hpp`).

**Initialization sequence**:
1. `InterconnectInterface::New(config_file)` — parses the interconnect config file
2. `CreateInterconnect(n_shader, n_mem)` — builds networks, creates `GPUTrafficManager`, initializes routing map, creates boundary/ejection buffers, creates node ID mapping
3. `Init()` — resets traffic manager state

**Per-cycle simulation**:
1. GPGPU-Sim calls `Push(input_deviceID, output_deviceID, data, size)` to inject packets:
   - Converts `mem_fetch*` to `Flit::FlitType` based on memory request type
   - Maps device IDs to internal network IDs via `_node_map`
   - Determines subnet (0 = shader→mem, 1 = mem→shader for dual-subnet configs)
   - Calls `GPUTrafficManager::_GeneratePacket()` to create flits
2. GPGPU-Sim calls `Advance()` → `GPUTrafficManager::_Step()` which:
   - Injects flits from `_input_queue` into the network
   - Steps all networks (routers + channels)
   - Retires arrived flits into `_boundary_buffer`
3. GPGPU-Sim calls `Pop(deviceID)` to retrieve completed packets:
   - Round-robin across VCs in `_boundary_buffer` for the destination node
   - Returns the original `void*` data pointer (e.g., `mem_fetch*`)
4. `HasBuffer(deviceID, size)` — checks injection buffer capacity before `Push()`
5. `Busy()` — returns true if any flits are in-flight or in boundary buffers

### 7.2 Node Mapping
- Device IDs 0 to n_shader-1 = shader cores (SMs)
- Device IDs n_shader to n_shader+n_mem-1 = memory partitions
- These are mapped to internal network node IDs via `_node_map` / `_reverse_node_map`
- With `use_map=1`, the mapping can be customized to match physical placement

### 7.3 Subnet Architecture
- Default `network_count=2`: subnet 0 for shader→memory, subnet 1 for memory→shader
- When `subnets=1`, a single shared network is used for both directions
- Subnet selection in `Push()`: input from shader → subnet 0; input from memory → subnet 1

---

## 8. Terminology

| # | Term | Definition |
|---|------|------------|
| 1 | **Flit** | Flow control unit — the smallest unit of data transfer in the network. A packet is split into one or more flits. |
| 2 | **Packet** | A complete message (e.g., a memory request/reply) composed of head, body, and tail flits. |
| 3 | **Head flit** | First flit of a packet; carries routing info, sets up the path. |
| 4 | **Tail flit** | Last flit of a packet; signals end of packet, releases VC. |
| 5 | **Body flit** | Intermediate flit(s) between head and tail. |
| 6 | **Virtual Channel (VC)** | A logical channel multiplexed over a physical channel. Each VC has its own buffer and state machine. Prevents head-of-line blocking. |
| 7 | **Credit** | Flow-control token sent upstream when a flit is consumed from a downstream buffer; indicates a free buffer slot. |
| 8 | **Credit-based flow control** | Mechanism where a sender tracks downstream buffer availability via credits; sends flit only when credits > 0. |
| 9 | **Wormhole routing** | Routing technique where flits of a packet are pipelined through routers. Head flit reserves the path; body/tail follow. Blocks if downstream buffer is full. |
| 10 | **Virtual Channel (VC) flow control** | Enhancement of wormhole: blocked packets can be bypassed by other packets using different VCs on the same physical channel. |
| 11 | **Dimension-Order Routing (DOR)** | Deterministic routing that traverses dimensions in a fixed order (e.g., X first, then Y). Deadlock-free for meshes. |
| 12 | **XY routing** | DOR for 2D mesh: route in X dimension first, then Y. |
| 13 | **Adaptive routing** | Routing that considers network state (congestion) to choose among multiple valid paths. |
| 14 | **Minimal routing** | Routing that only uses shortest paths (no misrouting). |
| 15 | **Valiant routing** | Non-minimal routing: send packet to a random intermediate node first, then to the destination. Balances load. |
| 16 | **Crossbar** | Switch fabric inside a router that connects input ports to output ports. |
| 17 | **Switch Allocation (SA)** | Process of assigning input→output crossbar connections each cycle. |
| 18 | **VC Allocation (VA)** | Process of assigning an output VC to a head flit that has been routed. |
| 19 | **Route Computation (RC)** | Pipeline stage where the routing function computes the output port and VC range for a head flit. |
| 20 | **Switch Traversal (ST)** | Pipeline stage where the flit crosses the crossbar. |
| 21 | **iSLIP** | Iterative Slip algorithm for switch allocation: round-robin matching with rotating priority pointers. |
| 22 | **Lookahead routing** | Routing computation performed one hop ahead; the current router computes the route for the next router. |
| 23 | **NOQ (Next-hop Output Queuing)** | Optimization where VC allocation at the next hop is pre-computed during routing. |
| 24 | **Speculative allocation** | Performing SA in parallel with VA, speculatively assuming VA will succeed. |
| 25 | **Subnet** | An independent physical network; GPGPU-Sim typically uses 2 subnets (request + reply). |
| 26 | **Concentration** | Multiple nodes connected to a single router (parameter `c`). |
| 27 | **Network radix** | Number of ports per router (parameter `k`). |
| 28 | **Ejection** | Process of removing flits from the network at the destination node. |
| 29 | **Injection** | Process of inserting flits into the network at the source node. |
| 30 | **Boundary buffer** | Buffer at the InterconnectInterface that reassembles packets from flits before delivery to GPGPU-Sim. |
| 31 | **Buffer policy** | Strategy for sharing buffer space among VCs: private, shared, limited shared, feedback-based. |
| 32 | **Activity factor** | Fraction of cycles a component is active; used for power estimation. |

---

## 9. Algorithms & Mechanisms

### 9.1 iSLIP Switch Allocation

**Purpose**: Fair, efficient matching of input ports to output ports in O(N) per iteration.

**Algorithm** (per iteration):
1. **Request**: Each unmatched input sends requests to all desired outputs.
2. **Grant**: Each output uses a round-robin pointer (`_gptrs`) to select one input among requestors.
3. **Accept**: Each input uses a round-robin pointer (`_aptrs`) to select one output among grants.
4. **Update**: Matched outputs advance their grant pointer past the winner (ensures fairness).

Multiple iterations (`alloc_iters`) improve matching quality. After `log(N)` iterations, iSLIP converges to maximum-size matching.

### 9.2 Wavefront Allocation

**Purpose**: Single-pass matching using a diagonal sweep across the NxN request matrix.

**Algorithm**:
1. Start at a diagonal position `(pri, pri)` in the request matrix.
2. Sweep along the diagonal: for each position `(i, j)` where `(i+j) mod N == pri`, if there's a request and neither input `i` nor output `j` is matched, grant it.
3. Advance `_pri` for next cycle.

O(N) time, hardware-friendly, but may not find maximum matching.

### 9.3 Separable Input-First / Output-First Allocation

**Purpose**: Two-phase decomposition using per-port arbiters.

**Input-First**:
1. Each input arbitrates locally among its competing VCs to select one output request.
2. Each output arbitrates among requests that won input arbitration.

**Output-First**:
1. Each output arbitrates locally to select one input.
2. Each input arbitrates among winning requests from output phase.

Arbiter types are pluggable: `round_robin`, `matrix`, `prio`, `tree`.

### 9.4 Routing Algorithms

**Dimension-Order Routing (DOR)**: For mesh/torus topologies. Traverses dimensions in order (X→Y for mesh, with dateline VCs for torus to avoid deadlock).

**XY-YX Adaptive Routing**: At injection, chooses XY or YX order based on credit availability (congestion) at the output ports. Uses separate VC pools for XY and YX routes to prevent deadlock.

**Valiant Routing**: Two-phase: (1) route to a random intermediate node using minimal path, (2) route from intermediate to final destination. Non-minimal but load-balanced.

**Minimal Adaptive Routing**: For meshes — chooses among all minimal paths based on downstream buffer occupancy.

**Nearest Common Ancestor (NCA)**: For tree topologies — route up to the nearest common ancestor, then down to the destination.

**Chaos Routing**: Deflection-based — flits can be misrouted to any available output if the productive output is blocked.

### 9.5 Credit-Based Flow Control

Each output VC buffer has `vc_buf_size` slots. The upstream router tracks available slots via credits:
- **Initial state**: credits = `vc_buf_size` for each downstream VC
- **On flit send**: decrement credit count for target VC via `BufferState::SendingFlit()`
- **On credit receive**: increment credit count via `BufferState::ProcessCredit()`
- **SA check**: `BufferState::IsFullFor(vc)` must be false to allow transmission

Buffer policies (private, shared, feedback) control how buffer space is divided among VCs.

---

## 10. State Machines

### 10.1 VC State Machine (`VC::eVCState`)

```
            ┌──────────────────────────────────────────┐
            │                                          │
            ▼                                          │
    ┌───────────┐  head flit    ┌───────────┐          │
    │   idle    │──arrives─────→│  routing   │          │
    └───────────┘               └─────┬─────┘          │
                                      │ route           │
                                      │ computed        │
                                      ▼                 │
                                ┌───────────┐          │
                                │ vc_alloc  │          │
                                └─────┬─────┘          │
                                      │ output VC       │
                                      │ granted         │
                                      ▼                 │
                                ┌───────────┐          │
                                │  active   │          │
                                └─────┬─────┘          │
                                      │ tail flit       │
                                      │ departs         │
                                      └────────────────┘
```

- **idle**: VC is free, no packet assigned
- **routing**: Head flit received; routing function is computing output port/VC range
- **vc_alloc**: Route computed; requesting an output VC from the VC allocator
- **active**: Output VC granted; transmitting flits through SA → ST → output

### 10.2 ChaosRouter Queue State Machine (`ChaosRouter::eQState`)

```
  empty → filling → full → leaving → empty
                ↓              ↑
           cut_through    shared
```

- **empty**: Queue available for new packet
- **filling**: Head arrived, body flits arriving
- **full**: Complete packet stored
- **leaving**: Packet being drained to output
- **cut_through**: Simultaneous filling and draining
- **shared**: Two partial packets sharing the queue

### 10.3 EventRouter Next-VC State (`EventNextVCState::eNextVCState`)

```
  idle → busy → tail_pending → idle
```

- **idle**: Output VC available for allocation
- **busy**: VC allocated to an active packet
- **tail_pending**: Tail flit sent; waiting for downstream acknowledgment

### 10.4 TrafficManager Simulation State (`TrafficManager::eSimState`)

```
  warming_up → running → draining → done
```

- **warming_up**: Network warming up, statistics not collected
- **running**: Active measurement period
- **draining**: No new injections, waiting for in-flight packets
- **done**: Simulation complete

---

## 11. Error / Edge Cases

### 11.1 Deadlock Detection
- `TrafficManager` maintains `_deadlock_timer` incremented each cycle when no flit is retired
- When `_deadlock_timer > _deadlock_warn_timeout` (default 256), a deadlock warning is issued
- Deadlocks can occur with insufficient VCs for the routing algorithm (e.g., adaptive XY-YX requires ≥2 VCs per class per direction)

### 11.2 Flit Misdelivery
- `GPUTrafficManager::_RetireFlit()` checks `f->dest != dest` for head flits and calls `Error()` if mismatch
- This catches routing function bugs

### 11.3 Buffer Overflow
- `InterconnectInterface::Push()` asserts `HasBuffer()` before injection — caller must check first
- `BufferState::IsFullFor()` prevents flit transmission when downstream buffer is full
- `Buffer::Full()` returns true when occupancy ≥ size; IQRouter checks before buffering

### 11.4 Credit Underflow/Overflow
- `BufferState` asserts `_occupancy <= _size` in `IsFull()`
- Credit counts per VC are tracked in `_vc_occupancy`; assertions prevent negative counts

### 11.5 VC Exhaustion
- If all output VCs are in use (`_in_use_by[vc] >= 0`), new head flits cannot be allocated
- `vc_busy_when_full` option marks VCs as unavailable when they have zero credits
- Can lead to transient stalls but not deadlock if routing algorithm has sufficient VCs

### 11.6 Packet Reassembly
- `_BoundaryBufferItem::PopPacket()` only returns data after tail flit arrives
- If flits arrive out-of-order (bug), reassembly would fail — but in-order delivery is guaranteed per VC

### 11.7 Configuration Errors
- `Configuration::ParseError()` reports parsing failures with line numbers
- Missing or invalid topology/routing combinations cause assertion failures during `InitializeRoutingMap()`

### 11.8 Undefined Packet Types
- `InterconnectInterface::Push()` asserts on unknown `mem_fetch` types (not READ_REQUEST, WRITE_REQUEST, READ_REPLY, WRITE_ACK)

---

## 12. Network Topologies

| Topology | Config Value | Class | File | Description |
|----------|-------------|-------|------|-------------|
| **Mesh** | `"mesh"` | `KNCube` | `kncube.hpp` | k-ary n-dimensional mesh (no wraparound links) |
| **Torus** | `"torus"` | `KNCube` | `kncube.hpp` | k-ary n-dimensional torus (wraparound links) |
| **Concentrated Mesh** | `"cmesh"` | `CMesh` | `cmesh.hpp` | Mesh with c>1 nodes per router; reduced router count |
| **Fat Tree** | `"fattree"` | `FatTree` | `fattree.hpp` | Multi-stage fat tree with increasing bandwidth toward root |
| **Flattened Butterfly** | `"flatfly_onchip"` | `FlatFlyOnChip` | `flatfly_onchip.hpp` | Flattened butterfly optimized for on-chip networks; high radix |
| **Butterfly** | `"fly"` | `Fly` | `fly.hpp` | Multi-stage butterfly (Banyan) network |
| **Dragonfly** | `"dragonfly"` | `DragonFly` | `dragonfly.hpp` | Hierarchical topology: local groups with global links |
| **Quad Tree** | `"qtree"` | `QTree` | `qtree.hpp` | Quaternary tree topology |
| **4-ary Tree** | `"tree4"` | `Tree4` | `tree4.hpp` | 4-ary bidirectional tree |
| **Arbitrary** | `"anynet"` | `AnyNet` | `anynet.hpp` | User-defined topology from adjacency file |

### Routing Functions per Topology

| Topology | Available Routing Functions |
|----------|---------------------------|
| Mesh | `dor_mesh`, `dim_order_mesh`, `dim_order_ni_mesh`, `dim_order_pni_mesh`, `xy_yx_mesh`, `adaptive_xy_yx_mesh`, `romm_mesh`, `romm_ni_mesh`, `min_adapt_mesh`, `planar_adapt_mesh`, `valiant_mesh`, `chaos_mesh` |
| Torus | `dim_order_torus`, `dim_order_ni_torus`, `dim_order_bal_torus`, `min_adapt_torus`, `valiant_torus`, `valiant_ni_torus`, `chaos_torus` |
| Fat Tree | `nca_fattree`, `anca_fattree` |
| Butterfly | `dest_tag_fly` |
| Quad Tree | `nca_qtree` |
| Tree4 | `nca_tree4`, `anca_tree4` |
| CMesh | Uses mesh routing functions with concentration mapping |
| FlatFly | Has own routing registered in `flatfly_onchip.cpp` |
| Dragonfly | Has own routing registered in `dragonfly.cpp` |

---

## Appendix: File Listing

### Root Level (36 files)
```
interconnect_interface.hpp/cpp   gputrafficmanager.hpp/cpp
trafficmanager.hpp/cpp           batchtrafficmanager.hpp/cpp
flit.hpp/cpp                     credit.hpp/cpp
buffer.hpp/cpp                   buffer_state.hpp/cpp
vc.hpp/cpp                       channel.hpp
flitchannel.hpp/cpp              outputset.hpp/cpp
routefunc.hpp/cpp                config_utils.hpp/cpp
booksim.hpp                      booksim_config.hpp/cpp
intersim_config.hpp/cpp          globals.hpp
module.hpp/cpp                   timed_module.hpp
stats.hpp/cpp                    traffic.hpp/cpp
injection.hpp/cpp                packet_reply_info.hpp/cpp
pipefifo.hpp                     misc_utils.hpp/cpp
random_utils.hpp                 rng.c/rng-double.c
rng_wrapper.cpp/rng_double_wrapper.cpp
main.cpp                         config.l/config.y
```

### allocators/ (10 classes, 18 files)
### arbiters/ (5 classes, 10 files)
### routers/ (4 classes, 8 files)
### networks/ (10 classes, 20 files)
### power/ (3 classes, 7 files including techfile.txt)
