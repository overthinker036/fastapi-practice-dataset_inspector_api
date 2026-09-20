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



app = FastAPI(lifespan=lifespan)



async def get_db_session():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


#Uploaded file processor function:
async def process_uploaded_file(file, a_id: int):
    async with AsyncSessionLocal() as db:
        df = None
        try:
            df = await asyncio.to_thread(pd.read_csv, file)
            
            #CSV analysis here:
            n_cols = len(list(df.columns))
            n_rows = len(df)
            missing_rows_per_column = df.isna().sum()

            analysis = await db.get(database_models.Analysis, a_id)

            if analysis is None:
                raise ValueError(f"Analysis {a_id} not found!")

            analysis.status = "success"
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




@app.post("/analyses")
async def user_posted_an_analysis(file: UploadFile, bgTask: BackgroundTasks, db: AsyncSession = Depends(get_db_session)):
    
    file_contents = await file.read()
    size_mb = len(file_contents)/(1000**2)
    f_type = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""

    if size_mb > 2: raise HTTPException(413, "File too large!")
    if size_mb <= 0: raise HTTPException(400, "File corrupted or empty!")
    if f_type != "csv": raise HTTPException(415, "File is not a CSV!")
   

    #Analyze, save report and filepath to database and the file itself to a filestore

    filename = file.filename
    status = "pending"
    result = None
    error = None


    analysis = database_models.Analysis(filename=filename, status=status, result=result, error=error)


    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    await aios.makedirs("uploads", exist_ok=True)
    dest = os.path.join("uploads", f'{analysis.a_id}.csv')

    async with aiofiles.open(dest, "wb") as buffer:
        await buffer.write(file_contents)
    
    bgTask.add_task(process_uploaded_file, io.BytesIO(file_contents), analysis.a_id)
    return {"message": "File is being processed.",
            "analysis": analysis}
    


@app.get("/analyses/{a_id}")
async def user_wants_single_analysis(a_id: int, db: AsyncSession = Depends(get_db_session)):
    analysis = await db.get(database_models.Analysis, a_id)

    if analysis is None:
        raise HTTPException(404, f"Analysis {a_id} not found!")
    return analysis




@app.get("/analyses/{a_id}/report")
async def user_wants_single_analysis_report(a_id: int, db: AsyncSession = Depends(get_db_session)):
    analysis = await db.get(database_models.Analysis, a_id)

    if analysis is None:
        raise HTTPException(404, f"Analysis {a_id} not found!")
    if analysis.result is None:
        raise HTTPException(404, f"Report for analysis {a_id} not found!")
    return analysis.result




@app.get("/analyses")
async def user_wants_all_analyses(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(database_models.Analysis))
    return result.scalars().all()