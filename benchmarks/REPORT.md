# Laya container benchmark

This report applies to this machine and the included `examples/request.json` payload. That payload contains three questions and produces 183 input tokens. Results are not universal limits; input length, question count, checkpoint, runtime versions, and hardware change them.

## Test machine

- CPU: AMD Ryzen 7 5700X, 8 cores / 16 logical processors
- RAM: 15.92 GiB host; Docker Desktop exposes 7.719 GiB
- GPU: NVIDIA GeForce RTX 4070 SUPER, 12,282 MiB
- Model: English checkpoint, 421M parameters
- Model cache: 808 MiB
- CPU image disk size: 1.67 GB shown by Docker (349 MB unique over shared layers)
- GPU image disk size: 9.8 GB shown by Docker

## CPU container, no explicit resource limit

Idle after model load:

- CPU: ~0.10%
- memory: 1.878 GiB initially

Peak/retained during a four-request concurrent load:

- CPU: 1,206.71% (about 12 logical cores)
- memory: 2.175 GiB
- processes/threads reported by Docker: 78

The first inference after startup took 5.762 s. Subsequent single requests took approximately 0.48–0.52 s.

| Concurrency | Requests | Errors | Throughput | Mean | p50 | p95 | p99 | Max |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 0 | 1.977 req/s | 503.79 ms | 492.76 ms | 549.42 ms | 651.16 ms | 690.55 ms |
| 2 | 32 | 0 | 2.111 req/s | 943.01 ms | 834.41 ms | 1,415.37 ms | 1,729.99 ms | 1,821.94 ms |
| 4 | 64 | 0 | **2.349 req/s** | 1,698.09 ms | 1,684.77 ms | 1,806.24 ms | 1,836.05 ms | 1,859.27 ms |
| 8 | 32 | 0 | 2.103 req/s | 3,787.27 ms | 3,762.49 ms | 4,118.09 ms | 4,181.84 ms | 4,203.98 ms |

CPU throughput peaked around concurrency 4, but concurrency 1 gave much lower latency.

## Constrained CPU test

A separate container was limited to four CPUs, 2 GiB RAM, and no swap:

```text
--cpus 4 --memory 2g --memory-swap 2g
```

At concurrency 4 over 32 requests:

- 32 successful, 0 failed, no OOM
- throughput: 0.743 req/s
- mean latency: 5,355.03 ms
- p95: 5,647.38 ms
- memory peaked at 1.999 GiB / 2 GiB (99.95%)
- CPU reached approximately 430%

Two GiB technically passed this test but has effectively no safety margin. Reserve at least 3 GiB RAM for one English CPU checkpoint.

## GPU container

The first GPU inference, including CUDA initialization, took 641 ms. The following direct requests took approximately 48–50 ms.

| Concurrency | Requests | Errors | Throughput | Mean | p50 | p95 | p99 | Max |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 100 | 0 | 26.183 req/s | 38.06 ms | **35.35 ms** | 56.37 ms | 59.46 ms | 66.95 ms |
| 2 | 100 | 0 | **26.808 req/s** | 74.09 ms | 74.38 ms | 89.37 ms | 96.72 ms | 102.30 ms |
| 4 | 100 | 0 | 21.127 req/s | 188.60 ms | 189.27 ms | 212.83 ms | 217.74 ms | 220.64 ms |
| 8 | 100 | 0 | 13.618 req/s | 580.30 ms | 592.93 ms | 626.27 ms | 629.65 ms | 632.55 ms |
| 16 | 100 | 0 | 13.817 req/s | 1,134.64 ms | 1,167.07 ms | 1,233.23 ms | 1,262.32 ms | 1,304.57 ms |

During the complete GPU load series:

- GPU utilization: 47% maximum, 26.62% sampled average
- GPU power: 78.35 W maximum
- GPU temperature: 42 C maximum
- total GPU memory reached 4,358 MiB; after stopping the model container it fell to 1,233 MiB, a measured difference of about 3,125 MiB
- container system RAM settled at 1.589 GiB after stress

Concurrency 1 is best for latency and nearly matches the maximum throughput. Concurrency 2 adds only 2.4% throughput while roughly doubling latency. Higher concurrency reduces throughput, increases latency, and increases retained GPU memory.

## Practical limits

For this checkpoint and payload:

- CPU: reserve 3 GiB RAM and use concurrency 1 for latency or up to 4 for throughput.
- GPU: reserve at least 4 GiB VRAM and 2 GiB system RAM for one English checkpoint.
- Keep one Uvicorn worker per GPU. Additional workers duplicate model memory.
- Add an application concurrency queue/limit; unbounded parallel requests are counterproductive.
- Preload only checkpoints that must remain immediately available. Every extra checkpoint increases RAM/VRAM and cache usage.

## Reproduce

Start the service, warm it once, then run:

```bash
python benchmarks/load_test.py --requests 100 --concurrency 1
python benchmarks/load_test.py --requests 100 --concurrency 2
python benchmarks/load_test.py --requests 100 --concurrency 4
```

GPU service on another port:

```bash
python benchmarks/load_test.py --url http://127.0.0.1:8001/predict --requests 100 --concurrency 1
```
