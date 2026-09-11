# pyright: reportUnusedExpression=false
# ruff: disable[B018]
#%%
import math
from itertools import product

import pandas as pd


# Round to the most significant decimal only when displaying floats < 10
def float_fmt(x):
    if x == 0:
        return "0"
    ax = abs(x)
    if ax >= 100:
        return f"{x:.0f}"
    if ax >= 10:
        return f"{x:.1f}"
    return f"{x:.2g}"

pd.set_option("display.float_format", float_fmt)

# pd.set_option("display.float_format", "{:g}".format)

# pd.set_option("display.max_rows", None)
# pd.set_option("display.max_columns", None)

# %% [markdown]
# # Hash/Graph-Based Challenge Notebook
#
# ## Challenge Goal
#
# 1. Generate a directed graph.
#
# 2. Find 16-circuits that start with a specified initial edge index in it.
#
# 3. Hash the edge indexes of the circuits and match bits against a target hash.
#
# 4. Keep generating graphs until a hash is found.
#
#
# The graph depends on the recipient-issued token, the sender-supplied payload and timestamp, and the sender-supplied first edge index of the 16-circuits being hashed.
#
# Circuits must not pass through a node more than once, but we ignore this for modeling purposes.
#
# ## Difficulty Toggles
#
# The difficulty is set by a mix of:
#
# 1. The number of bits to match `b`. This dictates the amount of random hashing needed to find a match.
#%%

def get_num_hashes(num_bits: int):
    return 2**num_bits

#%%
# 2. `gen_edge()` memory use and random work, modeled using `S`, the base mem size, `m`, the maximum number of random read operations on the buffer, and `p`, the mean number of uint64 read operations on it. This buffer is designed to fit and stay in a CPU L1 cache during graph gen, and be too large to fit in GPU registers at mid/hard levels. Random edges also depend on co-edges to serialize and decoalesce GPU warps even more. The model ignores those for simplicity.
#
# 3. The graph size, modeled by `n` and `d`. These dictate the maximum number of graph nodes (`N = 2^n`) and the exact number of edges (`E = d * 2^n`), so affects graph generation and traversal speed. The actual number of nodes is close enough to the maximum for small densities so we treat it as equal.
#%%

def get_num_nodes(graph_size: int):
    return 2**graph_size

def get_num_edges(density: float, graph_size: int):
    return math.ceil(density * 2**graph_size)

#%%
# 4. The circuit length, which stays fixed at `L = 16` to keep the wire format length at exactly `16 * 4 = 64` bytes.
#
# Finding circuits inside the graph is not possible without first generating its edges, and there are few enough circuits that skipping hard nodes is not a reasonable option.
#
#
# ## Number of Graphs
#
# The expected number of directed 16-circuits `C` that go through a fixed initial edge is:
#
#     C = d^L / E = d^16 / (d * 2^n) = d^15 / 2^n
#
# This gives the expected number of hashes per graph.
#
# A challenge typically needs `2^b` hashes to find a match, so the expected number of graphs to generate is:
#
#     G = 2^b / C = 2^(b + n) / d^15
#
# It follows that:
#
#     d = (2^(b + n) / G)^(1/15)
#     C = 2^b / G
#%%

def get_num_graphs(num_bits: int, graph_size: int, density: float):
    return 2**(num_bits + graph_size) / density**15

def get_density(num_bits: int, graph_size: int, num_graphs: float):
    return (2**(num_bits + graph_size) / num_graphs)**(1/15)

