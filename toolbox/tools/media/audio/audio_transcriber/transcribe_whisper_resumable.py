import os
import sys
import glob
import json
import time
import wave
import shutil
import datetime
import numpy as np
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import torch
import whisper

AUDIO_FILE = Path(r"C:\Users\crice\Downloads\USB_Recordings\20210707053656.WAV")
OUTPUT_DIR = AUDIO_FILE.parent
CHUNKS_DIR = OUTPUT_DIR / "_whisper_chunks_20210707053656"
PROGRESS_FILE = OUTPUT_DIR / "20210707053656_TRANSCRIPTION_PROGRESS.json"
COMPLETE_TXT = OUTPUT_DIR / "20210707053656_WHISPER_COMPLETE.txt"
COMPLETE_JSON = OUTPUT_DIR / "20210707053656_WHISPER_COMPLETE.json"

CHUNK_DURATION = 60  # seconds
OVERLAP = 2          # seconds overlap
TOTAL_CHUNKS = 243
NUM_WORKERS = 4      # 4 parallel worker processes utilizing 16 CPU cores

_worker_model = None
_worker_device = None

def format_timestamp(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def init_worker():
    global _worker_model, _worker_device
    torch.set_num_threads(4)
    _worker_device = "cuda" if torch.cuda.is_available() else "cpu"
    _worker_model = whisper.load_model("small", device=_worker_device)

def update_progress(completed_count, failed_count, last_chunk_num, is_final=False):
    pct = (completed_count / TOTAL_CHUNKS) * 100.0 if TOTAL_CHUNKS > 0 else 0
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    progress_data = {
        "total_chunks": TOTAL_CHUNKS,
        "completed_chunks": completed_count,
        "failed_chunks": failed_count,
        "last_successfully_processed_chunk": last_chunk_num,
        "percentage_complete": round(pct, 2),
        "status": "100% COMPLETE" if is_final and completed_count == TOTAL_CHUNKS else "IN PROGRESS",
        "date_and_time_last_updated": now_str,
        "parallel_workers": NUM_WORKERS
    }
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, indent=2)
    print(f"[PROGRESS UPDATE]: {completed_count}/{TOTAL_CHUNKS} completed ({pct:.1f}%)", flush=True)

