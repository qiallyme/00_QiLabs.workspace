import os
import sys
import wave
import json
import subprocess
from pathlib import Path
import vosk

def transcribe_with_vosk(wav_file, duration_sec=120, start_sec=0):
    wav_path = Path(wav_file)
    if not wav_path.exists():
        print(f"File {wav_path} not found.")
        return

    print(f"\n==========================================")
    print(f"Testing Vosk Multi-Speaker Speech Recognition")
    print(f"Target: {wav_path.name} (Segment {start_sec}s -> {start_sec+duration_sec}s)")
    print(f"==========================================")

    # Extract segment as mono 16kHz PCM WAV
    temp_wav = wav_path.parent / f"_temp_vosk_{wav_path.stem}.wav"
    cmd = [
        "ffmpeg", "-y", "-ss", str(start_sec), "-t", str(duration_sec),
        "-i", str(wav_path), "-ac", "1", "-ar", "16000", str(temp_wav)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not temp_wav.exists():
        print("Failed to extract audio segment.")
        return

    # Load Vosk model (en-us)
    print("Loading Vosk Model (en-us)...")
    try:
        model = vosk.Model(lang="en-us")
    except Exception as e:
        print(f"Error loading Vosk model: {e}")
        return

    wf = wave.open(str(temp_wav), "rb")
    rec = vosk.KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    results = []
    full_text_parts = []

    print("Transcribing continuous audio stream...")
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            text = res.get("text", "").strip()
            if text:
                full_text_parts.append(text)
                print(f"  [Vosk]: {text}")

    final_res = json.loads(rec.FinalResult())
    text_final = final_res.get("text", "").strip()
    if text_final:
        full_text_parts.append(text_final)
        print(f"  [Vosk Final]: {text_final}")

    wf.close()
    temp_wav.unlink(missing_ok=True)

    full_transcript = " ".join(full_text_parts)
    print(f"\nFULL VOSK TRANSCRIPT:\n{full_transcript if full_transcript else '[No speech detected]'}\n")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\crice\Downloads\USB_Recordings\20210707053656.WAV"
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    transcribe_with_vosk(target, duration_sec=180, start_sec=start)
