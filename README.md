# Local Laya API

A private Dockerized HTTP service for [Laya](https://huggingface.co/convaiinnovations/laya). Model inference and cached weights stay on your machine.

## CPU quick start

```bash
docker compose up --build -d
docker compose logs -f laya
```

The first start downloads the selected checkpoint. Later starts reuse the named Docker volume.

Check it:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/predict \
  -H "content-type: application/json" \
  --data-binary @examples/request.json
```

Interactive OpenAPI documentation: <http://127.0.0.1:8000/docs>

Stop without deleting downloaded weights:

```bash
docker compose down
```

Delete the container and model cache:

```bash
docker compose down -v
```

## NVIDIA GPU

Requirements: NVIDIA driver, Docker, and NVIDIA Container Toolkit. Confirm `docker run --gpus all ... nvidia-smi` works, then run:

```bash
docker compose -f compose.yaml -f compose.gpu.yaml up --build -d
```

Only one Uvicorn worker is used so the model is not duplicated in VRAM.

## Models and preload behavior

Copy `.env.example` to `.env`, then choose models:

```dotenv
# One English model, lowest memory
LAYA_PRELOAD=english
LAYA_MAX_LOADED=1

# Recommended for mixed English/non-English traffic
LAYA_PRELOAD=english,multilingual
LAYA_MAX_LOADED=2

# Keep all checkpoints resident
LAYA_PRELOAD=english,multilingual,typed-decisions
LAYA_MAX_LOADED=3
```

Valid model names are `english`, `multilingual`, and `typed-decisions`. Preloading consumes more RAM/VRAM but prevents multi-second reloads when requests switch models.

You can force a checkpoint per request:

```json
{
  "model": "multilingual",
  "state": "Votre texte",
  "questions": {}
}
```

Normally omit `model`; the router chooses English or multilingual from the input. The typed-decisions model is only selected when explicitly requested with `model` or `task`.

## API

- `GET /health` — device and loaded checkpoints
- `POST /route` — inspect routing without inference
- `POST /predict` — route and run prediction
- `GET /docs` — Swagger/OpenAPI interface

`POST /predict` body:

```json
{
  "state": "text, JSON object, or conversation list",
  "questions": {
    "question_id": {
      "type": "choice",
      "instructions": "Question to evaluate",
      "criteria": {
        "label_a": "meaning of A",
        "label_b": "meaning of B"
      }
    }
  },
  "model": null,
  "task": null,
  "lang": null
}
```

See `examples/client.ts` for a TypeScript client.

## Network exposure

The service binds to `127.0.0.1` by default, so only applications on this machine can access it. For another Docker Compose application, place both services on the same Docker network and call `http://laya:8000`; do not expose the port publicly without authentication and rate limiting.

## Notes

- The image contains Python, PyTorch, the small `laya` runtime, and its dependencies.
- Model weights are not in the image. They are downloaded into the `laya-model-cache` volume on first startup.
- `USE_TF=0` avoids unnecessary TensorFlow probing.
- CPU inference is slower but fully local.
