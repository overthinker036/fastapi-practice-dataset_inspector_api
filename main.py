from fastapi import FastAPI, UploadFile, Depends, HTTPException, BackgroundTasks
from database_conn import AsyncSessionLocal, engine
from sqlalchemy.ext.asyncio import AsyncSession
import database_models, io, traceback, asyncio, os, aiofiles
from contextlib import asynccontextmanager
import pandas as pd
from sqlalchemy import select
from aiofiles import os as aios



@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(
            database_models.Base.metadata.create_all
        )
    yield
    await engine.dispose()



app = FastAPI(lifespan=lifespan, title="CSV Inspector API")



async def get_db_session():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


#Uploaded file processor function:
async def process_uploaded_file(a_id: int, filepath: str):
    async with AsyncSessionLocal() as db:
        analysis = None
        try:
            analysis = await db.get(database_models.Analysis, a_id)

            if analysis is None:
                raise ValueError(f"Analysis {a_id} not found!")

            analysis.status = "running"

            await db.commit()

            #Read CSV without blocking event loop:
            df = await asyncio.to_thread(pd.read_csv, filepath)

            #CSV analysis:
            n_cols = len(list(df.columns))
            n_rows = len(df)

            missing_rows_per_column = df.isna().sum()

            #Analysis succesfull:
            analysis.status = "completed"

            analysis.result = {
                "Columns": int(n_cols),
                "Rows": int(n_rows),
                "Missing per column": {
                    col: int(count) for col, count in missing_rows_per_column.items()
                }
            }

            analysis.error = None
            await db.commit()
        except Exception as e:
            await db.rollback()

            analysis = await db.get(database_models.Analysis, a_id)

            if analysis is not None:
                analysis.status = "failed"
                analysis.error = str(e)
                await db.commit()

            traceback.print_exc()
            

    
    
@app.get("/")
def welcome():
    return "Hello Motherfucker!"




@app.post("/analyses", status_code=202)
async def user_posted_an_analysis(file: UploadFile, bgTask: BackgroundTasks, db: AsyncSession = Depends(get_db_session)):

    f_type = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if f_type != "csv": raise HTTPException(415, "File is not a CSV!")
   

    #Analyze, save report and filepath to database and the file itself to a filestore

    analysis = database_models.Analysis(filename=file.filename, status="pending", result=None, error=None)


    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    await aios.makedirs("uploads", exist_ok=True)
    dest = os.path.join("uploads", f"{analysis.a_id}.csv")

    MAX_SIZE = 2*1024*1024
    total_size = 0

    async with aiofiles.open(dest, "wb") as buffer:
        while True:
            chunk = await file.read(1024*1024)

            if not chunk: break

            total_size += len(chunk)

            if total_size > MAX_SIZE:
                raise HTTPException(413, "File too large!")
            await buffer.write(chunk)

        
    if total_size == 0: raise HTTPException(400, "File corrupted or empty!")

    bgTask.add_task(process_uploaded_file, analysis.a_id, dest)
    
    return {"a_id": analysis.a_id,
            "status": analysis.status}
    


@app.get("/analyses/{a_id}")
async def user_wants_single_analysis(a_id: int, db: AsyncSession = Depends(get_db_session)):
    analysis = await db.get(database_models.Analysis, a_id)

    if analysis is None:
        raise HTTPException(404, f"Analysis {a_id} not found!")
    
    return {
        "a_id": analysis.a_id,
        "status": analysis.status
    }




@app.get("/analyses/{a_id}/report")
async def user_wants_single_analysis_report(a_id: int, db: AsyncSession = Depends(get_db_session)):
    analysis = await db.get(database_models.Analysis, a_id)

    if analysis is None:
        raise HTTPException(404, f"Analysis {a_id} not found!")
    if analysis.status in ("pending", "running"):
        raise HTTPException(409, f"Analysis {a_id} not ready yet!")
    if analysis.status == "failed":
        raise HTTPException(409, f"Analysis {a_id} failed: {analysis.error}")

    return {
        "a_id": analysis.a_id,
        "report": analysis.result,
        "status": analysis.status
    }




@app.get("/analyses")
async def user_wants_all_analyses(status: str | None = None, skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):
    query = select(database_models.Analysis)

    if status is not None:
        query = query.where(database_models.Analysis.status == status)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)

    return result.scalars().all()
    