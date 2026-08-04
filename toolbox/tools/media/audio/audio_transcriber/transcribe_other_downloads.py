import os
import sys
import time
import math
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import speech_recognition as sr

def transcribe_chunk(cf_path, idx, s_sec, e_sec):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(str(cf_path)) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        if text:
            return idx, f"[{s_sec:.0f}s -> {e_sec:.0f}s] {text}", text
    except Exception:
        pass
    return idx, None, None

def transcribe_file_fast(f_path):
    print(f"\n==========================================")
    print(f"Transcribing: {f_path.name}")
    print(f"==========================================")

    chunks_dir = f_path.parent / f"_temp_segs_{f_path.stem}"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir, ignore_errors=True)
    chunks_dir.mkdir(exist_ok=True)

    segment_pattern = str(chunks_dir / "chunk_%04d.wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(f_path),
        "-f", "segment", "-segment_time", "30",
        "-ac", "1", "-ar", "16000", segment_pattern
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    chunk_files = sorted(list(chunks_dir.glob("chunk_*.wav")))
    print(f" Generated {len(chunk_files)} 30-second chunks...")

    results = {}
    tasks = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        for idx, cf in enumerate(chunk_files):
            s_s = idx * 30
            e_s = s_s + 30
            tasks.append(executor.submit(transcribe_chunk, cf, idx, s_s, e_s))

    for future in as_completed(tasks):
        idx, timed_str, text_str = future.result()
        if timed_str:
            results[idx] = (timed_str, text_str)

    ordered_timed = []
    ordered_text = []
    for idx in sorted(results.keys()):
        t_str, text_str = results[idx]
        ordered_timed.append(t_str)
        ordered_text.append(text_str)

    full_text = " ".join(ordered_text)
    if not full_text:
        full_text = "[No recognizable speech found in this file]"

    print(f"\n--- TRANSCRIPT for {f_path.name} ---")
    for t in ordered_timed:
        print(t)
    print(f"FULL: {full_text}\n")

    txt_out = f_path.with_suffix(".txt")
    with open(txt_out, "w", encoding="utf-8") as out:
        out.write(f"File: {f_path.name}\n\n")
        out.write("--- TIMED SEGMENTS ---\n")
        out.write("\n".join(ordered_timed) if ordered_timed else "No timed segments.\n")
        out.write("\n\n--- FULL TRANSCRIPT ---\n")
        out.write(full_text)

    shutil.rmtree(chunks_dir, ignore_errors=True)

def main():
    downloads = Path(r"C:\Users\crice\Downloads")
    other_files = [
        downloads / "Call Recording 2.m4a",
        downloads / "2026-03-27_Do_Not_Judge 2.mp3",
        downloads / "hhhhhhh (1) 2.mp3",
        downloads / "hhhhhhh (1).mp3",
        downloads / "onga (1).mp3"
    ]

    for f in other_files:
        if f.exists():
            transcribe_file_fast(f)

if __name__ == "__main__":
    main()
