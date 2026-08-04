import os
import sys
import wave
import json
import time
import math
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import vosk

_shared_vosk_model = None

def get_vosk_model():
    global _shared_vosk_model
    if _shared_vosk_model is None:
        model_dir = Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us-0.15"
        print("Loading Vosk Continuous Neural Acoustic Engine (en-us)...")
        _shared_vosk_model = vosk.Model(str(model_dir))
    return _shared_vosk_model

def write_live_vosk(txt_path, wav_name, size_mb, results, completed_count, total_chunks, is_final=False):
    ordered_timed = []
    ordered_text = []
    for idx in sorted(results.keys()):
        t_str, text_s = results[idx]
        if t_str:
            ordered_timed.append(t_str)
            ordered_text.append(text_s)

    combined_text = " ".join(ordered_text)
    if not combined_text and is_final:
        combined_text = "[No speech recognized by Vosk acoustic engine]"

    status_str = "COMPLETE" if is_final else f"IN PROGRESS ({completed_count}/{total_chunks} chunks completed - {completed_count/total_chunks*100:.1f}%)"

    with open(txt_path, "w", encoding="utf-8") as tf:
        tf.write(f"File: {wav_name}\n")
        tf.write(f"Engine: Vosk Continuous Neural Acoustic Engine (en-us)\n")
        tf.write(f"Status: {status_str}\n")
        tf.write(f"Size: {size_mb:.2f} MB\n\n")
        tf.write("--- TIMED CONVERSATIONAL SEGMENTS (VOSK LIVE) ---\n")
        tf.write("\n".join(ordered_timed) if ordered_timed else "(Listening / room quiet in completed chunks so far...)\n")
        tf.write("\n\n--- FULL TRANSCRIPT (VOSK LIVE) ---\n")
        tf.write(combined_text)
        tf.flush()

    return combined_text

def transcribe_wav_with_vosk(wav_path, chunk_sec=60):
    size_mb = wav_path.stat().st_size / (1024 * 1024)
    txt_out = wav_path.with_name(f"{wav_path.stem}_VOSK.txt")

    print(f"\n==========================================")
    print(f"Vosk Continuous Acoustic Engine: {wav_path.name} ({size_mb:.2f} MB)")
    print(f"==========================================")

    start_t = time.time()
    chunks_dir = wav_path.parent / f"_temp_vosk_chunks_{wav_path.stem}"
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
    print(f" Generated {total_chunks} chunks. Transcribing with Vosk acoustic engine...")

    model = get_vosk_model()
    results = {}
    write_live_vosk(txt_out, wav_path.name, size_mb, results, 0, total_chunks)

    for idx, cf_path in enumerate(chunk_files):
        s_s = idx * chunk_sec
        e_s = s_s + chunk_sec
        try:
            wf = wave.open(str(cf_path), "rb")
            rec = vosk.KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)

            full_parts = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    txt = res.get("text", "").strip()
                    if txt:
                        full_parts.append(txt)

            final_res = json.loads(rec.FinalResult())
            txt_final = final_res.get("text", "").strip()
            if txt_final:
                full_parts.append(txt_final)

            wf.close()
            text = " ".join(full_parts)
            if text:
                s_m = s_s / 60.0
                e_m = e_s / 60.0
                results[idx] = (f"[{s_m:.2f}m -> {e_m:.2f}m] {text}", text)
        except Exception as e:
            pass

        completed_count = idx + 1
        # Live update file after every single chunk!
        write_live_vosk(txt_out, wav_path.name, size_mb, results, completed_count, total_chunks)

        if completed_count % 15 == 0 or completed_count == total_chunks:
            pct = (completed_count / total_chunks) * 100
            print(f"  Vosk Progress {wav_path.name}: {completed_count}/{total_chunks} chunks ({pct:.1f}%) done...")

    final_text = write_live_vosk(txt_out, wav_path.name, size_mb, results, total_chunks, total_chunks, is_final=True)
    elapsed = time.time() - start_t
    print(f" Finished {wav_path.name} in {elapsed:.2f} seconds ({len(results)} conversational segments found)!")

    shutil.rmtree(chunks_dir, ignore_errors=True)
    return txt_out

def main():
    folder = Path(r"C:\Users\crice\Downloads\USB_Recordings")
    target_file = None

    if len(sys.argv) > 1:
        t = Path(sys.argv[1])
        if t.is_file():
            target_file = t

    if target_file:
        transcribe_wav_with_vosk(target_file)
    else:
        audio_files = [f for f in folder.glob("*.WAV") if f.stat().st_size > 50 * 1024 * 1024]
        audio_files.sort(key=lambda f: f.stat().st_size)
        for f in audio_files:
            transcribe_wav_with_vosk(f)

if __name__ == "__main__":
    main()
