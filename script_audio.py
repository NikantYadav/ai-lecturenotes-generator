import os
import re
from pathlib import Path
from openai import OpenAI
import time
import dotenv
from pydub import AudioSegment

# Load environment variables
dotenv.load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_revision_notes(transcript):
    """Create concise revision notes with emotional memory hooks"""
    prompt = f"""
    Create engaging audio-friendly revision notes with emotional cues:
    1. Convert key points to memorable phrases
    2. Add emotional context notes in [brackets]:
       - [important] for critical concepts
       - [remember] for memory hooks
       - [surprise] for counterintuitive facts
    3. Use mnemonics with personality
    4. Include self-testing questions with [curious] tone
    5. Add vocal emphasis hints like *remember this*

    Transcript:
    {transcript[:10000]}
    """
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You're creating audio revision materials with emotional memory aids."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )
    return response.choices[0].message.content.strip()

def text_to_speech(text, output_path, voice="shimmer", emotion_type="educational"):
    """Convert text to emotional speech using TTS instructions"""
    # Clean text while preserving emotional cues
    text = re.sub(r'[\[\]]', '', text)  # Remove brackets but keep content
    
    # Emotion-specific instructions
    emotion_instructions = {
        "podcast": "Use a warm, engaging tone. Vary your delivery - sound excited for breakthroughs, "
                   "serious for important concepts, and curious for questions. Add dramatic pauses "
                   "where indicated. Emphasize text between asterisks.",
        "revision": "Speak clearly at a moderate pace. Sound focused for key points, surprised for "
                    "counterintuitive facts, and encouraging for memory aids. Use slight emphasis "
                    "on asterisked terms. Pause briefly after each concept.",
        "educational": "Maintain professional educator tone. Sound passionate about the subject, "
                       "authoritative on key concepts, and intrigued by complexities. Use strategic "
                       "pauses for absorption."
    }
    
    # Voice mapping
    voice_profiles = {
        "shimmer": {"voice": "shimmer", "description": "expressive female"},
        "coral": {"voice": "coral", "description": "energetic female"},
        "nova": {"voice": "nova", "description": "clear female"},
        "onyx": {"voice": "onyx", "description": "deep male"}
    }
    
    # Create output directory if needed
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate speech with emotional instructions
    with client.audio.speech.with_streaming_response.create(
        model="tts-1-hd",
        voice=voice_profiles[voice]["voice"],
        input=text,
        instructions=emotion_instructions[emotion_type],
        response_format="mp3"
    ) as response:
        response.stream_to_file(output_path)
    
    print(f"Generated {emotion_type} audio with {voice_profiles[voice]['description']} voice")
    return output_path

def revision_audio_pipeline(transcript, output_dir=None, base_filename="lecture"):
    """Pipeline with emotional TTS instructions for revision audio notes
    """
    
    print("Generating revision notes...")
    revision_notes = create_revision_notes(transcript)
    
    print("Generating revision audio...")
    # Construct the full output path
    output_path = os.path.join(output_dir if output_dir else ".", f"{base_filename}_revision.mp3")
    
    revision_audio = text_to_speech(
        revision_notes,
        output_path,
        voice="nova",
        emotion_type="revision"
    )
    
    print("\nProcessing complete! Files created:")

    
    return {
        "revision_notes": revision_notes,
        "revision_audio": str(revision_audio)
    }

def clean_script(script):
    """Remove bracketed instructions and timestamps from the script"""
    # Remove timestamp patterns like "00:00:00.000"
    script = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}\s*', '', script)
    # Remove all bracketed instructions like [excited] or [Intro with welcoming tone]
    script = re.sub(r'\[[^\]]+\]\s*', '', script)
    return script.strip()

def convert_to_dialogue(script):
    """Convert single-speaker script into two-speaker dialogue"""
    # system_prompt = """You're a podcast producer converting a monologue script into a natural two-speaker dialogue between HOST and EXPERT.
    # - Maintain all technical content accurately
    # - Preserve the original structure and emotional tone cues
    # - HOST handles introductions, transitions, and questions
    # - EXPERT provides technical explanations and details
    # - Keep responses conversational and balanced"""
    
    system_prompt = """You're a podcast producer converting a monologue script into a natural two-speaker dialogue between HOST and EXPERT.

    FORMATTING REQUIREMENTS:
    - Use EXACTLY this format for speaker labels: "HOST:" and "EXPERT:" (no asterisks, no bold formatting)
    - Each speaker line must start with the label followed by a colon and space
    - Do not use **HOST:** or **EXPERT:** or any other formatting
    - Each speaker's dialogue should be on separate lines

    CONTENT REQUIREMENTS:
    - Maintain all technical content accurately
    - Preserve the original structure and emotional tone cues
    - HOST handles introductions, transitions, and questions
    - EXPERT provides technical explanations and details  
    - Keep responses conversational and balanced
    - Ensure natural flow between speakers

    EXAMPLE FORMAT:
    HOST: Welcome to today's episode! Let's dive into machine learning optimization.

    EXPERT: Thanks for having me! Optimization is indeed central to machine learning training.

    HOST: Can you explain what an optimization problem looks like in this context?

    EXPERT: Absolutely. An optimization problem typically involves finding the best solution from available alternatives...

    Always follow this exact formatting pattern throughout the entire dialogue."""

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": script}
        ],
        temperature=0.4,
        max_tokens=3000
    )
    return response.choices[0].message.content.strip()

