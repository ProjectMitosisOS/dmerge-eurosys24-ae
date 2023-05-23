from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    obj = {
        '3': 4
    }
    print(f'id is {hex(id(obj))}')
    return {"message": "Hello World"}