
import os
import cv2
import json
import numpy as np
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai
import logging
import re

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = genai.GenerativeModel("gemini-2.0-flash")




def load_and_clean_transcript(file_path):
    logger.info(f"Loading and cleaning transcript from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        cleaned = [line.strip() for line in lines if '-->' not in line and not line.strip().isdigit() and line.strip() != '']
        logger.info("Transcript cleaned successfully.")
        return "\n".join(cleaned)
    except Exception as e:
        logger.error(f"Error while cleaning transcript: {e}")
        raise


def extract_diagram_references(raw_transcript):
    logger.info("Extracting diagram references from transcript")
    try:
        response = GEMINI_MODEL.generate_content(
            ["""
            Analyze the transcript to identify all mentions of relevant educational diagrams or visual aids. Identify mentions of diagrams or visual aids with their timestamps in the transcript. 
            Respond with a JSON list: [{"timestamp": "HH:MM:SS", "context": "text near mention"}]
            """, raw_transcript]
        )
        diagram_references = json.loads(response.text[response.text.find('['):response.text.rfind(']')+1])
        logger.info(f"Found {len(diagram_references)} diagram references.")

        grouped_reference = []
        previous_ref = None

        for ref in diagram_references:
            timestamp = ref['timestamp']
            timestamp_seconds = timestamp_to_seconds(timestamp)

            if previous_ref:
                previous_timestamp_seconds = timestamp_to_seconds(previous_ref['timestamp'])
                if abs(timestamp_seconds-previous_timestamp_seconds) <=5:
                    previous_ref['context'] += " " + ref['context']
                else:
                    grouped_reference.append(previous_ref)
                    previous_ref = ref
            else:
                previous_ref=ref
        
        if previous_ref:
            grouped_reference.append(previous_ref)
        return grouped_reference
    except Exception as e:
        logger.error(f"Error extracting diagram references: {e}")
        return []


def timestamp_to_seconds(timestamp):
    h, m, s = map(int, timestamp.split(":"))
    return h * 3600 + m * 60 + s


def extract_best_frame(video_path, timestamp):
    logger.info(f"Extracting best frame from {video_path} at {timestamp}")
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Could not open video")
        fps = cap.get(cv2.CAP_PROP_FPS)
        target = int(fps * timestamp_to_seconds(timestamp))

        best_frame = None
        min_blur = float('inf')
        for offset in range(-3, 4):
            cap.set(cv2.CAP_PROP_POS_FRAMES, target + offset)
            success, frame = cap.read()
            if not success:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fft = np.fft.fft2(gray)
            magnitude = 20 * np.log(np.abs(np.fft.fftshift(fft)))
            blur_score = np.mean(magnitude)
            if blur_score < min_blur:
                best_frame = frame
                min_blur = blur_score
        cap.release()
        if best_frame is None:
            logger.warning(f"No good frame found at timestamp {timestamp}")
        return best_frame
    except Exception as e:
        logger.error(f"Error extracting frame at {timestamp}: {e}")
        return None


def analyze_frame_relevance(frame):
    logger.info("Analyzing frame relevance using VLM (Gemini model)")
    try:
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        frame_relevance_analysis = GEMINI_MODEL.generate_content([
            """
            Is this frame a relevant and complete diagram, graph, illustration or plot for educational notes?
            Respond with JSON: {"relevant": true/false, "score": 0-1, "reason": "..."}
            """, pil_img])

        frame_relevance_result = json.loads(frame_relevance_analysis.text[frame_relevance_analysis.text.find('{'):frame_relevance_analysis.text.rfind('}')+1])

        logger.info(f"Frame relevance: {frame_relevance_result['relevant']}, score: {frame_relevance_result['score']}")
        
        return frame_relevance_result

    except Exception as e:
        logger.error(f"Error analyzing frame relevance: {e}")
        return {"relevant": False, "score": 0, "reason": "Parsing failed"}


def extract_diagrams(video_path, references, output_dir):
    logger.info(f"Extracting diagrams from video: {video_path}")
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for ref in references:
        logger.info(f"Processing reference at timestamp {ref['timestamp']}")
        frame = extract_best_frame(video_path, ref['timestamp'])
        if frame is None:
            continue
        analysis = analyze_frame_relevance(frame)
        if analysis['relevant'] and analysis['score'] > 0.6:
            filename = f"{ref['timestamp'].replace(':', '_')}.jpg"
            path = os.path.join(output_dir, filename)
            cv2.imwrite(path, frame)
            results.append({
                "timestamp": ref['timestamp'],
                "path": path,
                "description": analysis['reason'],
                "relevance": analysis['score']
            })
    logger.info(f"Extracted {len(results)} relevant diagrams.")
    return results


def generate_outline(transcript):
    logger.info("Generating outline from transcript")
    try:
        response = GEMINI_MODEL.generate_content([
            """
            Analyze the provided transcript and create a detailed educational outline of the content.
            Using the Transcript, identify the core main topics, subtopics, and technical concepts.
            Your analysis should focus on:
            1. Main themes and concepts
            2. Indepth explanation and examples
            3. Logical flow of information
            4. Key points and supporting details
            5. Any references to diagrams or visual aids
            6. Contextual information that enhances understanding
            7. Any other relevant details that can aid in creating educational notes
            8. Formulas and Technical Knowledge
            """, transcript])
        logger.info("Outline generated successfully.")
        return response.text
    except Exception as e:
        logger.error(f"Error generating outline: {e}")
        return ""


def format_to_markdown(enriched_outline, diagrams, output_file):
    logger.info(f"Formatting enriched notes to markdown: {output_file}")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    toc = ["# Table of Contents"]
    content = []
    lines = enriched_outline.split('\n')

    diagram_map = {d['timestamp']: d for d in diagrams}

    for line in lines:
        inserted = False
    
        if line.startswith('## '):
            anchor = line[3:].strip().lower().replace(' ', '-')
            toc.append(f"- [{line[3:].strip()}](#{anchor})")
        elif line.startswith('### '):
            anchor = line[4:].strip().lower().replace(' ', '-')
            toc.append(f"  - [{line[4:].strip()}](#{anchor})")

        
        match = re.search(r'See Figure: (\d{2}:\d{2}:\d{2})', line)
        if match:
            timestamp = match.group(1)
            if timestamp in diagram_map:
                diagram = diagram_map[timestamp]
                rel_path = os.path.relpath(diagram['path'], os.path.dirname(output_file))
                alt_text = diagram.get('description', 'Diagram')
                # img_block = f"\n![{alt_text}]({rel_path})\n*Figure ({timestamp}): {alt_text}*\n"
                img_block = f"\n![]({rel_path})\n"
                line = re.sub(r'See Figure: \d{2}:\d{2}:\d{2}', img_block, line)
                inserted = True

        content.append(line)

    final = "\n".join(toc) + "\n\n" + "\n".join(content)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final)
    logger.info(f"Markdown saved at {output_file}")
    return output_file


