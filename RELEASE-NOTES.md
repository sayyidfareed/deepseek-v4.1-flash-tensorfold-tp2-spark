# Unreleased — upstream short-prompt kernel repair

Add a separately pinned upstream kit overlay for `_topk_sel` N=KK=256.
`prepare_kit.py` prepares a new kit and verifies all 223 manifest entries without
changing the original kit or starting a service. Add a short-boundary option to
the existing completion check. Keep the accepted engine patch and weights unchanged.
Update upstream dispositions: alignment PR closed, direct-I/O and RDMA merged.

Installed pair: all ten short-boundary completions and nine API route checks pass.
No new speed claim or clean-machine installation qualification is made.

# v0.1.0 — source-only preview

Pinned dual-GB10 TensorFold TP2 recipe with eight active slots, a shared 1M-token
pool, optional GPU sampling, retained-cache repairs, native RDMA compatibility,
and the long-prompt alignment fix. Includes the upstream direct-I/O test repair.

This publishes reproducible source and public qualification evidence, not new
model weights or prebuilt runtime binaries. The combined runtime was tested on
a two-node installation; the public checkout is host-tested and its patch
application tested against fresh pinned source. Clean-machine installation and
the remaining per-PR device gates are not claimed. Four runtime PRs are draft;
the test-only PR is ready for review. See UPSTREAM.md and VALIDATION.md.

The API model identity and underlying DeepSeek/Mia weights remain unchanged.
Adaptive 4K prefill is excluded. Measured sampling gains are modest and variable;
no broad advantage over unmodified upstream is claimed.