#%%
# ## Performance Assumptions
#
# The modeled device is a mid-range mobile phone in 2026. These typically have:
#
# * 4 big cores that are actually useful. We ignore the smaller ones, since they don't contribute much to the challenge in practice even if they get used.
#
# * 64 kB of private L1 per core, with a ~8 GB/s/core memory throughput, of which only half (32) kB is used to cache data.
#
# * 256 kB of private L2 per core, with a ~2 GB/s/core memory throughput.
#
# * 2 MB of L3 shared among the cores, with a ~.6 GB/s/core memory throughput.
#
# * 1 GB of RAM shared among the cores, with a ~.2 GB/s/core memory throughput.
#
# Memory access patterns are deliberately designed to be random and cause cache misses, so these throughputs are much lower than their theoretical maximums.
#
# The 1 GB RAM limit comes from the fact that mobile OSes like Android trigger an immediate OutOfMemory (OOM) kill or force the system into zRAM swapping, so the practical RAM limit that an app can allocate is 1 GB.
#
# Practically, the challenges are intended so that the whole graph fit in L3, with edge generation done in L1/L2. The RAM numbers matter to get a sense of the performance of levels intended for future proofing.
#
# We also model a high-end phone and a server for comparison.
#%%

KB = 1_024
MB = 1_048_576
GB = 1_073_741_824
GiB_s = 1_000_000_000

PROFILES = {
    "phone_mid": {
        "cores": 4,
        "L1": 32 * KB,
        "L2": 256 * KB,
        "L3": 2 * MB,
        "RAM": 1 * GB,
        "L3_rand": 10 * GiB_s,
        "RAM_rand": 1 * GiB_s,
        "L3_agg": 80 * GiB_s,
        "RAM_agg": 10 * GiB_s,
    },
    "phone_high": {
        "cores": 8,
        "L1": 32 * KB,
        "L2": 512 * KB,
        "L3": 8 * MB,
        "RAM": 1 * GB,
        "L3_rand": 12 * GiB_s,
        "RAM_rand": 1.5 * GiB_s,
        "L3_agg": 160 * GiB_s,
        "RAM_agg": 20 * GiB_s,
    },
    "server_shared": {
        "cores": 8,
        "L1": 32 * KB,
        "L2": 256 * KB,
        "L3": 4 * MB,
        "RAM": 8 * GB,
        "L3_rand": 6 * GiB_s,
        "RAM_rand": 0.8 * GiB_s,
        "L3_agg": 40 * GiB_s,
        "RAM_agg": 8 * GiB_s,
    },
    "server_dedicated": {
        "cores": 128,
        "L1": 32 * KB,
        "L2": 1 * MB,
        "L3": 512 * MB,
        "RAM": 512 * GB,
        "L3_rand": 20 * GiB_s,
        "RAM_rand": 2 * GiB_s,
        "L3_agg": 2_400 * GiB_s,
        "RAM_agg": 300 * GiB_s,
    }
}

def L1_seq_write_ms(bytes: int, profile: str):
    cores = PROFILES[profile]["cores"]
    return bytes / (32 * GiB_s * cores / 1000)

def L1_rand_read_ms(bytes: int, profile: str):
    cores = PROFILES[profile]["cores"]
    return bytes / (8 * GiB_s * cores / 1000)

def L1_rand_write_ms(bytes: int, profile: str):
    cores = PROFILES[profile]["cores"]
    return bytes / (6 * GiB_s * cores / 1000)

def L2_seq_read_ms(bytes: int, profile: str):
    cores = PROFILES[profile]["cores"]
    return bytes / (16 * GiB_s * cores / 1000)

def L2_rand_read_ms(bytes: int, profile: str):
    cores = PROFILES[profile]["cores"]
    return bytes / (2 * GiB_s * cores / 1000)

def L2_rand_write_ms(bytes: int, profile: str):
    cores = PROFILES[profile]["cores"]
    return bytes / (1.5 * GiB_s * cores / 1000)

def L3_seq_read_ms(bytes: int, profile: str):
    rand_bw = 2 * PROFILES[profile]["L3_rand"]
    agg_bw = PROFILES[profile]["L3_agg"]
    cores = PROFILES[profile]["cores"]
    bw = min(rand_bw * cores, agg_bw) / 1000
    return bytes / bw

