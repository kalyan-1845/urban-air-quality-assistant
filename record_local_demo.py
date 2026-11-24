import asyncio
import os
import shutil
import subprocess
import sys
import time
import requests
from playwright.async_api import async_playwright

def record_full_local_demo():
    video_dir = os.path.abspath("demo_video")
    if os.path.exists(video_dir):
        shutil.rmtree(video_dir)
    os.makedirs(video_dir, exist_ok=True)

    # 1. Start local Streamlit app via sys.executable
    print("Starting local Streamlit instance with python -m streamlit...")
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"]
    
    server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # 2. Wait until localhost:8501 responds
    print("Waiting for server to become responsive...")
    ready = False
    for attempt in range(20):
        try:
            r = requests.get("http://localhost:8501", timeout=1)
            if r.status_code == 200:
                print(f"Server is LIVE on attempt {attempt+1}!")
                ready = True
                break
        except Exception:
            pass
        time.sleep(1)

    if not ready:
        server_process.kill()
        raise RuntimeError("Failed to start local Streamlit server.")

    async def run_playwright():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=video_dir,
                record_video_size={"width": 1280, "height": 720}
            )

            page = await context.new_page()
            print("Connecting to http://localhost:8501 ...")
            await page.goto("http://localhost:8501", timeout=30000)
            await asyncio.sleep(5)

            print("Recording Hero & Metrics...")
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(3)

            await page.mouse.wheel(0, 300)
            await asyncio.sleep(3)

            # Cycle through all tabs
            tabs = await page.query_selector_all('button[data-baseweb="tab"]')
            print(f"Found {len(tabs)} tabs. Walking through each...")

            for i, tab in enumerate(tabs):
                try:
                    await tab.click()
                    print(f"Showing Tab {i+1}...")
                    await asyncio.sleep(4)
                except Exception as e:
                    print(f"Tab error: {e}")

            # Scroll down to see full tab content
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(3)

            # Scroll back to the top
            await page.mouse.wheel(0, -900)
            await asyncio.sleep(2)

            raw_path = await page.video.path()
            await context.close()
            await browser.close()
            return raw_path

    try:
        raw_video = asyncio.run(run_playwright())
        print("Raw video captured at:", raw_video)

        # Convert to MP4
        mp4_output = os.path.abspath("aerolife_demo.mp4")
        print("Encoding clean MP4 video with ffmpeg...")
        subprocess.run([
            "ffmpeg", "-y", "-i", raw_video,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
            mp4_output
        ], check=True)
        print("Done! Clean video saved at:", mp4_output)

    finally:
        server_process.terminate()
        server_process.kill()
        print("Local Streamlit server stopped.")

if __name__ == "__main__":
    record_full_local_demo()
