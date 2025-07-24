import os
import sys
import tempfile
import requests
import logging
import shutil
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException
from config.database import Database
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Add parent directory to path to import from original codebase
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from script import run_pipeline
from script_audio import revision_audio_pipeline, podcast_audio_pipeline
logger = logging.getLogger(__name__)

class LectureController:
    @staticmethod
    async def check_duplicate_lecture(lecture_data):
        """
        Check if a lecture with the same details already exists
        Returns the existing lecture if found, None otherwise
        """
        try:
            collection = Database.db.lectures
            
            # Query for lectures with matching core details (excluding timestamps and status)
            query = {
                "courseCode": lecture_data["courseCode"],
                "year": lecture_data["year"],
                "quarter": lecture_data["quarter"],
                "videoId": lecture_data["videoId"],
                "videoUrl": lecture_data["videoUrl"],
                "transcriptUrl": lecture_data["transcriptUrl"]
            }
            
            existing_lecture = await collection.find_one(query)
            return existing_lecture
        except Exception as e:
            logger.error(f"Error checking for duplicate lecture: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to check for duplicate lecture: {str(e)}")
    
    @staticmethod
    async def create_lecture(lecture_data):
        """
        Create a new lecture entry in the database
        Returns the ID of the created document
        """
        try:
            # Check for duplicate lecture first
            existing_lecture = await LectureController.check_duplicate_lecture(lecture_data)
            if existing_lecture:
                raise HTTPException(
                    status_code=409, 
                    detail="A lecture with these details already exists"
                )
            
            collection = Database.db.lectures
            # Set timestamps
            lecture_data["createdAt"] = datetime.utcnow()
            lecture_data["updatedAt"] = datetime.utcnow()
            lecture_data["status"] = "not started"
            
            result = await collection.insert_one(lecture_data)
            return str(result.inserted_id)
        except HTTPException as e:
            # Re-raise HTTPException (including duplicate check error)
            raise e
        except Exception as e:
            logger.error(f"Error creating lecture: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create lecture: {str(e)}")
    
    @staticmethod
    async def get_lecture(lecture_id):
        """Get a lecture by ID"""
        try:
            collection = Database.db.lectures
            lecture = await collection.find_one({"_id": ObjectId(lecture_id)})
            if not lecture:
                raise HTTPException(status_code=404, detail=f"Lecture with ID {lecture_id} not found")
            return lecture
        except Exception as e:
            logger.error(f"Error retrieving lecture: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve lecture: {str(e)}")

    @staticmethod
    async def process_lecture(lecture_id):
        """
        Process a lecture to generate notes
        1. Download video and transcript
        2. Run pipeline to generate notes
        3. Save notes to database
        4. Update lecture status
        """
        try:
            # Get lecture data
            collection = Database.db.lectures
            lecture = await collection.find_one({"_id": ObjectId(lecture_id)})
            if not lecture:
                raise HTTPException(status_code=404, detail=f"Lecture with ID {lecture_id} not found")
            
            # Update lecture status to processing
            await collection.update_one(
                {"_id": ObjectId(lecture_id)},
                {"$set": {"status": "processing", "updatedAt": datetime.utcnow()}}
            )
            
            # Import utility function
            from utils.file_utils import download_file
            
            try:
                # Download video and transcript
                video_path = await download_file(lecture['videoUrl'], ".mp4")
                transcript_path = await download_file(lecture['transcriptUrl'], ".txt")
            except HTTPException as e:
                await collection.update_one(
                    {"_id": ObjectId(lecture_id)},
                    {"$set": {"status": "failed", "updatedAt": datetime.utcnow(), "error": str(e.detail)}}
                )
                raise
            
            # Set up output path for markdown (intermediate file)
            temp_output_md = tempfile.NamedTemporaryFile(delete=False, suffix=".md").name
            
            # Create output directory for PDF files
            pdf_output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'pdfs')
            os.makedirs(pdf_output_dir, exist_ok=True)
            
            # Run pipeline to generate notes (this will create both MD and PDF)
            logger.info(f"Running pipeline for lecture {lecture_id}")
            # Make sure to set the OPENAI_API_KEY environment variable
            os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
            os.environ["OPENAI_MODEL"] = os.getenv("OPENAI_MODEL", "gpt-4o")
            
            # The run_pipeline function now returns the PDF file path
            
            # pdf_file_path = run_pipeline(transcript_path, video_path, temp_output_md, lecture_id)
            pdf_file_path = await asyncio.to_thread(
                run_pipeline, transcript_path, video_path, temp_output_md, lecture_id
            )
            # Generate a permanent PDF file path with lecture ID
            pdf_filename = f"lecture_{lecture_id}.pdf"
            permanent_pdf_path = os.path.join(pdf_output_dir, pdf_filename)
            
            # Move the generated PDF to the permanent location
            import shutil
            await asyncio.to_thread(shutil.move, pdf_file_path, permanent_pdf_path)
            
            # Create file URL (you might want to adjust this based on your server setup)
            pdf_file_url = f"/api/output/pdfs/{pdf_filename}"
            
            # Save notes to database with PDF file URL
            notes_collection = Database.db.notes
            notes_data = {
                "lectureId": ObjectId(lecture_id),
                "fileUrl": pdf_file_url,
                "format": "pdf",
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
            notes_result = await notes_collection.insert_one(notes_data)
            
            # Update lecture status to completed
            await collection.update_one(
                {"_id": ObjectId(lecture_id)},
                {"$set": {
                    "status": "completed", 
                    "updatedAt": datetime.utcnow(),
                    "notesId": notes_result.inserted_id
                }}
            )
            
            # Clean up temporary files
            await asyncio.to_thread(os.remove,video_path)
            await asyncio.to_thread(os.remove, transcript_path)
            await asyncio.to_thread(os.remove, temp_output_md)
            
            frames_dir = f"Data/Frames_{lecture_id}"
            if os.path.exists(frames_dir):
                try:
                    await asyncio.to_thread(shutil.rmtree, frames_dir)
                    logger.info(f"Removed frames directory: {frames_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove frames directory {frames_dir}: {e}")

            return {
                "lectureId": str(lecture_id),
                "notesId": str(notes_result.inserted_id),
                "status": "completed"
            }
        
        except Exception as e:
            logger.error(f"Error processing lecture: {e}")
            # Update lecture status to failed
            try:
                await collection.update_one(
                    {"_id": ObjectId(lecture_id)},
                    {"$set": {"status": "failed", "updatedAt": datetime.utcnow(), "error": str(e)}}
                )
            except:
                pass
            raise HTTPException(status_code=500, detail=f"Failed to process lecture: {str(e)}")

class NotesController:
    @staticmethod
    async def get_notes_by_lecture(lecture_id):
        """Get notes by lecture ID"""
        try:
            collection = Database.db.notes
            notes = await collection.find_one({"lectureId": ObjectId(lecture_id)})
            if not notes:
                raise HTTPException(status_code=404, detail=f"Notes for lecture {lecture_id} not found")
            return notes
        except Exception as e:
            logger.error(f"Error retrieving notes by lecture: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve notes: {str(e)}")


class AudioController:
    @staticmethod
    async def create_revision_audio(lecture_id, voice="nova", emotion_type="revision"):
        """
        Create revision audio for a lecture
        1. Get lecture data and check if it exists
        2. Download transcript
        3. Generate revision audio using the audio pipeline
        4. Save audio data to database
        5. Update lecture with audio info
        """
        try:
            # Get lecture data
            lectures_collection = Database.db.lectures
            lecture = await lectures_collection.find_one({"_id": ObjectId(lecture_id)})
            if not lecture:
                raise HTTPException(status_code=404, detail=f"Lecture with ID {lecture_id} not found")
        
            # Import utility function
            from utils.file_utils import download_file
            
            try:
                # Download transcript
                transcript_path = await download_file(lecture['transcriptUrl'], ".txt")
                
                # Read transcript content
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                    
            except HTTPException as e:
                raise
            
            # Create output directory for audio files
            audio_output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'audio')
            os.makedirs(audio_output_dir, exist_ok=True)
            
            # Generate revision audio using the pipeline
            logger.info(f"Generating revision audio for lecture {lecture_id}")
            
            # Run the audio pipeline
            audio_result = await asyncio.to_thread(
                revision_audio_pipeline,
                transcript_content,
                audio_output_dir,
                f"lecture_{lecture_id}"
            )
            
            # Create permanent paths and URLs
            audio_filename = f"lecture_{lecture_id}_revision.mp3"
            permanent_audio_path = os.path.join(audio_output_dir, audio_filename)
            
            # Move the generated audio to permanent location if needed
            if audio_result["revision_audio"] != permanent_audio_path:
                await asyncio.to_thread(shutil.move, audio_result["revision_audio"], permanent_audio_path)
            
            # Create file URL
            audio_file_url = f"/api/output/audio/{audio_filename}"
            
            notes_collection = Database.db.notes
            notes_record = await notes_collection.find_one({"lectureId": ObjectId(lecture_id)})

            await notes_collection.update_one(
                {"lectureId": ObjectId(lecture_id)},
                {"$set": {
                    "revisionAudio": audio_file_url,
                    "updatedAt": datetime.utcnow()
                }}
            )

            notes_id = notes_record["_id"]
            await asyncio.to_thread(os.remove, transcript_path)

            logger.info(f"Audio generation completed for lecture {lecture_id}")
    
            return {
                "lectureId": str(lecture_id),
                "notesId": str(notes_id),
                "audioUrl": audio_file_url,
                "revisionNotes": audio_result["revision_notes"],
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error creating revision audio: {e}")
            # Update lecture status to failed
            raise HTTPException(status_code=500, detail=f"Failed to create revision audio: {str(e)}")

    @staticmethod
    async def create_podcast_audio(lecture_id):
        """
        Create podcast audio for a lecture
        1. Get lecture data and check if it exists
        2. Download transcript
        3. Generate podcast audio using the podcast pipeline
        4. Save audio data to database
        5. Update lecture with podcast audio info
        """
        try:
            # Get lecture data
            lectures_collection = Database.db.lectures
            lecture = await lectures_collection.find_one({"_id": ObjectId(lecture_id)})
            if not lecture:
                raise HTTPException(status_code=404, detail=f"Lecture with ID {lecture_id} not found")
        
            # Import utility function
            from utils.file_utils import download_file
            
            try:
                # Download transcript
                transcript_path = await download_file(lecture['transcriptUrl'], ".txt")
                
                # Read transcript content
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                    
            except HTTPException as e:
                raise
            
            # Create output directory for audio files
            audio_output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'audio')
            os.makedirs(audio_output_dir, exist_ok=True)
            
            # Generate podcast audio using the pipeline
            logger.info(f"Generating podcast audio for lecture {lecture_id}")
            
            # Run the podcast pipeline
            podcast_result = await asyncio.to_thread(
                podcast_audio_pipeline,
                transcript_content,
                audio_output_dir,
                f"lecture_{lecture_id}"
            )
            
            # Create permanent paths and URLs
            audio_filename = f"lecture_{lecture_id}_podcast.mp3"
            permanent_audio_path = os.path.join(audio_output_dir, audio_filename)
            
            # Move the generated audio to permanent location if needed
            if podcast_result["podcast_audio"] != permanent_audio_path:
                await asyncio.to_thread(shutil.move, podcast_result["podcast_audio"], permanent_audio_path)
            
            # Create file URL
            audio_file_url = f"/api/output/audio/{audio_filename}"
            
            # Update notes collection with podcast audio
            notes_collection = Database.db.notes
            notes_record = await notes_collection.find_one({"lectureId": ObjectId(lecture_id)})

            await notes_collection.update_one(
                {"lectureId": ObjectId(lecture_id)},
                {"$set": {
                    "podcastAudio": audio_file_url,
                    "updatedAt": datetime.utcnow()
                }}
            )

            notes_id = notes_record["_id"]
            
            # Clean up temporary files
            await asyncio.to_thread(os.remove, transcript_path)

            logger.info(f"Podcast audio generation completed for lecture {lecture_id}")
    
            return {
                "lectureId": str(lecture_id),
                "notesId": str(notes_id),
                "podcastAudioUrl": audio_file_url,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error creating podcast audio: {e}")
            # Update lecture status to failed
            raise HTTPException(status_code=500, detail=f"Failed to create podcast audio: {str(e)}")
        