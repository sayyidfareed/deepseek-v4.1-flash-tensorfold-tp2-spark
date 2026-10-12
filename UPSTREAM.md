# Upstream contributions

Based on engine branch `deepseek-v41-zig` at the locked revision.

Status checked October 12, 2026. Retained-cache and GPU-candidate submissions
remain draft with device gates pending.

- fix(dsv41): align prompt index blocks without a scratch copy: [PR #8](https://github.com/bertholomus/TensorFold/pull/8) — closed; maintainer merged alternative #4
- test(core): use a buffered descriptor for direct IO comparison: [PR #9](https://github.com/bertholomus/TensorFold/pull/9) — merged
- fix(dsv41): protect retained cache extents during growth: [PR #10](https://github.com/bertholomus/TensorFold/pull/10) — draft
- perf(dsv41): add opt-in GPU sampling candidate selection: [PR #11](https://github.com/bertholomus/TensorFold/pull/11) — draft
- fix(dsv41): configure RDMA GID and negotiate endpoint MTU: [PR #12](https://github.com/bertholomus/TensorFold/pull/12) — merged

The alignment proposal is an alternative to [existing engine PR #4](https://github.com/bertholomus/TensorFold/pull/4), which uses a scratch copy. Our proposal instead rounds multi-block strides down to an even number.

At initial preparation the engine fork had no merged PRs. Recipe PRs [#7](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/pull/7) and [#8](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/pull/8) informed the small, issue-linked change format. CONTRIBUTING.md and the engine PR template control the receipts.

The recipe also consumes the merged upstream [kernel-kit PR #13](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/pull/13) by Lucas Peters, pinned by commit and file checksums in `lock.json`. This repairs a separate 512/513-token missing variant. Closing our alignment PR does not remove our locally validated alignment implementation; no source rebase or alternate alignment deployment is claimed.
