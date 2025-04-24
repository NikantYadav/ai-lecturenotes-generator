from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import logging
from pydantic import BaseModel
from io import BytesIO
import shutil
import tempfile
import requests
from fpdf import FPDF

from controllers import run_pipeline

app = FastAPI()


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

os.makedirs("output", exist_ok=True)


class LectureUploadRequest(BaseModel):
    courseCode: str
    year: int
    quarter: str
    videoId: str
    videoUrl: str
    transcriptUrl: str


@app.post("/uploadLecture")
async def upload_lecture(request: LectureUploadRequest):
    try:

        logger.info(f"Downloading video from {request.videoUrl}")
        video_response = requests.get(request.videoUrl)
        
        if video_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download video.")
        
        logger.info(f"Downloading transcript from {request.transcriptUrl}")
        transcript_response = requests.get(request.transcriptUrl)
        
        if transcript_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download transcript.")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
            temp_video_file.write(video_response.content)
            video_path = temp_video_file.name
            logger.info(f"Video saved at: {video_path}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_transcript_file:
            temp_transcript_file.write(transcript_response.content)
            transcript_path = temp_transcript_file.name
            logger.info(f"Transcript saved at: {transcript_path}")
        
        output_md = os.path.join("output", f"{request.videoId}_lecture_notes.md")
        
        run_pipeline(transcript_path, video_path, output_md)

        os.remove(video_path)
        os.remove(transcript_path)
        os.remove(output_md)

        return FileResponse(output_md, media_type='text/markdown', filename=os.path.basename(output_md))
    
    except Exception as e:
        logger.error(f"Error during upload lecture process: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the lecture files.")
