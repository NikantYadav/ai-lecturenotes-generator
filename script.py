import os
import cv2
import json
import numpy as np
from PIL import Image
from dotenv import load_dotenv
import litellm
import re
import base64
import time
from io import BytesIO
from datetime import datetime
import markdown
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import markdown
from selenium import webdriver
from selenium.webdriver.chrome.options import Options 

load_dotenv()

#For Google Cloud Vertex AI, uncomment the following lines and set the environment variables
#os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_LOCATION")
#os.environ["VERTEXAI_PROJECT"] = os.getenv("VERTEXAI_PROJECT")
#os.environ["VERTEXAI_LOCATION"] = os.getenv("VERTEXAI_LOCATION")


# Configure LiteLLM
litellm.api_key = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL")

token_usage = {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "steps": {}
}

def log_token_usage(step_name, input_tokens, output_tokens):
    token_usage["total_input_tokens"] += input_tokens
    token_usage["total_output_tokens"] += output_tokens
    token_usage["steps"][step_name] = {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens
    }
    print(f"Token usage for {step_name}: {input_tokens} in, {output_tokens} out")

def image_to_base64(image):
    """Convert PIL image to base64 string for LiteLLM"""
    if isinstance(image, np.ndarray):
        # Convert numpy array to PIL Image
        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

def load_and_clean_transcript(file_path):
    print(f"Loading and cleaning transcript from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        cleaned = [line.strip() for line in lines if '-->' not in line and not line.strip().isdigit() and line.strip() != '']
        result = "\n".join(cleaned)
        print(f"Transcript cleaned successfully. Length: {len(result)} characters")
        return result
    except Exception as e:
        print(f"Error while cleaning transcript: {e}")
        raise

def call_llm_with_retry(messages, max_retries=5, base_delay=1, max_delay=60):
    """Call LiteLLM with exponential backoff retry mechanism for rate limits"""
    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.1
            )
            return response
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a rate limit error (429)
            if "429" in error_str or "Too Many Requests" in error_str or "rate limit" in error_str.lower():
                if attempt < max_retries - 1:
                    # Extract retry-after if available
                    retry_after = 1
                    if "retry-after" in error_str:
                        try:
                            # Try to extract retry-after value from error
                            import re
                            match = re.search(r"retry-after['\"]?\s*:\s*['\"]?(\d+)", error_str)
                            if match:
                                retry_after = int(match.group(1))
                        except:
                            pass
                    
                    # Use exponential backoff with jitter, but respect retry-after
                    delay = min(max(base_delay * (2 ** attempt), retry_after), max_delay)
                    jitter = delay * 0.1 * np.random.random()  # Add 10% jitter
                    total_delay = delay + jitter
                    
                    print(f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Retrying in {total_delay:.2f} seconds...")
                    time.sleep(total_delay)
                    continue
                else:
                    print(f"Rate limit exceeded after {max_retries} attempts")
                    raise
            else:
                # For non-rate-limit errors, raise immediately
                print(f"LLM API error: {error_str}")
                raise
    
    raise Exception(f"Failed to complete request after {max_retries} retries")

def extract_diagram_references(raw_transcript):
    print("Extracting diagram references from transcript")
    try:
        prompt = """
        Analyze the transcript to identify all mentions of relevant educational diagrams or visual aids. Identify mentions of diagrams or visual aids with their timestamps in the transcript. 
        Respond with a JSON list: [{"timestamp": "HH:MM:SS", "context": "text near mention"}]
        """
        
        messages = [
            {"role": "user", "content": f"{prompt}\n\nTranscript:\n{raw_transcript}"}
        ]
        
        response = call_llm_with_retry(messages)
        
        # Use actual token usage from LiteLLM response
        usage = response.usage
        log_token_usage("diagram_references", usage.prompt_tokens, usage.completion_tokens)

        response_text = response.choices[0].message.content
        diagram_references = json.loads(response_text[response_text.find('['):response_text.rfind(']')+1])
        print(f"Found {len(diagram_references)} diagram references")

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
        print(f"Error extracting diagram references: {e}")
        return []

def timestamp_to_seconds(timestamp):
    h, m, s = map(int, timestamp.split(":"))
    return h * 3600 + m * 60 + s

def extract_best_frame(video_path, timestamp):
    print(f"Extracting best frame from {video_path} at {timestamp}")
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
            print(f"No good frame found at timestamp {timestamp}")
        return best_frame
    except Exception as e:
        print(f"Error extracting frame at {timestamp}: {e}")
        return None

def analyze_frame_relevance(frame):
    print("Analyzing frame relevance using VLM")
    try:
        # Convert frame to base64 for LiteLLM
        image_base64 = image_to_base64(frame)
        
        prompt = """
        Is this frame a relevant and complete diagram, graph, illustration or plot for educational notes?
        Respond with JSON: {"relevant": true/false, "score": 0-1, "reason": "..."}
        """

        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_base64}}
                ]
            }
        ]

        response = call_llm_with_retry(messages)

        # Use actual token usage from LiteLLM response
        usage = response.usage
        log_token_usage("frame_analysis", usage.prompt_tokens, usage.completion_tokens)

        response_text = response.choices[0].message.content
        frame_relevance_result = json.loads(response_text[response_text.find('{'):response_text.rfind('}')+1])

        print(f"Frame relevance: {frame_relevance_result['relevant']}, score: {frame_relevance_result['score']}")
        
        return frame_relevance_result

    except Exception as e:
        print(f"Error analyzing frame relevance: {e}")
        return {"relevant": False, "score": 0, "reason": "Parsing failed"}

