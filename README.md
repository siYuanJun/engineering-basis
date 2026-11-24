# 工程判定案例

瓶颈已经从写代码移到判断：这段改动能不能合、这个版本能不能发、这条意见该不该提。判断不写下来，就会变成每次重新讨论，讨论质量取决于当天在场的人。

这个仓收的是这些判断的写法。每个案例给三样东西：一段输入清单、一条可运行的命令、一个预期结论。

## 现有

- 合入前审查：三态判定、风格不进清单、三轮封顶 —— [案例页](cases/review-loop.html) / [可跑切片](demos/review-loop/)

- 发版闸门、缺陷闭环、需求核对、交付表达：在补，按同一模板

## 结构

```
cases/          案例页：问题、判定样例、边界
demos/          最小切片：clone 后可直接跑
method/         为什么这样设计
index.md        私有工程的名字与职责
resume-map.md   能力到案例的映射
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
