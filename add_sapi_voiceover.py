import os
import subprocess
import win32com.client

VOICEOVER_TEXT = (
    "Hello everyone! This is AeroLife, an Urban Air Quality and Smog Intelligence Assistant built for Google PromptWars Challenge 06. "
    "During severe winter smog, generic AQI numbers are not enough. AeroLife connects to live atmospheric sensors, "
    "tracking real-time PM2.5 and PM10 concentrations tailored to your city and household profile. "
    "Powered by Google Gemini, AeroLife generates time-blocked daily routines to bypass thermal inversion smog peaks, "
    "combined with science-backed indoor hacks like DIY box-fan HEPA filters and wet-mopping protocols. "
    "Every sustainable swap is quantified with exact metrics, showing monthly CO2 avoided in kilograms and the percentage reduction in personal particulate inhalation. "
    "Through our Prompt Inspector, judges can audit our structured system instructions and Pydantic schemas, fully backed by automated GitHub Actions CI. Thank you!"
)

def create_voiceover_and_merge():
    wav_path = os.path.abspath("voiceover.wav")
    if os.path.exists(wav_path):
        os.remove(wav_path)

    # Use Windows SAPI Voice
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    
    # SSFMCreateForWrite = 3
    stream.Open(wav_path, 3, False)
    speaker.AudioOutputStream = stream
    speaker.Rate = 0  # Normal speed
    speaker.Speak(VOICEOVER_TEXT)
    stream.Close()
    print("Generated voiceover.wav successfully!")

    input_video = os.path.abspath("aerolife_demo.mp4")
    temp_output = os.path.abspath("aerolife_demo_voiced.mp4")

    # Merge audio with video using ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", wav_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        temp_output
    ]
    subprocess.run(cmd, check=True)
    print("Merged audio and video successfully!")

    # Overwrite aerolife_demo.mp4 with the voiced video
    import shutil
    shutil.copyfile(temp_output, input_video)
    print("aerolife_demo.mp4 is now fully equipped with voiceover audio!")

if __name__ == "__main__":
    create_voiceover_and_merge()
