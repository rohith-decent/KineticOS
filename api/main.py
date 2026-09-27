from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from api.database import engine, Base, get_db
from api.models_db import SetDB
from contracts.models import SetRecord, SetReport, IsometricSample, IsometricReport
from analytics.report import ReportGenerator
from analytics.chronometer import TrueTimeChronometer
from analytics.trends import TrendsEngine, LongitudinalTrends
from fastapi.staticfiles import StaticFiles
import json

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="KineticOS Analytics & Engine API",
    version="1.0.0",
    description="Role B kinematics calculation, session database, and longitudinal trends"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Ensure directory exists
Path("clips").mkdir(parents=True, exist_ok=True)
app.mount("/clips", StaticFiles(directory="clips"), name="clips")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "KineticOS Role B"}

@app.post("/sets/process", response_model=SetReport)
def process_set(set_record: SetRecord, db: Session = Depends(get_db)):
    report = ReportGenerator.generate_set_report(set_record)

    db_record = SetDB(
        id=report.set_id,
        exercise=report.exercise,
        load_kg=report.load_kg,
        total_reps=report.total_reps,
        report_data=report.model_dump()
    )

    existing = db.query(SetDB).filter(SetDB.id == report.set_id).first()
    if existing:
        existing.exercise = db_record.exercise
        existing.load_kg = db_record.load_kg
        existing.total_reps = db_record.total_reps
        existing.report_data = db_record.report_data
    else:
        db.add(db_record)

    db.commit()
    return report

@app.get("/sets", response_model=List[SetReport])
def list_sets(
    exercise: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(SetDB)
    if exercise:
        query = query.filter(SetDB.exercise == exercise)
    records = query.limit(limit).all()
    return [SetReport.model_validate(r.report_data) for r in records]

@app.get("/sets/{set_id}", response_model=SetReport)
def get_set_report(set_id: str, db: Session = Depends(get_db)):
    record = db.query(SetDB).filter(SetDB.id == set_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Set record not found")
    return SetReport.model_validate(record.report_data)

@app.post("/isometric/process", response_model=IsometricReport)
def process_isometric_session(samples: List[IsometricSample]):
    chronometer = TrueTimeChronometer(exercise="plank")
    return chronometer.process_stream(samples)

@app.get("/analytics/trends/{exercise}", response_model=LongitudinalTrends)
def get_exercise_trends(exercise: str, db: Session = Depends(get_db)):
    records = db.query(SetDB).filter(SetDB.exercise == exercise).all()
    reports = [SetReport.model_validate(r.report_data) for r in records]
    return TrendsEngine.analyze_exercise_history(exercise, reports)



@app.post("/sets/upload", response_model=SetReport)
async def upload_set_record_file(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        contents = await file.read()
        raw_data = json.loads(contents.decode("utf-8"))
        record = SetRecord(**raw_data)
        return process_set(record, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid SetRecord payload: {str(e)}")