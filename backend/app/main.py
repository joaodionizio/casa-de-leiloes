from fastapi import FastAPI

app = FastAPI(title="Casa de Leilões")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
