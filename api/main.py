from fastapi import FastAPI
app = FastAPI(title="KineticOS")

@app.get("/health")
def health():
    return {"ok": True}
