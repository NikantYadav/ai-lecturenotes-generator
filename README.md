## AI Lecture Notes Generator (AILecN)

**AILecN** is a Python-based tool that automatically generates structured lecture notes with diagrams from educational videos. Designed for students, educators, and self-learners, it streamlines content conversion through AI-powered processing.



## Features

- **Automated Note Generation**: Extracts key concepts from video/audio lectures
- **Visual Aid Integration**: Embeds relevant diagrams using computer vision
- **API-Driven Workflow**: REST endpoint for scalable processing
- **Temporary File Management**: Automatic cleanup after processing

---

## Directory Structure

```
.
├── api/                   # FastAPI endpoint implementation
├── Data/
│   ├── Frames/           # Extracted video frames
│   ├── Transcript/       # Processed lecture transcripts
│   └── Video/            # Source video files
├── output/               # Generated lecture notes
├── requirements.txt      # Python dependencies
└── script.py             # Main processing script
```

---

## Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/NikantYadav/ai-lecturenotes-generator.git
   cd ai-lecturenotes-generator
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Data Directories**
   ```bash
   mkdir -p Data/{Frames,Transcript,Video} output
   ```

4. **Make and configure ENV file**
   ```bash
   touch .env
   ```

   The `.env` file should contain the following environment variables:

   ```
   GEMINI_API_KEY=<your_gemini_api_key>
   GEMINI_MODEL=<your_gemini_model_name>
   ```

   - **GEMINI_API_KEY**: Your API key for accessing the Gemini API.
   - **GEMINI_MODEL**: The specific Gemini model you want to use for processing.

---

## Usage

### Local Processing
1. Place source files:
   - Videos in `Data/Video/`
   - Transcripts in `Data/Transcript/`

2. Run processing script:
   ```bash
   python script.py
   ```

3. **Output**:  
   Generated notes appear at `output/lecture_notes.md`

---

## API Integration

AILecN provides a comprehensive RESTful API built with FastAPI. Below are the available endpoints and their usage:

### Setup 
Inside the api folder, create a new .env file which will include the following - 

```
# MongoDB connection string
MONGODB_URI=

# Port for the API server
PORT=

# API Key for Gemini
GEMINI_API_KEY=
GEMINI_MODEL=
```

### API Endpoints

#### Health Check
**`GET /health`**

Check if the API and database connection are functioning properly.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

#### Create Lecture
**`POST /api/lectures`**

Create a new lecture entry with video and transcript URLs.

**Request Format:**
```json
{
  "courseCode": "COMPSCI101",
  "year": 2025,
  "quarter": "Spring",
  "videoId": "lecture_04_24",
  "videoUrl": "https://example.com/lecture.mp4",
  "transcriptUrl": "https://example.com/transcript.txt"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/lectures" \
-H "Content-Type: application/json" \
-d '{
  "courseCode": "MATH202",
  "year": 2025,
  "quarter": "Spring",
  "videoId": "linear_algebra_04",
  "videoUrl": "https://storage.com/math202-lec4.mp4",
  "transcriptUrl": "https://storage.com/math202-lec4.txt"
}'
```

**Response:**
```json
{
  "id": "64c12d7b5a9f2e1c2a3b4d5e"
}
```
- HTTP 201 on success

#### Get Lecture by ID
**`GET /api/lectures/{lecture_id}`**

Get lecture information by ID.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/lectures/64c12d7b5a9f2e1c2a3b4d5e"
```

**Response:**
```json
{
  "_id": "64c12d7b5a9f2e1c2a3b4d5e",
  "courseCode": "MATH202",
  "year": 2025,
  "quarter": "Spring",
  "videoId": "linear_algebra_04",
  "videoUrl": "https://storage.com/math202-lec4.mp4",
  "transcriptUrl": "https://storage.com/math202-lec4.txt",
  "status": "pending",
  "createdAt": "2025-06-04T10:15:30.123Z",
  "updatedAt": "2025-06-04T10:15:30.123Z"
}
```

#### Process Lecture
**`POST /api/lectures/{lecture_id}/process`**

Start processing a lecture to generate notes. This runs as a background task.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/lectures/64c12d7b5a9f2e1c2a3b4d5e/process"
```

**Response:**
```json
{
  "message": "Processing started for lecture 64c12d7b5a9f2e1c2a3b4d5e"
}
```

#### Check Process Status
**`GET /api/lectures/{lecture_id}/status`**

Get the processing status of a lecture.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/lectures/64c12d7b5a9f2e1c2a3b4d5e/status"
```

**Response:**
```json
{
  "status": "processing"
}
```
Status can be "pending", "processing", "completed", or "failed".

#### Get Notes by ID
**`GET /api/notes/{notes_id}`**

Get notes by their ID.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/notes/64c12e8c6a9f2e1c2a3b4d5f"
```

**Response:**
```json
{
  "_id": "64c12e8c6a9f2e1c2a3b4d5f",
  "lectureId": "64c12d7b5a9f2e1c2a3b4d5e",
  "content": "# Lecture Notes\n\n## Introduction to Linear Algebra\n...",
  "format": "md",
  "createdAt": "2025-06-04T10:25:45.678Z",
  "updatedAt": "2025-06-04T10:25:45.678Z"
}
```

#### Get Notes by Lecture ID
**`GET /api/lectures/{lecture_id}/notes`**

Get notes associated with a lecture.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/lectures/64c12d7b5a9f2e1c2a3b4d5e/notes"
```

**Response:**
```json
{
  "_id": "64c12e8c6a9f2e1c2a3b4d5f",
  "lectureId": "64c12d7b5a9f2e1c2a3b4d5e",
  "content": "# Lecture Notes\n\n## Introduction to Linear Algebra\n...",
  "format": "md",
  "createdAt": "2025-06-04T10:25:45.678Z",
  "updatedAt": "2025-06-04T10:25:45.678Z"
}
```

#### Get Raw Notes Content
**`GET /api/lectures/{lecture_id}/notes/content`**

Get the raw Markdown content of notes associated with a lecture.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/lectures/64c12d7b5a9f2e1c2a3b4d5e/notes/content"
```

**Response:**
Raw markdown content with `Content-Type: text/markdown`

---

### API Workflow

1. Create a lecture using `POST /api/lectures`
2. Start processing using `POST /api/lectures/{lecture_id}/process`
3. Check processing status with `GET /api/lectures/{lecture_id}/status`
4. Once completed, retrieve the notes with `GET /api/lectures/{lecture_id}/notes/content`

The API handles:
- Downloading video and transcript files
- Processing media files to extract information
- Generating structured lecture notes with diagrams
- Storing results in a MongoDB database
- Automatic cleanup of temporary files

---

## Requirements

- Python 3.10.11
- All Python libraries listed in `requirements.txt`

---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for improvements and new features.

---

## License

This project is currently not associated with a specific open-source license. Please contact the repository owner for usage permissions.

---

## Contact

For questions, suggestions, or contributions, please open an issue on the GitHub repository.
