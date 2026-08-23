# Benchmark Backend V0.1 基线

> **Status:** Implemented read-only baseline

## 目标

本版本只完成现有 `aibench` Registry 的只读接入，以及为未来 MACRO / MICRO / TRACE 结果目录预留 Result Provider 扩展点。

当前**不做**：

- Benchmark Web 运行；
- Queue / Worker；
- Benchmark 数据库表；
- MACRO / MICRO / TRACE 结果格式设计；
- category / target 推断；
- Compare。

## 数据源

Registry 仍然是现有 aibench 的 Source of Truth：

```text
AIBENCH_HOME/
├── registry/
│   ├── chip_registry.json
│   ├── huawei/a5/benchmark_registry.json
│   ├── huawei/a6/benchmark_registry.json
│   └── nvidia/v100/benchmark_registry.json
└── benchmark/
```

平台不调用 `aibench chip list` 或 `aibench benchmark list` 并解析终端文本，而是直接读 JSON。

## 环境变量

在根目录 `.env.platform` 增加：

```bash
AIBENCH_HOME=/home/h00517730/code/ascend_workload_modeling_and_simulation/ascend-bench/aibench/aibench
```

## 当前 API

```text
GET /api/benchmark/status
GET /api/benchmark/chips
GET /api/benchmark/chips/{vendor}/{chip}
GET /api/benchmark/chips/{vendor}/{chip}/benchmarks
GET /api/benchmark/chips/{vendor}/{chip}/benchmarks/{benchmark_name}
GET /api/benchmark/chips/{vendor}/{chip}/benchmarks/{benchmark_name}/results
```

当前 results 接口返回：

```json
{
  "vendor": "huawei",
  "chip": "a5",
  "benchmark_name": "cube_throughput_benchmark",
  "configured": false,
  "items": [],
  "total": 0
}
```

这是有意的空壳，不生成假 Benchmark 数据。

## Registry Schema 策略

当前保持现状，不要求新增 category/target。

如果未来 Registry 中增加：

```json
{
  "category": "micro",
  "target": "cube"
}
```

V0.1 Reader 已经可以直接透传；字段不存在时返回 null。当前不会根据 module 路径猜测类别。

## Result 扩展点

现在：

```text
BenchmarkService
  -> EmptyBenchmarkResultProvider
```

未来结果目录确定后，只新增类似：

```text
FilesystemBenchmarkResultProvider
├── MacroResultParser
├── MicroResultParser
└── TraceResultParser
```

然后替换 Provider，不需要推翻 Registry/API 主结构。

## FastAPI 接入

Benchmark router 已在 `backend/app/main.py` 注册：

```python
from app.api.benchmark import router as benchmark_router
app.include_router(benchmark_router)
```

## 验证

Registry 直接验证：

```bash
cd backend
uv run python scripts/test_benchmark_registry.py \
  --aibench-home /path/to/aibench
```

启动 FastAPI 后：

```bash
curl http://127.0.0.1:8000/api/benchmark/status
curl http://127.0.0.1:8000/api/benchmark/chips
curl http://127.0.0.1:8000/api/benchmark/chips/huawei/a5/benchmarks
```

## 下一阶段

等 Benchmark 结果保存位置和真实样例确定后，再定义结果目录和 Parser。不要在缺少真实数据时预设 MACRO/MICRO/TRACE 的具体 Result Schema。
