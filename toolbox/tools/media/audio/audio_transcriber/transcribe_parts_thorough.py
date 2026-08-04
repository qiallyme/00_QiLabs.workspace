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

def transcribe_segment_thorough(seg_tuple):
    idx, orig_chunk_path, start_sec, end_sec = seg_tuple
    recognizer = sr.Recognizer()

    # Read audio frame data to check amplitude
    try:
        with wave.open(str(orig_chunk_path), 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            data = np.frombuffer(frames, dtype=np.int16)
            max_amp = np.max(np.abs(data)) if len(data) > 0 else 0
    except Exception:
        max_amp = 0

    # If completely flat/dead silent (< 150 amplitude out of 32767), skip
    if max_amp < 150:
        return idx, None, None

    recognized_text = None

    # Pass 1: Original audio recognition
    try:
        with sr.AudioFile(str(orig_chunk_path)) as source:
            audio1 = recognizer.record(source)
        text1 = recognizer.recognize_google(audio1)
        if text1:
            recognized_text = text1
    except Exception:
        pass

    # Pass 2: Boosted + Normalized audio recognition (if Pass 1 missed or to double check)
    norm_path = orig_chunk_path.parent / f"norm_{orig_chunk_path.name}"
    cmd_norm = [
        "ffmpeg", "-y", "-i", str(orig_chunk_path),
        "-af", "dynaudnorm=f=150:g=15,volume=12dB", str(norm_path)
    ]
    subprocess.run(cmd_norm, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if norm_path.exists():
        try:
            with sr.AudioFile(str(norm_path)) as source2:
                audio2 = recognizer.record(source2)
            text2 = recognizer.recognize_google(audio2)
            if text2:
                if not recognized_text:
                    recognized_text = text2
                elif text2.lower() not in recognized_text.lower():
                    recognized_text = f"{recognized_text} / {text2}"
        except Exception:
            pass
        norm_path.unlink(missing_ok=True)

    if recognized_text:
        min_start = start_sec / 60.0
        min_end = end_sec / 60.0
        timed_str = f"[{min_start:.2f}m -> {min_end:.2f}m] {recognized_text}"
        return idx, timed_str, recognized_text

    return idx, None, None

def write_live_part(txt_path, part_name, size_mb, duration_min, results, completed_count, total_chunks, is_final=False):
    ordered_timed = []
    ordered_text = []
    for idx in sorted(results.keys()):
        t_str, raw_t = results[idx]
        if t_str:
            ordered_timed.append(t_str)
            ordered_text.append(raw_t)

    combined = " ".join(ordered_text)
    if not combined and is_final:
        combined = "[No speech detected / ambient quiet in this chunk]"

    status = "COMPLETE" if is_final else f"IN PROGRESS ({completed_count}/{total_chunks} segments - {completed_count/total_chunks*100:.1f}%)"

    with open(txt_path, "w", encoding="utf-8") as tf:
        tf.write(f"Part File: {part_name}\n")
        tf.write(f"Status: {status}\n")
        tf.write(f"Size: {size_mb:.2f} MB\n")
        tf.write(f"Duration: {duration_min:.2f} minutes\n\n")
        tf.write("--- DETAILED TIMED SEGMENTS ---\n")
        tf.write("\n".join(ordered_timed) if ordered_timed else "(Scanning / ambient silence in completed segments...)\n")
        tf.write("\n\n--- FULL TRANSCRIPT ---\n")
        tf.write(combined)
        tf.flush()

    return combined

def process_part_file(wav_path, max_workers=16, seg_sec=25):
    size_mb = wav_path.stat().st_size / (1024 * 1024)
    txt_path = wav_path.with_suffix(".txt")

    try:
        with wave.open(str(wav_path), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration_sec = frames / float(rate)
    except Exception:
        duration_sec = 6600 # ~110 min fallback

    duration_min = duration_sec / 60.0
    print(f"\n==================================================")
    print(f"Transcribing Part: {wav_path.name} ({size_mb:.2f} MB)")
    print(f"Duration: {duration_min:.2f} minutes ({duration_sec:.0f}s)")
    print(f"==================================================")

    start_t = time.time()
    chunks_dir = wav_path.parent / f"_segs_{wav_path.stem}"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir, ignore_errors=True)
    chunks_dir.mkdir(exist_ok=True)

    print(" Splitting part file into 25-second segments via ffmpeg...")
    segment_pattern = str(chunks_dir / "seg_%04d.wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-f", "segment", "-segment_time", str(seg_sec),
        "-ac", "1", "-ar", "16000", segment_pattern
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    seg_files = sorted(list(chunks_dir.glob("seg_*.wav")))
    total_segs = len(seg_files)
    print(f" Generated {total_segs} segments. Transcribing dual-pass (Original + 12dB Gain Boost)...")

    results = {}
    write_live_part(txt_path, wav_path.name, size_mb, duration_min, results, 0, total_segs)

    task_items = []
    for idx, sf in enumerate(seg_files):
        s_s = idx * seg_sec
        e_s = s_s + seg_sec
        task_items.append((idx, sf, s_s, e_s))

    completed_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(transcribe_segment_thorough, item): item[0] for item in task_items}
        for future in as_completed(futures):
            idx, timed_str, raw_text = future.result()
            if timed_str:
                results[idx] = (timed_str, raw_text)
            completed_count += 1

            # Live update file on every completed segment
            write_live_part(txt_path, wav_path.name, size_mb, duration_min, results, completed_count, total_segs)

            if completed_count % 50 == 0 or completed_count == total_segs:
                pct = (completed_count / total_segs) * 100
                print(f"  Progress {wav_path.name}: {completed_count}/{total_segs} segments ({pct:.1f}%) done...")

    final_text = write_live_part(txt_path, wav_path.name, size_mb, duration_min, results, completed_count, total_segs, is_final=True)
    elapsed = time.time() - start_t
    print(f" Finished {wav_path.name} in {elapsed:.2f} seconds ({len(results)} speech segments found)!")

    shutil.rmtree(chunks_dir, ignore_errors=True)
    return txt_path, size_mb, duration_min, final_text, elapsed

def main():
    parts_dir = Path(r"C:\Users\crice\Downloads\USB_Recordings\20210925010006_Chunks_Under_512MB")
    if not parts_dir.exists():
        print(f"Directory {parts_dir} not found.")
        return

    part_files = sorted(list(parts_dir.glob("*.wav")))
    summary_file = parts_dir / "PARTS_TRANSCRIPT_SUMMARY.md"

    print(f"==================================================")
    print(f"THOROUGH DUAL-PASS PARALLEL TRANSCRIPTION")
    print(f"Folder: {parts_dir}")
    print(f"Found {len(part_files)} split audio files to transcribe")
    print(f"==================================================")

    summary_records = []

    for idx, pf in enumerate(part_files, 1):
        txt_p, size_mb, dur_min, text, elapsed = process_part_file(pf, max_workers=16)
        summary_records.append((pf.name, size_mb, dur_min, txt_p.name, text))

    with open(summary_file, "w", encoding="utf-8") as summary:
        summary.write("# Split Chunks Audio Transcriptions Summary\n\n")
        summary.write(f"- **Source Folder**: `{parts_dir}`\n")
        summary.write(f"- **Total Split Parts**: {len(part_files)}\n")
        summary.write(f"- **Method**: Dual-Pass (Original + 12dB Dynamic Normalization & Gain Boost)\n\n---\n\n")

        for idx, (pname, size_mb, dur_min, txt_name, text) in enumerate(summary_records, 1):
            summary.write(f"## {idx}. {pname}\n")
            summary.write(f"- **Size**: {size_mb:.2f} MB\n")
            summary.write(f"- **Duration**: {dur_min:.2f} minutes\n")
            summary.write(f"- **Transcript File**: [{txt_name}](./{txt_name})\n\n")
            summary.write("### Full Transcript:\n")
            summary.write(f"```\n{text}\n```\n\n---\n\n")

    print(f"\nALL PARTS TRANSCRIBED! Summary saved at: {summary_file}")

if __name__ == "__main__":
    main()