def generate_podcast_audio(script, output_path):
    """Generate podcast audio with two speakers and emotional tones, preserving dialogue order."""

    # 1) Parse the dialogue into an ordered list of (speaker, text)
    segments = []
    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith('HOST:'):
            text = line[len('HOST:'):].strip()
            segments.append({'speaker': 'host', 'text': text})
        elif line.startswith('EXPERT:'):
            text = line[len('EXPERT:'):].strip()
            segments.append({'speaker': 'expert', 'text': text})
        else:
            # Continuation of previous segment
            if segments:
                segments[-1]['text'] += ' ' + line

    # 2) Generate TTS for each segment in sequence
    temp_files = []
    for idx, seg in enumerate(segments):
        speaker = seg['speaker']
        text = seg['text']

        # choose voice
        voice = 'shimmer' if speaker == 'host' else 'onyx'
        # determine emotion
        if speaker == 'host':
            emotion = 'excited' if idx == 0 else 'serious'
        else:
            emotion = 'serious'

        filename = f"{speaker}_{idx}.mp3"
        generate_tts_segment(text, filename, voice=voice, emotion=emotion)
        temp_files.append(filename)

    # 3) Concatenate all segments in order
    combined = AudioSegment.empty()
    for fn in temp_files:
        combined += AudioSegment.from_mp3(fn)

    # 4) Export final podcast file
    combined.export(output_path, format='mp3')

    # 5) Clean up temporary files
    for fn in temp_files:
        Path(fn).unlink()

    print(f"Podcast audio written to {output_path} (built from {len(temp_files)} segments)")

def generate_tts_segment(text, output_path, voice="shimmer", emotion="neutral"):
    """Generate TTS for a single segment with emotional instructions"""
    emotion_instructions = {
        "excited": "Speak in an excited, enthusiastic tone. Vary your pitch and pace. Sound welcoming and engaging.",
        "serious": "Use a serious, professional tone. Speak clearly and authoritatively. Emphasize technical terms.",
        "neutral": "Maintain a calm, professional educator tone. Speak clearly at a moderate pace."
    }
    
    instruction = emotion_instructions.get(emotion, emotion_instructions["neutral"])
    
    # Clean text for TTS
    text = re.sub(r'[\[\]\(\)\*]', '', text)  # Remove special formatting
    
    with client.audio.speech.with_streaming_response.create(
        model="tts-1-hd",
        voice=voice,
        input=text,
        instructions=instruction,
        response_format="mp3"
    ) as response:
        response.stream_to_file(output_path)

def combine_audio(segment_files, output_path):
    """Combine multiple audio segments into a single file"""
    
    combined = AudioSegment.empty()
    for file in segment_files:
        sound = AudioSegment.from_mp3(file)
        combined += sound
    
    combined.export(output_path, format="mp3")

def podcast_audio_pipeline(transcript, output_dir=None, base_filename="podcast"):
    """Pipeline for creating podcast audio from script with emotional TTS
    
    Args:
        script (str): Raw script content or file path
        output_dir (str): Output directory path (optional)
        base_filename (str): Base name for output files
    
    Returns:
        dict: Dictionary containing paths to generated files
    """
    
    print("Creating podcast from script...")
    
    # Handle script input (string content or file path)
    if os.path.isfile(transcript):
        with open(transcript, 'r') as f:
            original_script = f.read()
        print(f"Loaded script from file: {transcript}")
    else:
        original_script = transcript
        print("Using provided transcript content")

    # Clean the script
    print("Cleaning script...")
    cleaned_script = clean_script(original_script)
    
    # Convert to two-speaker dialogue
    print("Converting to dialogue format...")
    dialogue_script = convert_to_dialogue(cleaned_script)

    # Generate podcast audio
    print("Generating podcast audio...")
    
    # Construct the full output path
    output_path = os.path.join(output_dir if output_dir else ".", f"{base_filename}_podcast.mp3")
    
    # Generate the podcast audio
    generate_podcast_audio(dialogue_script, output_path)
    
    print("\nProcessing complete! Files created:")
    print(f"- Podcast audio: {output_path}")
    
    return {
        "podcast_audio": str(output_path)
    }
