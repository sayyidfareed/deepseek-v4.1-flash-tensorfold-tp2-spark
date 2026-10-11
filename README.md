# Fareed's DeepSeek V4.1 Flash dual-Spark recipe

A pinned, community-maintained TensorFold TP2 serving recipe for two NVIDIA GB10
systems (DGX Spark / compatible GX10). This is a serving recipe, not a new model
or quantization. The weights remain DeepSeek V4.1 Flash, quantized by Mia-AiLab
as EXL3 2.9 bpw. The engine and original recipe are Bertholomus's work on TensorFold.

**v0.1.0 is a source-only preview.** The combined configuration has run on our
pair, but this public checkout has not undergone a separate clean-machine
installation. No model weights, CUDA binaries, private chat data, credentials,
or machine configuration are distributed. Engine PRs and remaining review gates
are listed in [UPSTREAM.md](UPSTREAM.md).

## Accepted configuration

- Two GB10 nodes, tensor parallelism 2; 8 active slots and 16 verification rows.
- Shared token pool: 1,048,576 tokens, not that amount per stream.
- GPU sampling candidates enabled on both ranks; original sampler retained as fallback.
- Temperature 1.0, top-p 0.95, top-k 20; client overrides remain supported.
- Replay-floor fix enabled; adaptive 4K prefill disabled.
- Native default output limit 32,768 tokens. Reserve less for many long histories:
  eight 102,400-token prompts plus 32,768 output tokens each exceed the shared pool.
- Automatic tools and ordinary streaming tested. Required/named tool choice and
  strict JSON-schema output remain unsupported; this is not full OpenAI API parity.
- Long prompt alignment repair included; direct-I/O correction changes a test only.

The public `qualified_here` field remains false: successful checks do not establish
all capabilities, every prompt length, or every eight-user workload. Extra work
queues when active slots or shared memory reservations are exhausted.

## What changed

| Change | Purpose |
|---|---|
| Configurable RDMA GID and negotiated endpoint MTU | Bring up the native transport on non-default fabric settings |
| Retained-cache reservation and growth relocation | Prevent continuation growth from overwriting another retained prefix |
| Opt-in GPU sampling candidates | Reduce candidate transfer/selection work while retaining host sampling |
| Profiling counter initialization and candidate count widening | Correct supporting runtime bookkeeping and integer-width behavior |
| Even prompt index block strides | Keep VIS pointers aligned without an extra scratch buffer or copy |
| Buffered reference descriptor in the direct-I/O test | Make the reference actually buffered; preserve all assertions |

The combined patch is pinned and checksum-checked in `lock.json`. Rejected 4K
prefill experiments and diagnostic patches are deliberately absent.

## Measurements and limits

The historical matched API comparison used the same two-node system, EXL3 2.9 bpw,
1M shared pool, 8 slots, 16 verification rows and temperature 1.0/top-p .95/top-k 20
for sampled workloads; greedy set B used temperature 0. Results are medians of
three repetitions. R2 already includes our cache and transport fixes: it is **not
unmodified upstream**.

| Workload | R2 | GPU candidate | Difference |
|---|---:|---:|---:|
| Sampled C1 short-prompt batch, including prefill | 69.65 tok/s | 72.63 tok/s | +4.3% |
| Sampled C8 aggregate, including prefill | 114.20 tok/s | 116.54 tok/s | +2.0% |
| Greedy code decode | 101.04 tok/s | 101.31 tok/s | +0.3% |
| Greedy prose decode | 62.57 tok/s | 62.77 tok/s | +0.3% |
| Greedy structured decode | 141.04 tok/s | 142.87 tok/s | +1.3% |

These small gains are not a broad speed-lead claim. Other repeated native on/off
runs were effectively equal, and unaffected greedy paths also varied. No new
throughput benchmark is claimed for the alignment fix. See the public
[evidence](evidence/) and [validation status](VALIDATION.md).