def enrich_outline_with_diagrams(outline, diagrams):
    logger.info("Enriching outline with diagram integration")
    try:
        diagram_descriptions = "\n".join([
            f"Timestamp: {d['timestamp']}, Description: {d['description']}" for d in diagrams
        ])
        
        prompt = f"""
        You are an expert in educational content creation with a focus on clarity, structure, and effective use of visual aids.

        You are given:
        1. A detailed lecture outline extracted from an academic transcript.
        2. A list of relevant diagrams, each with a timestamp and a description generated from a vision-language model.

        Your task is to convert the outline into **detailed, natural, and highly readable lecture notes** designed for students.

        Here's what you must do:

        - **Elaborate on each outline point** using full sentences, explanations, and examples. Ensure the tone is approachable but academically precise.
        - **Integrate diagrams meaningfully** by:
        - Inserting a placeholder like `See Figure: <timestamp>` exactly where each diagram logically fits in the explanation.
        - Writing a **caption** for each diagram using its description, tailored to reinforce the explanation above.
        - If a diagram relates to a technical concept or formula, **expand on that concept** using your understanding of the visual content.
        - Where appropriate, include **LaTeX-formatted equations** to make mathematical parts clearer.
        - Ensure the final output is in well-structured **Markdown format**, with:
        - Headings and subheadings preserved and improved
        - Bullet points or numbered lists where helpful
        - Clear and informative image references

        Your goal is to create polished lecture notes that:
        - **Read naturally** like what a top-tier educator would hand out
        - **Explain concepts clearly**
        - **Integrate visuals in context**, not as afterthoughts

        Outline -
        {outline}

        Diagrams-
        {diagram_descriptions}


        """

        response = GEMINI_MODEL.generate_content(prompt)
        content = response.text.strip()

        if content.startswith("```markdown"):
            content = content[len("```markdown"):].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        logger.info("Outline enriched with diagrams.")
        return content

    except Exception as e:
        logger.error(f"Error enriching outline with diagrams: {e}")
        return outline



def run_pipeline(transcript_path, video_path, output_md):
    logger.info(f"Running pipeline for transcript: {transcript_path}, video: {video_path}")
    try:
        raw_transcript = open(transcript_path, 'r', encoding='utf-8').read()
        clean_transcript = load_and_clean_transcript(transcript_path)
        outline = generate_outline(raw_transcript)
        refs = extract_diagram_references(raw_transcript)
        print(refs)
        diagrams = extract_diagrams(video_path, refs, 'Data/Frames')
        enriched = enrich_outline_with_diagrams(outline, diagrams)
        output = format_to_markdown(enriched, diagrams, output_md)
        logger.info(f"Pipeline completed successfully. Notes saved at: {output}")
    except Exception as e:
        logger.error(f"Error during pipeline execution: {e}")
        raise

