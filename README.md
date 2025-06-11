## AI Lecture Notes Generator (AILecN)

**AILecN** is a Python-based tool that automatically generates structured lecture notes with diagrams from educational videos. Designed for students, educators, and self-learners, it streamlines content conversion through AI-powered processing .

## Features

- **Automated Note Generation**: Extracts key concepts from video/audio lectures 
- **Visual Aid Integration**: Embeds relevant diagrams using computer vision and AI analysis
- **PDF Output**: Generates professional PDF lecture notes with embedded diagrams
- **API-Driven Workflow**: Complete REST API with MongoDB integration for scalable processing

---

## Directory Structure

```
.
├── api/                   # FastAPI endpoint implementation
│   ├── config/           # Database configuration
│   ├── controllers/      # Business logic controllers
│   ├── models/           # Data models and schemas
│   ├── routes/           # API route definitions
│   ├── utils/            # Utility functions
│   ├── output/pdfs/      # Generated PDF files
│   └── requirements.txt  # API-specific dependencies
├── Data/
│   ├── Frames/           # Extracted video frames
│   ├── Transcript/       # Processed lecture transcripts
│   └── Video/            # Source video files
├── output/               # Generated lecture notes (local processing)
├── requirements.txt      # Main dependencies
└── script.py             # Core processing pipeline
```

**Note**: PDF storage location is currently set to `api/output/pdfs/` and can be modified in the `process_lecture` function within `api/controllers/lecture_controller.py`.

---

## Installation

### Prerequisites
- Python 3.10.11+
- Google Chrome browser (for PDF generation)
- MongoDB (for API functionality)

### Setup Steps

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

4. **Configure Environment Variables**
   
   Create a `.env` file in the root directory:
   ```bash
   touch .env
   ```

   Add the following environment variables:
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=<your_openai_api_key>
   OPENAI_MODEL=gpt-4o

   # Google Cloud Vertex AI (Optional - uncomment in script.py if using)
   GOOGLE_APPLICATION_CREDENTIALS_LOCATION=<path_to_credentials_json>
   VERTEXAI_PROJECT=<your_project_id>
   VERTEXAI_LOCATION=<your_location>
   ```

   - **OPENAI_API_KEY**: Your OpenAI API key for GPT model access
   - **OPENAI_MODEL**: The OpenAI model to use (e.g., `gpt-4o`, `gpt-4`, `gpt-3.5-turbo`)

---

## Usage

### Local Processing
1. **Place source files:**
   - Videos in `Data/Video/video.mp4`
   - Transcripts in `Data/Transcript/video.txt`

2. **Run processing script:**
   ```bash
   python script.py
   ```

3. **Output:**  
   - Markdown notes: `output/lecture_notes.md`
   - PDF notes: `output/lecture_notes.pdf`
   - Extracted frames: `Data/Frames_1/`

### Key Features in Local Processing
- **Token Usage Tracking**: Monitors API costs with detailed breakdown
- **Rate Limit Handling**: Automatic retry with exponential backoff
- **PDF Generation**: Professional output using Chrome headless browser
- **Visual Integration**: AI-powered diagram extraction and embedding

---

## API Integration

AILecN provides a comprehensive RESTful API built with FastAPI and MongoDB. The API supports scalable processing with background tasks and automatic file management.

### API Setup 

1. **Install API Dependencies**
   ```bash
   cd api
   pip install -r requirements.txt
   ```

2. **Configure API Environment**
   
   Create `.env` file in the `api/` directory:
   ```env
   # MongoDB Configuration
   MONGODB_URI=<mongodb_uri>

   # Server Configuration
   PORT=8000

   # OpenAI Configuration
   OPENAI_API_KEY=<your_openai_api_key>
   OPENAI_MODEL=gpt-4o
   ```

3. **Start API Server**
   ```bash
   cd api
   uvicorn server:app --reload
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
Status can be "not started", "processing", "completed".

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
  "fileUrl": "/api/output/pdfs/lecture_64c12d7b5a9f2e1c2a3b4d5e.pdf",
  "format": "pdf",
  "createdAt": "2025-06-04T10:25:45.678Z",
  "updatedAt": "2025-06-04T10:25:45.678Z"
}
```

#### Get Notes File URL
**`GET /api/lectures/{lecture_id}/notes/url`**

Get the file URL for downloading PDF notes.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/lectures/64c12d7b5a9f2e1c2a3b4d5e/notes/url"
```

**Response:**
```json
{
  "fileUrl": "/api/output/pdfs/lecture_64c12d7b5a9f2e1c2a3b4d5e.pdf",
  "format": "pdf"
}
```

---

### API Workflow

1. **Create a lecture** using `POST /api/lectures`
2. **Start processing** using `POST /api/lectures/{lecture_id}/process`
3. **Monitor progress** with `GET /api/lectures/{lecture_id}/status`
4. **Retrieve PDF notes** with `GET /api/lectures/{lecture_id}/notes/url`

---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for improvements and new features.

---

## License

This project is currently not associated with a specific open-source license. Please contact the repository owner for usage permissions.

---

## Contact

For questions, suggestions, or contributions, please open an issue on the GitHub repository.


---

## Future Scope & Improvements

- [ ] Diagram Detection Enhancements

- [ ] Notes Quality Improvements

- [ ] Consistency in Notes Generation

- [ ] Fixing Litellm Logging issues

- [ ] Task Management & Queue System : Implement robust background job processing with Redis/Celery

- [ ] Failed Status Implementation


---

