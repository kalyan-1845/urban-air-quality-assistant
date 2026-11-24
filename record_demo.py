import asyncio
import os
import shutil
import subprocess
from playwright.async_api import async_playwright

async def record_demo():
    video_dir = os.path.abspath("demo_video")
    if os.path.exists(video_dir):
        shutil.rmtree(video_dir)
    os.makedirs(video_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=video_dir,
            record_video_size={"width": 1280, "height": 720}
        )

        page = await context.new_page()
        print("Navigating to live Streamlit app...")
        await page.goto("https://urban-air-quality-assistant.streamlit.app", timeout=60000)
        
        # Wait for Streamlit to finish loading
        await asyncio.sleep(8)
        print("Page loaded. Starting smooth walkthrough...")

        # Scroll to metrics
        await page.mouse.wheel(0, 250)
        await asyncio.sleep(4)

        await page.mouse.wheel(0, 250)
        await asyncio.sleep(4)

        # Click through tabs
        tab_buttons = await page.query_selector_all('button[data-baseweb="tab"]')
        if not tab_buttons:
            tab_buttons = await page.query_selector_all('[role="tab"]')
        
        print(f"Found {len(tab_buttons)} tabs.")
        for idx, tab in enumerate(tab_buttons):
            try:
                await tab.click()
                print(f"Clicked tab {idx+1}")
                await asyncio.sleep(4)
            except Exception as e:
                print(f"Tab click error {idx}: {e}")

        # Scroll down through content
        await page.mouse.wheel(0, 300)
        await asyncio.sleep(4)

        # Scroll back up to the top
        await page.mouse.wheel(0, -900)
        await asyncio.sleep(3)

        raw_video_path = await page.video.path()
        await context.close()
        await browser.close()
        print("Raw recording saved at:", raw_video_path)

        # Convert to high-quality MP4 using ffmpeg
        mp4_output = os.path.abspath("aerolife_demo.mp4")
        print("Converting to MP4 with ffmpeg...")
        cmd = [
            "ffmpeg", "-y", "-i", raw_video_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
            mp4_output
        ]
        subprocess.run(cmd, check=True)
        print("Successfully generated final MP4 video at:", mp4_output)

if __name__ == "__main__":
    asyncio.run(record_demo())
