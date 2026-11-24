# review-loop 判定切片

从合入前审查工程中抽出的最小可跑部分：清单校验 + 三态结论。完整工程另有轮次台账、指标统计与交接单，不在这里。

## 跑

```bash
python3 check.py fixtures/block.json
python3 check.py fixtures/pass.json
python3 check.py fixtures/block.json --round 4
python3 check.py fixtures/invalid-style.json
```

零依赖，Python 3。

## 预期结果

| 样例 | 结论 | 退出码 |
|---|---|---|
| block.json | BLOCK，2 条里 1 条 Important 未关闭 | 3 |
| pass.json | APPROVE，历史问题已注明另开单 | 0 |
| block.json --round 4 | ESCALATE，第 4 轮仍未关闭 | 3 |
| invalid-style.json | 清单不合法，风格类意见被拒 | 1 |

## 切片范围

保留：字段校验（id/severity/file/line/claim/evidence/verify/status）、风格词拦截、同文件同行去重、三态判定、退出码。

不含：改动打包、轮次台账写入、指标归一、交接单生成、跨文件影响面分析。

样例均为合成数据，不含任何项目信息。
