import os
import sys
import wave
import time
import math
import shutil
import numpy as np
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import speech_recognition as sr

def process_boosted_chunk(cf_tuple):
    idx, cf_path, start_sec, end_sec = cf_tuple
    recognizer = sr.Recognizer()

    # Read audio data to check max amplitude
    try:
        with wave.open(str(cf_path), 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            data = np.frombuffer(frames, dtype=np.int16)
            max_amp = np.max(np.abs(data)) if len(data) > 0 else 0
    except Exception:
        max_amp = 0

    # If practically silent (< 200 amplitude out of 32767), skip
    if max_amp < 200:
        return idx, None

    # Apply dynamic normalization and gain boost to pull out faint speech
    norm_file = cf_path.parent / f"norm_{cf_path.name}"
    cmd_norm = [
        "ffmpeg", "-y", "-i", str(cf_path),
        "-af", "dynaudnorm=f=150:g=15,volume=12dB", str(norm_file)
    ]
    subprocess.run(cmd_norm, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    text = None
    if norm_file.exists():
        try:
            with sr.AudioFile(str(norm_file)) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
        except Exception:
            pass
        norm_file.unlink(missing_ok=True)

    if text:
        return idx, f"[{start_sec/60:.1f}m] (Amp: {max_amp}) {text}"
    return idx, None

def main():
    wav_path = Path(r"C:\Users\crice\Downloads\USB_Recordings\20210925010006.WAV")
    if not wav_path.exists():
        print(f"File {wav_path} not found.")
        return

    print(f"==================================================")
    print(f"HIGH-SENSITIVITY GAIN BOOST SCAN (16 WORKERS)")
    print(f"Target: {wav_path.name}")
    print(f"==================================================")

    chunk_sec = 30
    chunks_dir = wav_path.parent / f"_fast_boost_chunks_{wav_path.stem}"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir, ignore_errors=True)
    chunks_dir.mkdir(exist_ok=True)

    print(" Creating 30-second audio chunks via ffmpeg...")
    segment_pattern = str(chunks_dir / "chunk_%04d.wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-f", "segment", "-segment_time", str(chunk_sec),
        "-ac", "1", "-ar", "16000", segment_pattern
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    chunk_files = sorted(list(chunks_dir.glob("chunk_*.wav")))
    total_chunks = len(chunk_files)
    print(f" Generated {total_chunks} chunks. Transcribing with 16 parallel workers + dynaudnorm gain boost...")

    tasks_info = []
    for idx, cf in enumerate(chunk_files):
        s_sec = idx * chunk_sec
        e_sec = s_sec + chunk_sec
        tasks_info.append((idx, cf, s_sec, e_sec))

    results = {}
    completed_count = 0
    start_t = time.time()

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(process_boosted_chunk, item): item[0] for item in tasks_info}
        for future in as_completed(futures):
            idx, res_str = future.result()
            if res_str:
                results[idx] = res_str
            completed_count += 1
            if completed_count % 100 == 0 or completed_count == total_chunks:
                print(f"  Progress: {completed_count}/{total_chunks} chunks analyzed...")

    elapsed = time.time() - start_t
    print(f"\nScan completed in {elapsed:.2f} seconds.")
    print(f"Total speech findings: {len(results)}")

    print("\n--- RESULTS FROM HIGH-SENSITIVITY GAIN BOOST ---")
    for idx in sorted(results.keys()):
        print(results[idx])

    shutil.rmtree(chunks_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
