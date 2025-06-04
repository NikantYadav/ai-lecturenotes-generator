from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from bson import ObjectId, json_util
import json
from controllers.lecture_controller import LectureController, NotesController
from models.models import LectureModel, NotesModel
from typing import Dict, Any

router = APIRouter()

# Helper function to convert MongoDB objects to JSON
def parse_json(data):
    return json.loads(json_util.dumps(data))

class LectureRequest(BaseModel):
    courseCode: str
    year: int
    quarter: str
    videoId: str
    videoUrl: str
    transcriptUrl: str

@router.post("/api/lectures")
async def create_lecture(lecture: LectureRequest):
    """
    Create a new lecture entry with video and transcript URLs
    Returns the ID of the created document
    """
    lecture_id = await LectureController.create_lecture(lecture.dict())
    return JSONResponse(content={"id": lecture_id}, status_code=201)

@router.get("/api/lectures/{lecture_id}")
async def get_lecture(lecture_id: str):
    """
    Get lecture information by ID
    """
    try:
        lecture = await LectureController.get_lecture(lecture_id)
        return JSONResponse(content=parse_json(lecture))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/lectures/{lecture_id}/process")
async def process_lecture(lecture_id: str, background_tasks: BackgroundTasks):
    """
    Process a lecture to generate notes
    This runs in the background as it may take some time
    """
    background_tasks.add_task(LectureController.process_lecture, lecture_id)
    return JSONResponse(content={"message": f"Processing started for lecture {lecture_id}"})

@router.get("/api/lectures/{lecture_id}/status")
async def get_lecture_status(lecture_id: str):
    """
    Get the processing status of a lecture
    """
    try:
        lecture = await LectureController.get_lecture(lecture_id)
        return JSONResponse(content={"status": lecture["status"]})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/notes/{notes_id}")
async def get_notes(notes_id: str):
    """
    Get notes by ID
    """
    try:
        notes = await NotesController.get_notes(notes_id)
        return JSONResponse(content=parse_json(notes))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/lectures/{lecture_id}/notes")
async def get_lecture_notes(lecture_id: str):
    """
    Get notes associated with a lecture
    """
    try:
        notes = await NotesController.get_notes_by_lecture(lecture_id)
        return JSONResponse(content=parse_json(notes))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/lectures/{lecture_id}/notes/content")
async def get_lecture_notes_content(lecture_id: str):
    """
    Get the raw notes content associated with a lecture
    """
    try:
        notes = await NotesController.get_notes_by_lecture(lecture_id)
        return Response(content=notes["content"], media_type="text/markdown")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
