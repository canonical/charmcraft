from fastapi import FastAPI  # ty:ignore[unresolved-import]

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
