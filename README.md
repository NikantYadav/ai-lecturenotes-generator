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

### `POST /uploadLecture`

#### Request Format
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

#### Example Request
```bash
curl -X POST "http://localhost:8000/uploadLecture" \
-H "Content-Type: application/json" \
-d '{
  "courseCode": "MATH202",
  "year": 2025,
  "videoId": "linear_algebra_04",
  "videoUrl": "https://storage.com/math202-lec4.mp4",
  "transcriptUrl": "https://storage.com/math202-lec4.txt"
}'
```

#### Response
- Returns `lecture_notes.md` as file attachment
- HTTP 200 on success
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
