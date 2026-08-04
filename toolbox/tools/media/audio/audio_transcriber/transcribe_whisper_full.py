import os
import sys
import wave
import time
import math
import shutil
import torch
import subprocess
from pathlib import Path
import whisper

# Set PyTorch to use all CPU cores efficiently without thread contention
torch.set_num_threads(os.cpu_count() or 8)

def write_live_whisper(txt_path, wav_name, size_mb, duration_min, results, completed_count, total_chunks, is_final=False):
    ordered_timed = []
    ordered_text = []
    for idx in sorted(results.keys()):
        t_lines, text_s = results[idx]
        if t_lines:
            ordered_timed.append(t_lines)
            ordered_text.append(text_s)

    combined_text = "\n".join(ordered_text)
    if not combined_text and is_final:
        combined_text = "[No speech detected by Whisper in this audio file]"

    status_str = "COMPLETE" if is_final else f"IN PROGRESS ({completed_count}/{total_chunks} chunks completed - {completed_count/total_chunks*100:.1f}%)"

    with open(txt_path, "w", encoding="utf-8") as tf:
        tf.write(f"File: {wav_name}\n")
        tf.write(f"Engine: Official OpenAI Whisper Neural Model ('base')\n")
        tf.write(f"Status: {status_str}\n")
        tf.write(f"Size: {size_mb:.2f} MB\n")
        tf.write(f"Duration: {duration_min:.2f} minutes\n\n")
        tf.write("--- TIMED SEGMENTS (OPENAI WHISPER LIVE) ---\n")
        tf.write("\n\n".join(ordered_timed) if ordered_timed else "(Listening / room quiet in completed chunks so far...)\n")
        tf.write("\n\n--- FULL TRANSCRIPT (OPENAI WHISPER LIVE) ---\n")
        tf.write(combined_text)
        tf.flush()

    return combined_text

def process_file_whisper(wav_path, model, chunk_sec=60):
    size_mb = wav_path.stat().st_size / (1024 * 1024)
    txt_path = wav_path.with_name(f"{wav_path.stem}_WHISPER.txt")

    try:
        with wave.open(str(wav_path), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration_sec = frames / float(rate)
    except Exception:
        duration_sec = 14550

    duration_min = duration_sec / 60.0

    print(f"\n==================================================")
    print(f"OpenAI Whisper Transcribing: {wav_path.name} ({size_mb:.2f} MB)")
    print(f"Duration: {duration_min:.2f} minutes ({duration_sec:.0f}s)")
    print(f"==================================================")

    start_t = time.time()
    chunks_dir = wav_path.parent / f"_fast_whisper_{wav_path.stem}"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir, ignore_errors=True)
    chunks_dir.mkdir(exist_ok=True)

    print(" Creating 60-second PCM audio chunks via ffmpeg...")
    segment_pattern = str(chunks_dir / "chunk_%04d.wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-f", "segment", "-segment_time", str(chunk_sec),
        "-ac", "1", "-ar", "16000", segment_pattern
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    chunk_files = sorted(list(chunks_dir.glob("chunk_*.wav")))
    total_chunks = len(chunk_files)
    print(f" Generated {total_chunks} chunks. Transcribing with OpenAI Whisper...")

    results = {}
    write_live_whisper(txt_path, wav_path.name, size_mb, duration_min, results, 0, total_chunks)

    for idx, cf_path in enumerate(chunk_files):
        s_sec = idx * chunk_sec
        try:
            res = model.transcribe(str(cf_path), beam_size=5, verbose=False, language="en")
            segments = res.get("segments", [])
            lines = []
            texts = []
            for seg in segments:
                s_m = (s_sec + seg["start"]) / 60.0
                e_m = (s_sec + seg["end"]) / 60.0
                t = seg["text"].strip()
                if t:
                    lines.append(f"[{s_m:.2f}m -> {e_m:.2f}m] {t}")
                    texts.append(t)
            if lines:
                results[idx] = ("\n".join(lines), " ".join(texts))
        except Exception:
            pass

        completed_count = idx + 1
        # Live update file after every single chunk!
        write_live_whisper(txt_path, wav_path.name, size_mb, duration_min, results, completed_count, total_chunks)

        if completed_count % 10 == 0 or completed_count == total_chunks:
            pct = (completed_count / total_chunks) * 100
            print(f"  Whisper Progress {wav_path.name}: {completed_count}/{total_chunks} chunks ({pct:.1f}%) done...")

    final_text = write_live_whisper(txt_path, wav_path.name, size_mb, duration_min, results, total_chunks, total_chunks, is_final=True)
    elapsed = time.time() - start_t
    print(f" Finished {wav_path.name} in {elapsed:.2f} seconds ({len(results)} chunks with speech)!")

    shutil.rmtree(chunks_dir, ignore_errors=True)
    return txt_path

def main():
    folder = Path(r"C:\Users\crice\Downloads\USB_Recordings")
    target_file = None

    if len(sys.argv) > 1:
        t = Path(sys.argv[1])
        if t.is_file():
            target_file = t

    print("Loading OpenAI Whisper neural model ('base')...")
    model = whisper.load_model("base")

    if target_file:
        process_file_whisper(target_file, model)
    else:
        audio_files = [f for f in folder.glob("*.WAV") if f.stat().st_size > 10 * 1024 * 1024]
        audio_files.sort(key=lambda f: f.stat().st_size)
        for f in audio_files:
            process_file_whisper(f, model)

if __name__ == "__main__":
    main()