def prepare_chunks():
    CHUNKS_DIR.mkdir(exist_ok=True, parents=True)
    
    try:
        with wave.open(str(AUDIO_FILE), 'rb') as wf:
            total_duration = wf.getnframes() / float(wf.getframerate())
    except Exception:
        total_duration = 14553.0

    existing_wavs = list(CHUNKS_DIR.glob("chunk_*.wav"))
    if len(existing_wavs) < TOTAL_CHUNKS:
        print(f"Preparing {TOTAL_CHUNKS} WAV chunks via ffmpeg...", flush=True)
        for i in range(1, TOTAL_CHUNKS + 1):
            chunk_file = CHUNKS_DIR / f"chunk_{i:04d}.wav"
            if not chunk_file.exists():
                start_sec = (i - 1) * CHUNK_DURATION
                duration = CHUNK_DURATION + (OVERLAP if i < TOTAL_CHUNKS else 0)
                cmd = [
                    "ffmpeg", "-y", "-ss", str(start_sec), "-t", str(duration),
                    "-i", str(AUDIO_FILE),
                    "-ac", "1", "-ar", "16000", str(chunk_file)
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
    print(f"All {TOTAL_CHUNKS} chunk WAV files are verified in {CHUNKS_DIR}.", flush=True)
    return total_duration

def load_wav_pcm_float(wav_path):
    with wave.open(str(wav_path), 'rb') as wf:
        n_frames = wf.getnframes()
        frames = wf.readframes(n_frames)
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        return audio

def process_single_chunk(chunk_num):
    global _worker_model, _worker_device
    chunk_wav = CHUNKS_DIR / f"chunk_{chunk_num:04d}.wav"
    chunk_json = CHUNKS_DIR / f"chunk_{chunk_num:04d}.json"
    chunk_txt = CHUNKS_DIR / f"chunk_{chunk_num:04d}.txt"

    if chunk_json.exists():
        try:
            with open(chunk_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("processing_status") == "completed":
                    print(f"Chunk {chunk_num}/{TOTAL_CHUNKS} already completed on disk. Skipping.", flush=True)
                    return data
        except Exception:
            pass

    start_time_sec = (chunk_num - 1) * CHUNK_DURATION
    end_time_sec = start_time_sec + CHUNK_DURATION + (OVERLAP if chunk_num < TOTAL_CHUNKS else 0)

    for attempt in range(1, 4):
        try:
            print(f"Processing chunk {chunk_num} of {TOTAL_CHUNKS} (Attempt {attempt})...", flush=True)
            audio = load_wav_pcm_float(chunk_wav)
            sample_rate = 16000
            window_samples = 30 * sample_rate
            
            chunk_segments = []
            texts = []
            options = whisper.DecodingOptions(fp16=False, language="en")

            num_windows = int(np.ceil(len(audio) / window_samples))
            for w in range(num_windows):
                w_start_sample = w * window_samples
                w_end_sample = min((w + 1) * window_samples, len(audio))
                w_audio = audio[w_start_sample:w_end_sample]
                
                if len(w_audio) == 0:
                    continue
                    
                w_padded = whisper.pad_or_trim(w_audio)
                mel = whisper.log_mel_spectrogram(w_padded).to(_worker_device)
                res = _worker_model.decode(mel, options)
                
                w_text = res.text.strip()
                if w_text and w_text != "[BLANK_AUDIO]":
                    w_abs_start = start_time_sec + (w * 30)
                    w_abs_end = min(start_time_sec + ((w + 1) * 30), end_time_sec)
                    chunk_segments.append({
                        "start": round(w_abs_start, 2),
                        "end": round(w_abs_end, 2),
                        "text": w_text
                    })
                    texts.append(w_text)

            raw_text = " ".join(texts)

            chunk_data = {
                "chunk_number": chunk_num,
                "start_time": format_timestamp(start_time_sec),
                "end_time": format_timestamp(end_time_sec),
                "start_sec": start_time_sec,
                "end_sec": end_time_sec,
                "transcript_text": raw_text,
                "segments": chunk_segments,
                "processing_status": "completed",
                "detected_language": "en",
                "model_used": "small",
                "device_used": _worker_device
            }

            with open(chunk_json, "w", encoding="utf-8") as fj:
                json.dump(chunk_data, fj, indent=2)

            with open(chunk_txt, "w", encoding="utf-8") as ft:
                ft.write(f"Chunk {chunk_num} [{format_timestamp(start_time_sec)} -> {format_timestamp(end_time_sec)}]\n")
                for s in chunk_segments:
                    ft.write(f"[{format_timestamp(s['start'])} -> {format_timestamp(s['end'])}] {s['text']}\n")

            print(f" Chunk {chunk_num}/{TOTAL_CHUNKS} COMPLETED!", flush=True)
            return chunk_data

        except Exception as e:
            print(f" Error processing chunk {chunk_num} (Attempt {attempt}): {e}", flush=True)
            time.sleep(1)

    failed_data = {
        "chunk_number": chunk_num,
        "start_time": format_timestamp(start_time_sec),
        "end_time": format_timestamp(end_time_sec),
        "start_sec": start_time_sec,
        "end_sec": end_time_sec,
        "transcript_text": "[FAILED CHUNK]",
        "segments": [],
        "processing_status": "failed",
        "detected_language": "en",
        "model_used": "small",
        "device_used": _worker_device
    }
    with open(chunk_json, "w", encoding="utf-8") as fj:
        json.dump(failed_data, fj, indent=2)
    return failed_data

def merge_transcripts(all_chunks, total_duration):
    print("\nMerging all 243 chunk transcripts in chronological order...", flush=True)
    all_chunks.sort(key=lambda c: c["chunk_number"])

    merged_segments = []
    seen_keys = set()

    for chunk in all_chunks:
        if chunk.get("processing_status") != "completed":
            continue
        for seg in chunk.get("segments", []):
            txt = seg["text"].strip()
            key = f"{round(seg['start'])}_{txt[:30]}"
            if key not in seen_keys:
                seen_keys.add(key)
                merged_segments.append(seg)

    lines = []
    lines.append(f"File: 20210707053656.WAV")
    lines.append(f"Engine: Official OpenAI Whisper Neural Model ('small')")
    lines.append(f"Hardware Acceleration: Multi-Process CPU ({NUM_WORKERS} Workers)")
    lines.append(f"Total Duration: {total_duration / 60.0:.2f} minutes ({format_timestamp(total_duration)})")
    lines.append(f"Total Chunks Processed: {len(all_chunks)} / {TOTAL_CHUNKS}")
    lines.append(f"Date & Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("\n" + "=" * 60 + "\n")
    lines.append("--- CHRONOLOGICAL TIMESTAMPED TRANSCRIPT ---\n")

    full_text_list = []
    for s in merged_segments:
        lines.append(f"[{format_timestamp(s['start'])} -> {format_timestamp(s['end'])}] {s['text']}")
        full_text_list.append(s["text"])

    lines.append("\n" + "=" * 60 + "\n")
    lines.append("--- FULL CONTINUOUS TRANSCRIPT ---\n")
    lines.append(" ".join(full_text_list))

    with open(COMPLETE_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    complete_json_data = {
        "audio_file": "20210707053656.WAV",
        "total_chunks": TOTAL_CHUNKS,
        "completed_chunks": len([c for c in all_chunks if c.get("processing_status") == "completed"]),
        "failed_chunks": len([c for c in all_chunks if c.get("processing_status") == "failed"]),
        "total_duration_minutes": round(total_duration / 60.0, 2),
        "model_used": "small",
        "device_used": "cpu",
        "parallel_workers": NUM_WORKERS,
        "chunks": all_chunks,
        "merged_transcript": " ".join(full_text_list)
    }

    with open(COMPLETE_JSON, "w", encoding="utf-8") as f:
        json.dump(complete_json_data, f, indent=2)

    print(f"Saved complete readable transcript to: {COMPLETE_TXT}", flush=True)
    print(f"Saved complete JSON transcript to: {COMPLETE_JSON}", flush=True)

def main():
    total_duration = prepare_chunks()
    
    # Check existing completed chunks on disk
    all_chunks = {}
    for i in range(1, TOTAL_CHUNKS + 1):
        chunk_json = CHUNKS_DIR / f"chunk_{i:04d}.json"
        if chunk_json.exists():
            try:
                with open(chunk_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("processing_status") == "completed":
                        all_chunks[i] = data
            except Exception:
                pass

    completed_count = len(all_chunks)
    update_progress(completed_count, 0, completed_count)

    pending_chunks = [i for i in range(1, TOTAL_CHUNKS + 1) if i not in all_chunks]
    print(f"Starting 4-worker parallel transcription ({len(pending_chunks)} chunks remaining)...", flush=True)

    if pending_chunks:
        with ProcessPoolExecutor(max_workers=NUM_WORKERS, initializer=init_worker) as executor:
            future_to_chunk = {executor.submit(process_single_chunk, i): i for i in pending_chunks}
            for future in as_completed(future_to_chunk):
                c_num = future_to_chunk[future]
                try:
                    c_data = future.result()
                    all_chunks[c_num] = c_data
                except Exception as e:
                    print(f"Unhandled error in chunk {c_num}: {e}", flush=True)
                
                comp_cnt = len([c for c in all_chunks.values() if c.get("processing_status") == "completed"])
                fail_cnt = len([c for c in all_chunks.values() if c.get("processing_status") == "failed"])
                update_progress(comp_cnt, fail_cnt, c_num)

    all_chunks_list = list(all_chunks.values())
    update_progress(len(all_chunks_list), 0, TOTAL_CHUNKS, is_final=True)
    merge_transcripts(all_chunks_list, total_duration)

    print("\n" + "=" * 60, flush=True)
    print("TRANSCRIPTION PIPELINE COMPLETE!", flush=True)
    print(f" Successful Chunks: {len(all_chunks_list)} / {TOTAL_CHUNKS}", flush=True)
    print(f" Final Transcript: {COMPLETE_TXT}", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()
