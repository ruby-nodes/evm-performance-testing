# Run the System

## Standalone Mode (Single Locust Instance)
To run Locust in standalone mode, build and run the Docker container:

```bash
docker build -t monad-locust .
docker run --rm -p 8089:8089 monad-locust
```

🔗 Open http://localhost:8089 to access the Locust UI.

## Distributed Mode (Master + Workers)
To run Locust in distributed mode (1 master + multiple workers):

```bash
docker-compose up --scale locust-worker=5
```
This will:
- Start 1 Locust Master (UI + Controller)
- Start 5 Locust Workers (processing requests)

Open http://localhost:8089 to control the stress test.