def L3_seq_write_ms(bytes: int, profile: str):
    rand_bw = 1.5 * PROFILES[profile]["L3_rand"]
    agg_bw = PROFILES[profile]["L3_agg"]
    cores = PROFILES[profile]["cores"]
    bw = min(rand_bw * cores, agg_bw) / 1000
    return bytes / bw

def L3_rand_read_ms(bytes: int, profile: str):
    rand_bw = PROFILES[profile]["L3_rand"]
    agg_bw = PROFILES[profile]["L3_agg"]
    cores = PROFILES[profile]["cores"]
    bw = min(rand_bw * cores, agg_bw) / 1000
    return bytes / bw

def L3_rand_write_ms(bytes: int, profile: str):
    rand_bw = .75 * PROFILES[profile]["L3_rand"]
    agg_bw = PROFILES[profile]["L3_agg"]
    cores = PROFILES[profile]["cores"]
    bw = min(rand_bw * cores, agg_bw) / 1000
    return bytes / bw

def RAM_seq_read_ms(bytes: int, profile: str):
    rand_bw = 1.5 * PROFILES[profile]["RAM_rand"]
    agg_bw = PROFILES[profile]["RAM_agg"]
    cores = PROFILES[profile]["cores"]
    bw = min(rand_bw * cores, agg_bw) / 1000
    return bytes / bw

def RAM_seq_write_ms(bytes: int, profile: str):
    rand_bw = 1.125 * PROFILES[profile]["RAM_rand"]
    agg_bw = PROFILES[profile]["RAM_agg"]
    cores = PROFILES[profile]["cores"]
    bw = min(rand_bw * cores, agg_bw) / 1000
    return bytes / bw

def RAM_rand_read_ms(bytes: int, profile: str):
    rand_bw = PROFILES[profile]["RAM_rand"]
    agg_bw = PROFILES[profile]["RAM_agg"]
    cores = PROFILES[profile]["cores"]
    bw = min(rand_bw * cores, agg_bw) / 1000
    return bytes / bw

def RAM_rand_write_ms(bytes: int, profile: str):
    rand_bw = .75 * PROFILES[profile]["RAM_rand"]
    agg_bw = PROFILES[profile]["RAM_agg"]
    cores = PROFILES[profile]["cores"]
    bw = min(rand_bw * cores, agg_bw) / 1000
    return bytes / bw

def priv_rand_read_ms(bytes: int, working_set_bytes: int, profile: str):
    if working_set_bytes <= PROFILES[profile]["L1"]:
        return L1_rand_read_ms(bytes, profile)
    elif working_set_bytes <= PROFILES[profile]["L2"]:
        return L2_rand_read_ms(bytes, profile)
    else:
        return float('inf')

def priv_rand_write_ms(bytes: int, working_set_bytes: int, profile: str):
    if working_set_bytes <= PROFILES[profile]["L1"]:
        return L1_rand_write_ms(bytes, profile)
    elif working_set_bytes <= PROFILES[profile]["L2"]:
        return L2_rand_write_ms(bytes, profile)
    else:
        return float('inf')

def shared_rand_read_ms(bytes: int, working_set_bytes: int, profile: str):
    if working_set_bytes <= PROFILES[profile]["L3"]:
        return L3_rand_read_ms(bytes, profile)
    elif working_set_bytes <= PROFILES[profile]["RAM"]:
        return RAM_rand_read_ms(bytes, profile)
    else:
        return float('inf')

def shared_rand_write_ms(bytes: int, working_set_bytes: int, profile: str):
    if working_set_bytes <= PROFILES[profile]["L3"]:
        return L3_rand_write_ms(bytes, profile)
    elif working_set_bytes <= PROFILES[profile]["RAM"]:
        return RAM_rand_write_ms(bytes, profile)
    else:
        return float('inf')

