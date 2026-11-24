# 工程判定案例

AI 写代码不再是瓶颈。真正耗时的是判断：这段改动能不能合、这个版本能不能发、这条意见该不该提。判断不写下来，就会变成每次重新讨论，讨论质量取决于当天在场的人。

这个仓收的是这些判断的写法。每个案例给三样东西：一段合成输入、一条可运行的命令、一个预期结论。不放项目数据，不放日志截图，也不宣称效果。

## 现有

- 合入前审查：三态判定、风格不进清单、三轮封顶 —— [案例页](cases/review-loop.html) / [可跑切片](demos/review-loop/)

- 发版闸门、缺陷闭环、需求核对、交付表达：在补，按同一模板

## 结构

```
cases/          案例页：问题、判定样例、边界
demos/          最小切片：clone 后可直接跑
method/         为什么这样设计
index.md        私有工程的名字与边界，不含实现
resume-map.md   能力到案例的映射
```

## 边界

- 完整实现在私有仓；公开的是判定切片，不含轮次台账、指标统计与交接单
- 样例是合成的，不代表任何真实项目
- 未接 CI，需本地执行
- 切片只覆盖判定这一段，不替代架构决策

## 本地跑

```bash
git clone --depth 1 https://github.com/siYuanJun/engineering-basis
cd engineering-basis
python3 demos/review-loop/check.py demos/review-loop/fixtures/block.json
```

零依赖，Python 3 直接执行。
