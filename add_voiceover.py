import asyncio
import os
import subprocess
import edge_tts

VOICE = "en-IN-PrabhatNeural"  # Professional Indian English tech voice
VOICEOVER_TEXT = (
    "Hello everyone! This is AeroLife, an Urban Air Quality and Smog Intelligence Assistant built for Google PromptWars Challenge 06. "
    "During severe winter smog, generic AQI numbers are not enough. AeroLife connects to live atmospheric sensors, "
    "tracking real-time PM2.5 and PM10 concentrations tailored to your city and household profile. "
    "Powered by Google Gemini, AeroLife generates time-blocked daily routines to bypass thermal inversion smog peaks, "
    "combined with science-backed indoor hacks like DIY box-fan HEPA filters and wet-mopping protocols. "
    "Every sustainable swap is quantified with exact metrics, showing monthly CO2 avoided in kilograms and the percentage reduction in personal particulate inhalation. "
    "Through our Prompt Inspector, judges can audit our structured system instructions and Pydantic schemas, fully backed by automated GitHub Actions CI. Thank you!"
)

async def generate_voiceover():
    mp3_path = os.path.abspath("voiceover.mp3")
    communicate = edge_tts.Communicate(VOICEOVER_TEXT, VOICE, rate="+5%")
    await communicate.save(mp3_path)
    print("Voiceover audio saved at:", mp3_path)

    input_video = os.path.abspath("aerolife_demo.mp4")
    output_video = os.path.abspath("aerolife_demo_with_voice.mp4")

    # Merge audio with video using ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", mp3_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_video
    ]
    subprocess.run(cmd, check=True)
    print("Merged final video with voiceover at:", output_video)

    # Overwrite aerolife_demo.mp4 with the voiced version
    import shutil
    shutil.copyfile(output_video, input_video)
    print("aerolife_demo.mp4 updated with voiceover successfully!")

if __name__ == "__main__":
    asyncio.run(generate_voiceover())