#%%
# ## Difficulty Milestones
#
# Level 0 is intended for known senders, and Levels 1-3 are designed for normal traffic levels, so are deliberately simple.
#
# Levels 4-7 are intended to repel a DDoS in the next 10 years.
#
# Levels 8-11 are intended to repel a DDoS in 10-20 years.
#
# Levels 12-15 are intended to repel a DDoS in 21+ years.
#
# The challenge is nominally about finding a hash, but the difficulty lever is memory use rather than raw computations.
#
# Building the graph requires random reads on a small-ish buffer. That invites maintaining a copy of that buffer per core to avoid serializing concurrent random reads. The concurrent random writes in two hash maps are not avoidable. Edges get generated as idx -> (src, dst) so there is no plausible shortcut to avoid building most or all of the graph.
#
# Building the filter table requires concurrent random reads on the graph table with concurrent writes in a shared hashmap. The initial node defines the graph, so there is no possible exploring different initial nodes in parallel. At best, the parallelization involves assigning unexplored nodes to new threads as nodes get discovered from the initial node.
#
# The threat level `l` rises like the log2 of the number of successful challenges inside a time window, with the exact growth curve at the app's discretion. What is more, there are cheap pre-flight checks before even verifying the challenge  that discard random traffic.
#
# In the interest of estimating the difficulty needs, an attacker might need to sustain 1k successful level 3 challenges per second for the recipient to even set the threat level to 4 and require level 4 challenges, and would need to sustain perhaps 10k level 7 challenges per second to maintain it at a level 7 for any extended period.
#
# Level 7 is intended to be comfortably solvable (under 250ms) by a mid-range mobile phone, and prohibitively expensive to sustain for an attacker owing to the memory use. To wit, hacked IoT devices cannot complete challenges that requires non-trivial amounts of memory and computations, and hacked servers that complete such challenges repeatedly tend to get promptly shut down.
#
#
# ## Resolution Strategy
#
# The optimal strategy to minimize memory use is a meet-in-the-middle strategy from the starting edge. It involves a generation step to generate the graph. This gets followed by a path generation step where forward paths get built, and matched against backward paths.
#
# ### Graph Generate
#
# `gen_edge(idx)->(src, dst)` gets called over `E`. We need forward and backward hash maps:
#
#     forward[src] = list((dst, idx))
#     backward[dst] = list((src, idx))
#
# The nominal data per edge is 12 bytes, but the two hashmaps and the lists in them add pointers and other overhead. 36 bytes in total per edge is a more realistic estimate: 4 key + 4 pointer to list + 2 hash map overhead, plus 8 data, is 18 bytes in each direction.
#
# This implies `36 * d * 2^n` of L3+ write traffic just to store the graph.
#
# If we assume a 0.75 load factor for zeroing at initialization, we need to add an initial extra `2 * 8 * 2^n / .75` of L3+ write traffic, so `16 * 2^n / .75`. This could be halved for smaller graphs that use 16-bit indexes instead of 32-bit ones, but we're not modeling those.
#
# Using CSR is not a good option. It would add overhead to offer a smaller memory footprint, with very little benefit since we'd end up sorting the whole set to optimize looking for the circuits that pass through a specific node. Plus, a hashmap is still needed to build it\, so the memory reduction is not that substantial. It doesn't pay for itself, so we skip it.
#
# Head-Next Array (Forward Star) is another option to reduce the memory use per direction. It comes at the cost of increasing the random cache‑line traffic for path expansions because the adjacency entries are then not contiguous, so we skip it too.
#
# Indexed arrays could reduce pointer chasing, but adds initialization overhead and complexity when the initial memory allotment overflows. An attacker might use indexed arrays as an optimization. Hash maps are the better choice for our modeling purposes.
#
# The total gen L3+ write traffic to store the graph is therefore:
#
#     36 * d * 2^n + 16 * 2^n / .75
#%%

def get_graph_writes_bytes(density: float, graph_size: int):
    return math.ceil((36 * density + 16 / .75) * 2**graph_size)

def get_graph_writes_ms(bytes: int, profile: str):
    return shared_rand_write_ms(bytes, bytes, profile)

