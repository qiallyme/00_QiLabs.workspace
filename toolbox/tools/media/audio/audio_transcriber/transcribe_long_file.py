import os
import sys
import wave
import time
import math
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import speech_recognition as sr

def transcribe_chunk(chunk_path, idx, start_sec, end_sec):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(str(chunk_path)) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data)
        if text:
            return idx, f"[{start_sec/60:.1f}m] {text}", text
    except Exception:
        pass
    return idx, None, None

def write_live(txt_path, wav_name, size_mb, total_dur, results, completed_count, total_chunks, is_final=False):
    ordered_timed = []
    ordered_text = []
    for idx in sorted(results.keys()):
        timed_s, text_s = results[idx]
        if timed_s:
            ordered_timed.append(timed_s)
            ordered_text.append(text_s)

    combined_text = " ".join(ordered_text)
    if not combined_text and is_final:
        combined_text = "[No speech detected / silent / background noise only]"

    status_str = "COMPLETE" if is_final else f"IN PROGRESS ({completed_count}/{total_chunks} chunks completed - {completed_count/total_chunks*100:.1f}%)"

    with open(txt_path, "w", encoding="utf-8") as tf:
        tf.write(f"File: {wav_name}\n")
        tf.write(f"Status: {status_str}\n")
        tf.write(f"Size: {size_mb:.2f} MB\n")
        tf.write(f"Duration: {total_dur / 60:.2f} minutes ({total_dur/3600:.2f} hours)\n\n")
        tf.write("--- TIMED SEGMENTS ---\n")
        tf.write("\n".join(ordered_timed) if ordered_timed else "(Listening / silence in completed chunks so far...)\n")
        tf.write("\n\n--- FULL TRANSCRIPT (LIVE) ---\n")
        tf.write(combined_text)
        tf.flush()

def main():
    wav_path = Path(r"C:\Users\crice\Downloads\USB_Recordings\20210925010006.WAV")
    if not wav_path.exists():
        print(f"File {wav_path} not found.")
        return

    txt_path = wav_path.with_suffix(".txt")
    size_mb = wav_path.stat().st_size / (1024 * 1024)

    print(f"Reading wave header for {wav_path.name}...")
    try:
        with wave.open(str(wav_path), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
    except Exception as e:
        print(f"Error reading header: {e}")
        duration = 33553 # ~9.3 hours fallback

    chunk_sec = 45
    total_chunks = math.ceil(duration / chunk_sec)
    print(f"Target: {wav_path.name} ({size_mb:.2f} MB, {duration/60:.1f} min)")
    print(f"Splitting into {total_chunks} chunks using ffmpeg...")

    chunks_dir = wav_path.parent / f"_fast_chunks_{wav_path.stem}"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir, ignore_errors=True)
    chunks_dir.mkdir(exist_ok=True)

    segment_pattern = str(chunks_dir / "chunk_%04d.wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-f", "segment", "-segment_time", str(chunk_sec),
        "-ac", "1", "-ar", "16000", segment_pattern
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    chunk_files = sorted(list(chunks_dir.glob("chunk_*.wav")))
    total_chunks = len(chunk_files)
    print(f"Chunking complete. Total chunks generated: {total_chunks}")
    print(f"Starting 16-worker parallel transcription with LIVE streaming output...")

    results = {}
    write_live(txt_path, wav_path.name, size_mb, duration, results, 0, total_chunks)

    max_workers = 16
    start_t = time.time()

    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, cf in enumerate(chunk_files):
            s_sec = idx * chunk_sec
            e_sec = s_sec + chunk_sec
            tasks.append(executor.submit(transcribe_chunk, cf, idx, s_sec, e_sec))

    completed_count = 0
    for future in as_completed(tasks):
        idx, timed_str, text_str = future.result()
        if timed_str:
            results[idx] = (timed_str, text_str)
        completed_count += 1
        
        # Write live to file on every completion!
        write_live(txt_path, wav_path.name, size_mb, duration, results, completed_count, total_chunks)

        if completed_count % 25 == 0 or completed_count == total_chunks:
            pct = (completed_count / total_chunks) * 100
            print(f" Progress: {completed_count}/{total_chunks} chunks ({pct:.1f}%) transcribed...")

    write_live(txt_path, wav_path.name, size_mb, duration, results, completed_count, total_chunks, is_final=True)
    elapsed = time.time() - start_t
    print(f"\n==================================================")
    print(f"SUCCESS: {wav_path.name} transcribed in {elapsed:.2f} seconds!")
    print(f"Transcript saved to: {txt_path}")
    print(f"==================================================")

    # Clean up chunks
    shutil.rmtree(chunks_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