def extract_diagrams(video_path, references, output_dir):
    print(f"Extracting diagrams from video: {video_path}")
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for ref in references:
        print(f"Processing reference at timestamp {ref['timestamp']}")
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
    print(f"Extracted {len(results)} relevant diagrams.")
    return results

def generate_outline(transcript):
    print("Generating outline from transcript")
    try:
        prompt = """
        Analyze the provided transcript and create a detailed educational outline of the content.
        Using the Transcript, identify the core main topics, subtopics, and technical concepts.
        Your analysis should focus on:
        1. Main themes and concepts
        2. Indepth explanation and examples
        3. #logical flow of information
        4. Key points and supporting details
        5. Any references to diagrams or visual aids
        6. Contextual information that enhances understanding
        7. Any other relevant details that can aid in creating educational notes
        8. Formulas and Technical Knowledge
        """
        
        messages = [
            {"role": "user", "content": f"{prompt}\n\nTranscript:\n{transcript}"}
        ]
        
        response = call_llm_with_retry(messages)
        
        # Use actual token usage from LiteLLM response
        usage = response.usage
        log_token_usage("outline_generation", usage.prompt_tokens, usage.completion_tokens)

        outline = response.choices[0].message.content
        print(f"Outline generated successfully. Length: {len(outline)} characters")
        
        return outline
    except Exception as e:
        print(f"Error generating outline: {e}")
        return ""

def fix_image_paths(md_text, base_path):
    """Fix relative image paths to absolute paths for HTML rendering"""
    def replacer(match):
        rel_path = match.group(1).strip()
        abs_path = os.path.abspath(os.path.join(base_path, rel_path))
        return f'![]({f"file://{abs_path}"})'

    return re.sub(r'!\[\]\((.*?)\)', replacer, md_text)

