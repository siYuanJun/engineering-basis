# 工程判定案例

合入、发版、评审各有判定口：这段改动能不能合、这个版本能不能发、这条意见该不该提。把判据写成可执行规则，同一份输入换个人来判，结论一样。

这个仓收的是这些判断的写法。每个案例给三样东西：一段输入清单、一条可运行的命令、一个预期结论。

## 现有

- 合入前审查：三态判定、风格不进清单、三轮封顶 —— [案例页](cases/review-loop.html) / [可跑切片](demos/review-loop/)
- 发版闸门：契约快照比对，字段改名与端点删除阻断 —— [案例页](cases/release-loop.html) / [可跑切片](demos/release-loop/)
- 缺陷闭环：归因决定谁能落，关闭交给提报人 —— [案例页](cases/bug-loop.html) / [可跑切片](demos/bug-loop/)
- 需求核对：逐条台账，验收独立、冲突待决策 —— [案例页](cases/prd-gap-loop.html) / [可跑切片](demos/prd-gap-loop/)
- 交付表达：结构与文案先校验，再生成舞台 —— [案例页](cases/stage-spec.html) / [可跑切片](demos/stage-spec/)

## 结构

```
cases/          案例页：问题、判定样例、边界
demos/          最小切片：clone 后可直接跑
method/         为什么这样设计
index.md        私有工程的名字与职责
```

## 边界

- 公开的是判定切片；完整工程（轮次台账、指标统计、交接单）在私有仓
- 样例是构造的输入，三种结论各一条，用于复现判定
- 本地执行，零依赖
- 判定回答“这条改动按规则能不能合”；方案取舍由人决定

## 本地跑

```bash
git clone --depth 1 https://github.com/siYuanJun/engineering-basis
cd engineering-basis
python3 demos/review-loop/check.py demos/review-loop/fixtures/block.json
```

零依赖，Python 3 直接执行。
