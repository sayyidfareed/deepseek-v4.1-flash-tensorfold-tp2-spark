# Upstream contributions

Based on engine branch `deepseek-v41-zig` at the locked revision.

The runtime submissions are draft until the unrun device gates in their receipts
are satisfied. The test-only correction is ready for review.

- fix(dsv41): align prompt index blocks without a scratch copy: [PR #8](https://github.com/bertholomus/TensorFold/pull/8) — draft
- test(core): use a buffered descriptor for direct IO comparison: [PR #9](https://github.com/bertholomus/TensorFold/pull/9) — ready for review
- fix(dsv41): protect retained cache extents during growth: [PR #10](https://github.com/bertholomus/TensorFold/pull/10) — draft
- perf(dsv41): add opt-in GPU sampling candidate selection: [PR #11](https://github.com/bertholomus/TensorFold/pull/11) — draft
- fix(dsv41): configure RDMA GID and negotiate endpoint MTU: [PR #12](https://github.com/bertholomus/TensorFold/pull/12) — draft

The alignment proposal is an alternative to [existing engine PR #4](https://github.com/bertholomus/TensorFold/pull/4), which uses a scratch copy. Our proposal instead rounds multi-block strides down to an even number.

The engine fork has no merged PRs at preparation time. Recipe PRs [#7](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/pull/7) and [#8](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/pull/8) informed the small, issue-linked change format. CONTRIBUTING.md and the engine PR template control the receipts.
