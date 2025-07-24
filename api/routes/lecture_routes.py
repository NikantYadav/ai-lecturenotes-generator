from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response, FileResponse
from pydantic import BaseModel
from bson import ObjectId
import bson.json_util as json_util
import json
import os
from controllers.lecture_controller import LectureController, NotesController, AudioController
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
    try:
        lecture_id = await LectureController.create_lecture(lecture.dict())
        return JSONResponse(content={"id": lecture_id}, status_code=201)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    try:
        # Check if lecture is already completed
        lecture = await LectureController.get_lecture(lecture_id)
        if lecture.get("status") == "completed":
            return JSONResponse(
                content={"message": f"Lecture {lecture_id} has already been processed and completed"},
                status_code=200
            )
        
        # If not completed, start the processing
        background_tasks.add_task(LectureController.process_lecture, lecture_id)
        return JSONResponse(content={"message": f"Processing started for lecture {lecture_id}"})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/api/lectures/{lecture_id}/notes/url")
async def get_lecture_notes_content(lecture_id: str):
    """
    Get the raw notes content associated with a lecture
    For PDF format, this will return the file URL instead of content
    """
    try:
        notes = await NotesController.get_notes_by_lecture(lecture_id)
        if notes["format"] == "pdf":
            return JSONResponse(content={"fileUrl": notes["fileUrl"], "format": "pdf"})
        else:
            # Backward compatibility for markdown content
            return Response(content=notes["content"], media_type="text/markdown")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/api/lectures/{lecture_id}/audio/revision/create")
async def get_revision_audio(lecture_id: str):
    """
    Get the revision audio file for a lecture
    """
    try:
        notes = await NotesController.get_notes_by_lecture(lecture_id)
        if not notes:
            raise HTTPException(status_code=404, detail="Notes not found for this lecture")

        if not notes.get("revisionAudio"):
            revision_result = await AudioController.create_revision_audio(lecture_id)
            return revision_result["audioUrl"]
        else:
            return notes.get("revisionAudio")

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/lectures/{lecture_id}/audio/podcast/create")
async def get_podcast_audio(lecture_id: str):
    """
    Get the podcast audio file for a lecture
    """
    try:
        notes = await NotesController.get_notes_by_lecture(lecture_id)
        if not notes:
            raise HTTPException(status_code=404, detail="Notes not found for this lecture")

        if not notes.get("podcastAudio"):
            podcast_result = await AudioController.create_podcast_audio(lecture_id)
            return podcast_result["podcastAudioUrl"]
        else:
            return notes.get("podcastAudio")

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/api/lectures/{lecture_id}/audio/revision")
async def get_revision_audio_file(lecture_id: str):
    """
    Get the revision audio file url for a lecture
    """
    try:
        notes = await NotesController.get_notes_by_lecture(lecture_id)
        if not notes or not notes.get("revisionAudio"):
            raise HTTPException(status_code=404, detail="Revision audio not found for this lecture")

        return notes["revisionAudio"]
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/api/lectures/{lecture_id}/audio/podcast")
async def get_podcast_audio_file(lecture_id: str):
    """
    Get the podcast audio file url for a lecture
    """
    try:
        notes = await NotesController.get_notes_by_lecture(lecture_id)
        if not notes or not notes.get("podcastAudio"):
            raise HTTPException(status_code=404, detail="Podcast audio not found for this lecture")

        return notes["podcastAudio"]
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))