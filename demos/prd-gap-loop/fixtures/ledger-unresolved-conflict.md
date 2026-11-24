# 合成台账反例：冲突未按待决策处理（非真实项目）

| id | source | requirement | verdict | evidence_type | evidence_ref | gap | action | priority | owner | status | verified_by | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FR-01 | PRD v1.2 §4.1 L20 | 预约人可取消未开始的预约 | 一致 | 真跑 | run:UI-01 -> 取消成功; reports/run-01.md:12 | — | — | P0 | 开发方 | 已闭环 | 验收方 | 验收方独立复跑 |
| FR-02 | PRD v1.2 §4.2 L40 | 取消后释放时段 | 部分 | 接口 | api:POST /api/demo/2/cancel -> 200; reports/api.log:14 | 已有取消接口；缺开始时间校验 | 补齐开始时间校验并补接口证据 | P1 | 开发方 | 处理中 | — | 当前证据只覆盖正常取消 |
| FR-03 | PRD v1.2 §4.3 L60 | 取消后发送通知 | 缺失 | 代码静态 | code-search:rg "notify" -> 0 hits | 未发现通知实现 | 新增通知能力并补运行态证据 | P1 | 开发方 | 待处理 | — | — |
| FR-04 | PRD v1.2 §4.4 L80 | 历史记录导出 | 不适用 | 文档 | docs/contract.md#L10 | 本期范围声明不含导出；依据 PRD §4.4 的 out-of-scope 说明 | — | P2 | 拆单方 | 待验收 | — | 范围依据见文档 |
| AC-01 | PRD v1.2 §5.1 L100 | 并发取消幂等 | 冲突 | 接口 | api:POST /api/demo/3/cancel -> 409; reports/api.log:20 | 实现返回 409，PRD 要求幂等返回 200 | 提交裁决口径 | P1 | 开发方 | 待决策 | — | 已登记，待后续处理 |
| EX-01 | 实现侧扩展 | 批量取消 | 多做 | 代码静态 | demo/service.py:42 | PRD 未要求批量取消 | 保留并登记为扩展能力 | P2 | 开发方 | 待处理 | — | 需产品确认是否下线 |