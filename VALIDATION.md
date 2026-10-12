# Validation and unrun gates

Environment: two GB10 GPUs, EXL3 2.9 bpw, TP2, CUDA SM121, Zig 0.17.0;
source and checkpoint revisions and ARM64 container identities are in lock.json.
OS receipt: Ubuntu 24.04.5 LTS, kernel 7.0.0-1019-nvidia, driver 580.178.04.
The tested engine uses Bertholomus v0.6.1 kernel assets. No Metal test is claimed.

- Publication recipe: 10/10 offline contracts passed; a real fresh source fetch,
  complete patch application and ready-state verification passed.
- Publication combined source: host build 19/19 steps; 144/144 executed tests
  plus 42 cached passes (186 total). DeepSeek group 110/110, core group 12/12.
- Direct-I/O regression: before 2/3, after 3/3; production read logic unchanged.
- GPU candidate kernel: 21 finite cases, 3 fallback cases, 1 all-tied case passed.
- Alignment helper: regression failed before and passed after; exact cold live
  lengths 72,149 / 72,150 / 72,151 returned correct markers, zero cached tokens.
- Installed combined runtime: 9/9 authentication/stream/tool route checks passed.
- The accepted upstream branch starts with 1,420 lean findings; no submitted
  branch adds a finding. Inherited oversized files remain identified in PRs.
- `test-golden` is listed in CONTRIBUTING.md but absent from this pinned branch:
  invoking it fails with "no such step: test-golden". It was not counted as a pass.

The live evidence predates publication-only formatting/comment cleanup; the
public tree matches the validated source after removing whitespace and standalone
comments (evidence/source-parity.json). The public combined source itself was
host-tested. A new CUDA build and clean-machine installation of this release are
not claimed. No model reload was performed for publication.

Unrun release gates: complete draft-versus-plain, concurrent-versus-solo,
resumed-versus-fresh and intermediate tensor/logit seam comparisons for each
individual PR revision; exhaustive prompt lengths; Metal M1–M5; a standard-server
comparison; the prescribed fresh-KV cold-prefill matrix with retention disabled.
These gaps keep runtime PRs draft. Historical measurements are descriptive,
not substitutes for those release gates or proof of a broad speed improvement.

Run the synthetic boundary gate only against an available test server:

```sh
BASE_URL=http://127.0.0.1:8000 python3 boundary_check.py
```

Supply API_KEY through your environment when authentication is enabled. It is
never written to the receipt. This submits three approximately 72K-token prompts;
the test checks counted tokens and returned markers. It does not restart a server.
The helper needs tokenizer routes exposed on the chosen test endpoint.

## October 12 kit correction

The installed pair added upstream recipe PR #13's pinned kernel overlay to the
existing accepted runtime. Ten cold completions passed at 256, 257, 510, 511,
512, 513, 514, 515, 1024 and 1025 tokens, including correct synthetic marker
retrieval and zero cached prompt tokens. All nine authentication, streaming and
automatic-tool checks passed across three routes. Original credentials restored;
access isolation lasted 184.75 seconds. This is a correctness repair, not a speed
benchmark or proof of every prompt length. See `evidence/short-boundary.json`.

The existing boundary helper can run these short cases independently:

```sh
BASE_URL=http://127.0.0.1:8000 python3 boundary_check.py --short
```

The previous long-boundary mode remains the default.

Recipe-update validation: 12/12 offline tests passed, including preserving the
input kit and rejecting corruption/existing outputs. The preparation command
produced a separate complete kit from the original base with all 223 checksums
verified. The updated public boundary helper passed all ten short cases on the
running pair without a restart. These checks do not qualify a clean-machine
GPU installation of the whole public recipe.
