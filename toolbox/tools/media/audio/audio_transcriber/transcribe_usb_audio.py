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

def get_audio_info(wav_path):
    try:
        with wave.open(str(wav_path), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            return duration, wf.getnchannels(), rate
    except Exception:
        return 0, 0, 0

def transcribe_single_chunk(chunk_path, chunk_idx, start_sec, end_sec):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(str(chunk_path)) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data)
        if text:
            return chunk_idx, f"[{start_sec:.1f}s -> {end_sec:.1f}s] {text}", text
    except Exception:
        pass
    return chunk_idx, None, None

def write_live_transcript(txt_path, wav_path, file_size_mb, duration, results, completed_count, total_chunks, is_final=False):
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

    status_str = "COMPLETE" if is_final else f"IN PROGRESS ({completed_count}/{total_chunks} chunks completed)"

    with open(txt_path, "w", encoding="utf-8") as tf:
        tf.write(f"File: {wav_path.name}\n")
        tf.write(f"Status: {status_str}\n")
        tf.write(f"Size: {file_size_mb:.2f} MB\n")
        tf.write(f"Duration: {duration / 60:.2f} minutes\n\n")
        tf.write("--- TIMED SEGMENTS ---\n")
        tf.write("\n".join(ordered_timed) if ordered_timed else "(Listening / no speech in completed chunks yet...)\n")
        tf.write("\n\n--- FULL TRANSCRIPT (LIVE) ---\n")
        tf.write(combined_text)
        tf.flush()

    return combined_text

def process_file_fast(wav_path, max_workers=16, chunk_sec=45):
    duration, channels, rate = get_audio_info(wav_path)
    file_size_mb = wav_path.stat().st_size / (1024 * 1024)
    txt_path = wav_path.with_suffix(".txt")
    
    print(f"\n==================================================")
    print(f"Processing: {wav_path.name} ({file_size_mb:.2f} MB)")
    print(f"Duration: {duration / 60:.2f} minutes ({duration:.0f}s)")
    print(f"==================================================")

    start_t = time.time()
    
    chunks_dir = wav_path.parent / f"_fast_chunks_{wav_path.stem}"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir, ignore_errors=True)
    chunks_dir.mkdir(exist_ok=True)

    print(" Creating 45-second audio chunks via ffmpeg...")
    segment_pattern = str(chunks_dir / "chunk_%04d.wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-f", "segment", "-segment_time", str(chunk_sec),
        "-ac", "1", "-ar", "16000", segment_pattern
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    chunk_files = sorted(list(chunks_dir.glob("chunk_*.wav")))
    total_chunks = len(chunk_files)
    print(f" Generated {total_chunks} chunks. Transcribing with {max_workers} parallel workers...")

    # Write initial header to txt file
    results = {}
    write_live_transcript(txt_path, wav_path, file_size_mb, duration, results, 0, total_chunks)

    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, cf in enumerate(chunk_files):
            start_s = idx * chunk_sec
            end_s = start_s + chunk_sec
            tasks.append(executor.submit(transcribe_single_chunk, cf, idx, start_s, end_s))

    completed_count = 0
    for future in as_completed(tasks):
        idx, timed_str, text_str = future.result()
        if timed_str:
            results[idx] = (timed_str, text_str)
        completed_count += 1
        
        # Live update text file on EVERY completion so user sees text immediately!
        write_live_transcript(txt_path, wav_path, file_size_mb, duration, results, completed_count, total_chunks)

        if completed_count % 15 == 0 or completed_count == total_chunks:
            print(f"  Live Progress: {completed_count}/{total_chunks} chunks transcribed...")

    final_text = write_live_transcript(txt_path, wav_path, file_size_mb, duration, results, completed_count, total_chunks, is_final=True)
    elapsed = time.time() - start_t
    print(f" Finished {wav_path.name} in {elapsed:.2f} seconds!")

    # Clean up temp folder
    shutil.rmtree(chunks_dir, ignore_errors=True)
    return txt_path, file_size_mb, duration, final_text, elapsed

def main(folder_path):
    target_dir = Path(folder_path)
    if not target_dir.exists():
        print(f"Target directory {target_dir} not found.")
        return

    audio_files = [f for f in target_dir.glob("*.WAV") if f.stat().st_size > 0]
    audio_files.sort(key=lambda f: f.stat().st_size)

    summary_file = target_dir / "TRANSCRIPTIONS_SUMMARY.md"

    print(f"\n==================================================")
    print(f"HIGH-SPEED REAL-TIME STREAMING TRANSCRIPTION")
    print(f"Folder: {target_dir}")
    print(f"Found {len(audio_files)} valid audio recordings\n")

    summary_items = []

    for idx, audio_path in enumerate(audio_files, 1):
        txt_path = audio_path.with_suffix(".txt")
        # Check if already completed
        if txt_path.exists():
            with open(txt_path, "r", encoding="utf-8") as tf:
                head = tf.read(200)
                if "Status: COMPLETE" in head:
                    print(f"[{idx}/{len(audio_files)}] Skipping {audio_path.name} (already fully transcribed).")
                    with open(txt_path, "r", encoding="utf-8") as tf2:
                        content = tf2.read()
                        full_text = content.split("--- FULL TRANSCRIPT (LIVE) ---\n")[-1] if "--- FULL TRANSCRIPT (LIVE) ---" in content else content
                    summary_items.append((audio_path.name, audio_path.stat().st_size / (1024*1024), txt_path.name, full_text.strip()))
                    continue

        txt_p, size_mb, dur, full_text, elapsed = process_file_fast(audio_path, max_workers=16)
        summary_items.append((audio_path.name, size_mb, txt_p.name, full_text))

    with open(summary_file, "w", encoding="utf-8") as summary:
        summary.write("# USB Audio Recordings Transcriptions Summary\n\n")
        summary.write(f"- **Source Folder**: `{target_dir}`\n")
        summary.write(f"- **Total Recordings**: {len(audio_files)}\n\n---\n\n")

        for idx, (fname, size_mb, txt_name, text) in enumerate(summary_items, 1):
            summary.write(f"## {idx}. {fname}\n")
            summary.write(f"- **Size**: {size_mb:.2f} MB\n")
            summary.write(f"- **Transcript File**: [{txt_name}](./{txt_name})\n\n")
            summary.write("### Full Transcript:\n")
            summary.write(f"```\n{text}\n```\n\n---\n\n")

    print(f"\nALL TRANSCRIPTIONS COMPLETE! Summary saved at: {summary_file}")

if __name__ == "__main__":
    dir_p = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\crice\Downloads\USB_Recordings"
    main(dir_p)