#%%
# In addition to this, generating each edge requires making up to `m` random reads of a buffer of size `s` into L1. It gets reused as is from an edge gen call to the next, so it will almost certainly reside in L2 if it gets evicted from L1---which it should not. We need to add a mean of `p * 64` bytes of extra L1+ read traffic, and an equivalent amount of writes for the intermediary results as the computation moves forward.
#
# The total edge gen L1+ random read and write traffic (with the two counted separately) is thus:
#
#     p * 64 * d * 2^n
#
# Where this actually lives depends on the maximum number of copies m.
#%%

def get_buffer_bytes(mean_ops: float, density: float, graph_size: int):
    return 64 * mean_ops * density * 2**graph_size

def get_buffer_read_ms(bytes: int, profile: str):
    return L1_rand_read_ms(bytes, profile)

def get_buffer_write_ms(bytes: int, profile: str):
    return L1_rand_write_ms(bytes, profile)

#%%
# ### Path Expansions
#
# The number of final paths of length i in a direction is d^i. The initial edge provides the first step in one direction, so our two directions require:
#
#     R_f = sum(0..6, d^i) = (d^7 - 1) / (d - 1)
#     R_b = sum(0..7, d^i) = (d^8 - 1) / (d - 1)
#
# We therefore need `R_f + R_b` reads worth of random L3+ BW traffic. Each read fetches 64 B owing to how cache lines work, which we count twice due to pointer chasing. We then add a 2x probe factor to keep things simple and conservative.
#
# That gives us a L3+ random read term total of:
#
#     256 * (d^8 + d^7 - 2) / (d - 1)
#%%

def get_forward_reads_bytes(density: float):
    return math.ceil(256 * (density**7 - 1) / (density - 1))

def get_backward_reads_bytes(density: float):
    return math.ceil(256 * (density**8 - 1) / (density - 1))

def get_graph_reads_ms(reads_bytes: int, graph_bytes: int, profile: str):
    return shared_rand_read_ms(reads_bytes, graph_bytes, profile)

#%%
# The most memory efficient way to expand the `d^7` partial forward paths is a DSF. It requires writing `d^7` paths of L3+ BW traffic, plus L1-related stack push-pop traffic that is negligible in comparison.
#
# Each of these `d^7` writes adds `8 * 4 B = 32` bytes to avoid random L3+ read traffic when checking for duplicate nodes inside the paths, plus 32 bytes for the edge indexes to avoid random L3+ read traffic when hashing, plus a lump 8 bytes estimate for the hash table. So `72 * d^7` bytes of writes in total. We apply the same `1/.75` factor as earlier for zeroing, or `96 * d^7` bytes in total. We could add a further coherence factor to account for concurrent writes on that table, but this write term is minor compared to the reads, so we ignore it for simplicity. The `8 * 4 B` numbers can be halved for small graphs.
#
# The total filter L3+ write traffic term is thus:
#
#     96 * d^7
#%%

def get_filter_writes_bytes(density: float):
    return math.ceil(96 * density**7)

def get_filter_writes_ms(filter_bytes: int, profile: str):
    return shared_rand_write_ms(filter_bytes, filter_bytes, profile)

#%%
# We can use the paths in the forward direction as a filter when doing the work in the backward direction to skip L3+ writes. We can then hash the whole path directly for good measure, which adds extra L1 traffic but for our purposes is free compared to the L3+ memory traffic. We model a small hash contribution for lower levels, but memory use quickly dominates it.
#%%

def get_hash_ms(num_hashes: int, profile: str):
    # X25519 is paired with SHA-512 (see Security). Not all phones have hardware
    # acceleration, and not all libraries actually use it when it's available.
    cores = PROFILES[profile]["cores"]
    per_hash_ms = 0.0005              # would be .0001 with acceleration
    return num_hashes * per_hash_ms / cores