def markdown_to_html(md_path, html_path):
    """Convert markdown file to HTML with proper styling"""
    print(f"Converting markdown to HTML: {md_path} -> {html_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    fixed_md = fix_image_paths(text, os.path.dirname(md_path))
    html = markdown.markdown(fixed_md, extensions=['fenced_code', 'tables'])
    full_html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: sans-serif; margin: 40px; }}
        img {{ max-width: 100%; height: auto; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
      </style>
    </head>
    <body>{html}</body></html>
    """
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"HTML file created: {html_path}")

def html_to_pdf(html_path, pdf_path):
    """Convert HTML file to PDF using selenium and Chrome browser"""
    print(f"Converting HTML to PDF: {html_path} -> {pdf_path}")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)

        # Load the HTML file
        file_url = "file://" + os.path.abspath(html_path)
        driver.get(file_url)
        time.sleep(2)  # wait for full render including images

        # Use DevTools command to print PDF
        pdf = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "paperWidth": 8.27,  # A4 width in inches
            "paperHeight": 11.7,  # A4 height in inches
            "marginTop": 0.4,
            "marginBottom": 0.4,
            "marginLeft": 0.4,
            "marginRight": 0.4
        })

        # Write the PDF data
        with open(pdf_path, "wb") as f:
            f.write(base64.b64decode(pdf['data']))

        print(f"PDF saved successfully: {pdf_path}")
        driver.quit()
        return pdf_path
    except Exception as e:
        print(f"Error converting HTML to PDF: {e}")
        if 'driver' in locals():
            driver.quit()
        raise

def convert_markdown_to_pdf(md_path, output_dir):
    """Convert markdown file to PDF via HTML intermediate"""
    print(f"Converting markdown to PDF: {md_path}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate file paths
    base_name = os.path.splitext(os.path.basename(md_path))[0]
    html_path = os.path.join(output_dir, f"{base_name}_temp.html")
    pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
    
    try:
        # Convert markdown to HTML
        markdown_to_html(md_path, html_path)
        
        # Convert HTML to PDF
        final_pdf_path = html_to_pdf(html_path, pdf_path)
        
        # Clean up temporary HTML file
        if os.path.exists(html_path):
            os.remove(html_path)
            print(f"Temporary HTML file removed: {html_path}")
            
        return final_pdf_path
    except Exception as e:
        print(f"Error in markdown to PDF conversion: {e}")
        # Clean up temporary HTML file if it exists
        if os.path.exists(html_path):
            os.remove(html_path)
        raise

def format_to_markdown(enriched_outline, diagrams, output_file):
    print(f"Formatting enriched notes to markdown: {output_file}")
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
    print(f"Markdown saved at {output_file}")
    return output_file

def enrich_outline_with_diagrams(outline, diagrams):
    print(f"Enriching outline with diagram integration ({len(diagrams)} diagrams)")
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
        - Inserting a placeholder like `See Figure: <timestamp>` exactly where each diagram #logically fits in the explanation.
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

        messages = [
            {"role": "user", "content": prompt}
        ]

        response = call_llm_with_retry(messages)

        # Use actual token usage from LiteLLM response
        usage = response.usage
        log_token_usage("content_enrichment", usage.prompt_tokens, usage.completion_tokens)

        content = response.choices[0].message.content.strip()

        if content.startswith("```markdown"):
            content = content[len("```markdown"):].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        print(f"Outline enriched successfully. Final content length: {len(content)} characters")
        
        return content

    except Exception as e:
        print(f"Error enriching outline with diagrams: {e}")
        return outline

def run_pipeline(transcript_path, video_path, output_md, lecture_id):
    print(f"Running pipeline for transcript: {transcript_path}, video: {video_path}")
    try:
        raw_transcript = open(transcript_path, 'r', encoding='utf-8').read()
        
        # Use clean_transcript instead of raw_transcript for outline generation
        clean_transcript = load_and_clean_transcript(transcript_path)
        outline = generate_outline(clean_transcript)
        refs = extract_diagram_references(raw_transcript)
        print(f"Found {len(refs)} diagram references: {[ref['timestamp'] for ref in refs]}")
        diagrams = extract_diagrams(video_path, refs, f"Data/Frames_{lecture_id}")
        enriched = enrich_outline_with_diagrams(outline, diagrams)
        markdown_output = format_to_markdown(enriched, diagrams, output_md)

        # Convert markdown to PDF
        output_dir = os.path.dirname(output_md)
        pdf_output = convert_markdown_to_pdf(markdown_output, output_dir)

        print(f"Pipeline completed successfully. Notes saved at: {markdown_output}")
        print(f"PDF saved at: {pdf_output}")
        print("\n=== Token Usage Summary ===")
        print(f"Total Input Tokens: {token_usage['total_input_tokens']}")
        print(f"Total Output Tokens: {token_usage['total_output_tokens']}")
        
        # Print step-by-step breakdown of token usage
        for step, usage in token_usage["steps"].items():
            print(f"  {step}: {usage['input']} in, {usage['output']} out, {usage['total']} total")
        
        return pdf_output
    except Exception as e:
        print(f"Error in pipeline execution: {e}")
        raise

if __name__ == "__main__":
    os.makedirs('Data', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    transcript_dir = 'Data/Transcript'
    video_dir = 'Data/Video'
    frames_dir = 'Data/Frames'

    os.makedirs(transcript_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)
    
    #logger.info(f"#logs saved to: {#log_filename}")
    pdf_output = run_pipeline(
        transcript_path="Data/Transcript/video.txt",
        video_path="Data/Video/video.mp4",
        output_md="output/lecture_notes.md",
        lecture_id="1"
    )
    print(f"Final PDF output available at: {pdf_output}")
