# Phase 0 交付索引

Phase 0 的目标是建立可复现的设计和工程基线，而不是提前实现 Graph 或
ReAct 运行时。以下清单对应 `docs/PRD.md` 第 8 节的任务与验收证据。

| PRD 任务 | 交付物 | 验证证据 |
|---|---|---|
| Monorepo、源码布局、版本策略 | [`src/`](../../src/)、[`packages/`](../../packages/)、[`VERSION`](../../VERSION)、[`VERSIONING.md`](../VERSIONING.md) | 根 `src/` 下 16 个能力模块及各发行物元数据的一致性结构检查 |
| 贡献指南与术语表 | [`CONTRIBUTING.md`](../../CONTRIBUTING.md)、[`GLOSSARY.md`](../GLOSSARY.md) | 提交/推送、边界和安全约束已书面化 |
| 12 个端到端场景 | [`scenario-matrix.md`](scenario-matrix.md) | `E2E-01` 到 `E2E-12` 全量检查；后续测试按 ID 回链 |
| Core boundary、Turn lifecycle、security gateway ADR | [`docs/adr/`](../adr/) | 三份 Proposed ADR 已提交并纳入结构检查 |
| 依赖、代码量、覆盖率和 CI 基线 | [`quality-baseline.md`](quality-baseline.md)、[`quality.yml`](../../.github/workflows/quality.yml) | `make check`、Ruff、strict mypy、coverage；Python 3.12/3.13 矩阵 |
| 架构图与非目标评审材料 | [`ARCHITECTURE.md`](../ARCHITECTURE.md)、[`NON-GOALS.md`](../NON-GOALS.md) | 包依赖方向、Core 禁止反向依赖和 v1 非目标可追溯 |

## 验收命令

在仓库根目录执行：

```text
make check
```

该命令不要求安装 NovaAgent 包或访问网络，适合干净 checkout 的第一道
检查。支持解释器、开发工具和后续行为测试的门禁由 GitHub Actions 工作流
补充。Phase 1 开始后，每新增一个公共契约都必须同时增加 schema、序列化和
端口 conformance 证据，并将结果更新到本索引或对应阶段文档。

Phase 1 的实现与验收证据见 [`docs/phase1/README.md`](../phase1/README.md)。