#%%
# For each backward path ending at a node, the expected number of forward paths with the same node is `d^7/2^n`. We do this `d^8` times, so that is `d^15/2^n` in total reads on the filter table to do the joins. Each reads exactly 64 bytes of data, so this adds `64 * d^15/2^n` bytes of L3+ read traffic in total.
#
# We also need to locate that hash bucket. We do this the same number of times, so `d^8`. That adds 64 bytes (one cache line) of reads with each look-up. There's a probe factor to add, since not every look-up will be successful. We simply multiply by 3 as a conservative estimate, for a final 192 * d^8.
#
# The total filter L3+ read traffic term is thus:
#
#     192 * d^8 + 64 * d^15/2^n
#
# If the combined graph and filter size is too large to fit in L3, the modeling assumes the CPU will evict the graph to RAM and try to keep the filter in L3.
#%%

def get_filter_reads_bytes(density: float, graph_size: int):
    return math.ceil(192 * density**8 + 64 * density**15 / 2**graph_size)

def get_filter_reads_ms(reads_bytes: int, filter_bytes: int, profile: str):
    return shared_rand_read_ms(reads_bytes, filter_bytes, profile)

#%%
# The L1 traffic in this step is negligible compared to the L3+ traffic, so we can safely ignore it.
#%%

def k(value: int):
    return value / 1_000

def m(value: int):
    return value / 1_000_000

def kb(bytes: int):
    return bytes / KB

def mb(bytes: int):
    return bytes / MB

def gb(bytes: int):
    return bytes / GB

#%%
# ## Graph Generation speeds
#%%

def gen_record(l: int, b: int, n: int, d: float, s: int, m: int, p: float, profile: str):
    level       = l
    num_bits    = b
    graph_size  = n
    density     = d
    buffer      = s
    max_ops     = m
    mean_ops     = p

    num_hashes  = get_num_hashes(num_bits)
    num_nodes   = get_num_nodes(graph_size)
    num_graphs  = get_num_graphs(num_bits, graph_size, density)
    num_edges   = get_num_edges(density, graph_size)

    full_graphs = math.ceil(num_graphs)

    ops_bytes           = get_buffer_bytes(mean_ops, density, graph_size)
    ops_ms              = get_buffer_read_ms(ops_bytes, profile) \
                        + get_buffer_write_ms(ops_bytes, profile)

    graph_bytes         = get_graph_writes_bytes(density, graph_size)
    graph_writes_ms     = get_graph_writes_ms(graph_bytes, profile)

    forward_reads_bytes   = get_forward_reads_bytes(density)
    filter_bytes        = get_filter_writes_bytes(density)
    backward_reads_bytes   = get_backward_reads_bytes(density)
    filter_reads_bytes  = get_filter_reads_bytes(density, graph_size)

    total_bytes         = graph_bytes + filter_bytes

    forward_reads_ms      = get_graph_reads_ms(forward_reads_bytes, total_bytes, profile)
    backward_reads_ms      = get_graph_reads_ms(backward_reads_bytes, total_bytes, profile)
    filter_writes_ms    = get_filter_writes_ms(filter_bytes, profile)
    filter_reads_ms     = get_filter_reads_ms(filter_reads_bytes, filter_bytes, profile)

    build_ms    = full_graphs * (ops_ms + graph_writes_ms)
    filter_ms   = full_graphs * (forward_reads_ms + filter_writes_ms)
    join_ms     = num_graphs * (backward_reads_ms + filter_reads_ms)
    hash_ms     = get_hash_ms(num_hashes, profile)
    total_ms    = build_ms + filter_ms + join_ms + hash_ms

    total_writes_bytes = full_graphs * (graph_bytes + filter_bytes)
    total_reads_bytes = (full_graphs * (ops_bytes + forward_reads_bytes)
                    + num_graphs * (backward_reads_bytes + filter_reads_bytes))

    yield {
        "level": level,

        "num_bits": num_bits,
        "graph_size": graph_size,
        "density": density,

        "num_hashes": num_hashes,
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "num_graphs": num_graphs,

        "buffer": buffer,
        "max_ops": max_ops,
        "mean_ops": mean_ops,

        "ops_bytes": ops_bytes,
        "ops_bytes_mb": mb(ops_bytes),
        "ops_ms": ops_ms,

        "graph_bytes": graph_bytes,
        "graph_bytes_mb": mb(graph_bytes),
        "graph_writes_ms": graph_writes_ms,

        "forward_reads_bytes": forward_reads_bytes,
        "forward_reads_bytes_mb": mb(forward_reads_bytes),
        "forward_reads_ms": forward_reads_ms,

        "filter_bytes": filter_bytes,
        "filter_bytes_mb": mb(filter_bytes),
        "filter_writes_ms": filter_writes_ms,

        "backward_reads_bytes": backward_reads_bytes,
        "backward_reads_bytes_mb": mb(backward_reads_bytes),
        "backward_reads_ms": backward_reads_ms,

        "filter_reads_bytes": filter_reads_bytes,
        "filter_reads_bytes_mb": mb(filter_reads_bytes),
        "filter_reads_ms": filter_reads_ms,

        "build_ms": build_ms,
        "filter_ms": filter_ms,
        "join_ms": join_ms,
        "hash_ms": hash_ms,

        "total_writes_bytes": total_writes_bytes,
        "total_writes_bytes_mb": mb(total_writes_bytes),
        "total_reads_bytes": total_reads_bytes,
        "total_reads_bytes_mb": mb(total_reads_bytes),
        "total_ms": total_ms,
    }