Cold exact-length completions of 72,149, 72,150 and 72,151 tokens all returned the
correct synthetic marker after the alignment fix, with zero cached tokens and
roughly 30 seconds end-to-end each. This is a boundary regression, not proof for
every length or a model-quality benchmark. Three route configurations passed all
nine authentication, streaming and automatic-tool checks in the installed setup.

## Prepare pinned source

Requires Git and Python 3.11+. Fetching below downloads source only:

```sh
python3 recipe.py fetch native
python3 recipe.py patch native
python3 recipe.py fetch python
python3 recipe.py fetch recipe
python3 recipe.py status
python3 -m unittest discover -s . -p 'test_recipe.py' -v
```

`patch native` validates the complete patch checksum and source revision, applies
it once, and refuses unexpected source drift. Added kernel/test files are included.
The native revision is `4e80f05ecba89a4e90d16375ade2eddbdc0a10c4`, matching
Bertholomus recipe v0.6.1. All source, model, original-shard and kit revisions are
in [lock.json](lock.json). Preserve the source licenses and third-party notices.

## Prepare each GPU node

Use the pinned upstream recipe's [preparation instructions](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/tree/5e90ec9302149049e8f019ea035827cb24c206f8)
for driver/container setup and the immutable published kernel kit. Obtain the
Mia checkpoint at the locked revision, original DeepSeek shards 47 and 48 for
Engram, and a separate rank cache and token map for each node. Do not confuse a
complete weight download with complete rank-cache preparation. Rank caches add
about 106 GB per node; retain enough storage for inputs, build outputs and rollback.

`upstream/native/tools/dsv41-zig/build_inputs.sh` documents the input-generation
contract and invokes the **Python** TP2 engine. Inspect its fixed container names,
GID value and port before adapting it to your hosts. The Python cache-generation
engine starts rank 0 first; this recipe's **native** serving commands start the
worker first. These are different launch protocols. Do not run cache preparation
alongside a model already occupying the same GPUs.

Build the patched native source with its exact `.zig-version` (0.17.0) in the
locked ARM64 CUDA environment, following your local managed-build policy:

```sh
cd upstream/native
zig build native install -Dnvcc=/usr/local/cuda/bin/nvcc -Doptimize=safe -j1
zig build test -j1 --summary all
```

The server is `zig-out/native/bin/tensorfold-native`, the worker is
`zig-out/bin/tf-dsv41-lanes`. Prepare the CUDA fatbins as specified by upstream's
native packaging rules, including the built `dsv41_ops` code for GPU candidates
and the matching RDMA fatbin. Preserve the published AOT kit; do not silently
replace it with locally rebuilt expert kernels. Both nodes must use identical
runtime artifacts, patches and kit. The RDMA metadata changed; mixed versions
are unsupported. Endpoint MTU negotiation does not validate switched path MTUs.

## Render serving commands

Copy `site.example.json` to `site.json` on each node. Fill actual fabric address,
interface, HCA ports and GID index; container paths; and a local API-key-file path.
The reserved example address and placeholder strings are refused. Example files
contain no actual credentials. Keep site files and keys out of Git.

```sh
python3 recipe.py render --site site.json --profile accepted-c8 --shell
```

This only prints commands. Execute the worker command on rank 1 first, then the
head command on rank 0, inside correctly mounted GPU/RDMA containers. Each node's
paths and HCA names may differ, but their pool, stream and round-row settings must
agree. The head binds loopback and reads an API key from a file; remote access
requires your authenticated gateway. Preserve an existing gateway/key/IP mapping
when upgrading an installation. The public example is not an automatic replacement
for somebody else's reverse proxy or service manager.

Before calling a deployment accepted, verify real completions, cold boundary
requests, streamed replies, tool round trips and rejected credentials through
its actual client routes. Save the old runtime and service configuration so a
failed candidate can be rolled back. This repository never starts or stops a
service automatically.

## Attribution and license

Apache-2.0 for this recipe and TensorFold source contributions. Model weights
retain their own licenses. See [NOTICE](NOTICE) for upstream identities and
[UPSTREAM.md](UPSTREAM.md) for contribution links. We do not claim authorship
of DeepSeek's model, Mia's quantization, or Bertholomus's engine and kernel kit.