def gen_all_records(bracket: range, profile: str):
    level_values = {}
    for level in range(16):
        level_values[level] = {
            "num_bits": [
                12 + math.ceil(8 * (level / 15)**.2)
            ],
            "graph_size": [
                8 + math.ceil(12 * (level / 15)**.2)
            ],
            "num_graphs": [
                .1 * .8**(level)
            ],
            "buffer": [
                128 * 2**math.ceil(level / 8)
            ],
            "max_ops": [
                2**math.floor(level / 2)
            ],
            "mean_ops" : [
                math.ceil((level + 1) / 4)
                # 1 + math.ceil(math.sqrt(level))
            ]
        }

    for level, values in level_values.items():
        if level not in bracket:
            continue
        for l, b, n, g, s, m, p in product(
            {level},
            set(values["num_bits"]),
            set(values["graph_size"]),
            set(values["num_graphs"]),
            set(values["buffer"]),
            set(values["max_ops"]),
            set(values["mean_ops"]),
        ):
            d = get_density(b, n, g)
            # p = 1
            yield from gen_record(l, b, n, d, s, m, p, profile)


params = [
    "level", "num_bits", "graph_size", "density", "num_graphs",
    "buffer", "max_ops", "mean_ops",
    # "num_nodes", "num_edges",
    # "num_hashes",
]
components = [
    # "max_bytes",
    # "ops_bytes_mb",
    "graph_bytes_mb",
    "filter_bytes_mb",
    "forward_reads_bytes_mb",
    "filter_reads_bytes_mb", "backward_reads_bytes_mb",
    "build_ms", "filter_ms", "join_ms", "hash_ms",
    "total_writes_bytes_mb", "total_reads_bytes_mb",
    "total_ms"
]

df = pd.DataFrame(gen_all_records(range(16),
    "phone_mid"
    # "phone_high"
    # "server_shared"
    # "server_dedicated"
))
df = df[params + components]
df = df.sort_values(by=["level"], ascending=[True]) # type: ignore
df

# 1. GPU-breaking does not require large L1 copies
#
# A simpler gen_edge() can still be GPU-hostile if it forces:
#
# per-thread random reads from a buffer larger than GPU L2
#
# variable number of reads per edge
#
# co-edge dependencies
#
# irregular control flow
#
# So replacing the copy/edit/reduce with just a few random 4-byte reads from a large shared buffer is probably enough to wreck GPU warp efficiency. That’s worth testing.
