#!/usr/bin/env python
"""Volume + silence-trim each T8 take, then concat toward 90s."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


FFMPEG = Path(r"C:\ffmpeg\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ffmpeg\bin\ffprobe.exe")
ASR = Path(r"C:\Users\steven\AppData\Local\hermes\skills\media\asr\scripts\asr.py")


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        [str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        check=True, stdout=subprocess.PIPE, text=True,
    )
    return float(out.stdout.strip())


def volumedetect(path: Path) -> dict:
    proc = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    mean = maxv = None
    for line in proc.stdout.splitlines():
        if "mean_volume" in line:
            mean = float(line.rsplit(":", 1)[-1].replace("dB", "").strip())
        if "max_volume" in line:
            maxv = float(line.rsplit(":", 1)[-1].replace("dB", "").strip())
    return {"mean_db": mean, "max_db": maxv}


def speech_window(path: Path, threshold_db: float = -32.0) -> tuple[float, float]:
    """Return first/last time the clip is louder than threshold. Trailing-only trim."""
    proc = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(path),
         "-af", f"silencedetect=noise={threshold_db}dB:d=0.12", "-f", "null", "-"],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    duration = probe_duration(path)
    silences = []
    start = None
    for line in proc.stdout.splitlines():
        if "silence_start:" in line:
            start = float(line.rsplit("silence_start:", 1)[-1].split()[0])
        elif "silence_end:" in line and start is not None:
            end = float(line.rsplit("silence_end:", 1)[-1].split("|")[0].split()[0])
            silences.append((start, end))
            start = None
    if start is not None:
        silences.append((start, duration))
    speech_start = 0.0
    speech_end = duration
    if silences and silences[0][0] <= 0.05:
        speech_start = silences[0][1]
    if silences and silences[-1][1] >= duration - 0.05:
        speech_end = silences[-1][0]
    if speech_end <= speech_start + 0.25:
        return 0.0, duration
    return max(0.0, speech_start - 0.08), min(duration, speech_end + 1.05)


def trim_take(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    start, end = speech_window(src)
    subprocess.run(
        [str(FFMPEG), "-hide_banner", "-y", "-i", str(src),
         "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
         "-af", "alimiter=limit=0.89", "-ar", "32000", "-ac", "1", str(dest)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )


def asr_text(wav: Path) -> str:
    proc = subprocess.run(
        ["python", str(ASR), str(wav), "--lang", "zh"],
        check=True, stdout=subprocess.PIPE, text=True,
    )
    text = proc.stdout
    if "=== TRANSCRIPT ===" in text:
        text = text.split("=== TRANSCRIPT ===", 1)[1]
        text = text.split("=== OUTPUTS ===", 1)[0]
    return re.sub(r"\s+", "", text).strip()


def normalize(s: str) -> str:
    table = str.maketrans({
        "，": "", "。": "", "？": "", "、": "", "！": "",
        ",": "", ".": "", "?": "", "!": "", " ": "",
        "妳": "你", "臺": "台",
    })
    return s.translate(table).replace("这里", "這裡").replace("什么", "什麼")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--gap", type=float, default=0.92)
    parser.add_argument("--skip-asr", action="store_true")
    args = parser.parse_args()
    project = Path(args.project)
    sketch = json.loads((project / "01_sources" / "sketch.json").read_text(encoding="utf-8"))
    report = []
    trimmed = []
    for segment in sketch["segments"]:
        src = project / "04_audio" / f"seg_{segment['id']:02d}_t8_20step.wav"
        if not src.exists():
            raise FileNotFoundError(src)
        dest = project / "04_audio" / f"seg_{segment['id']:02d}_trim.wav"
        trim_take(src, dest)
        vol = volumedetect(src)
        item = {
            "id": segment["id"],
            "speaker": segment["speaker"],
            "beat": segment.get("beat"),
            "text": segment["text"],
            "raw_seconds": round(probe_duration(src), 3),
            "trim_seconds": round(probe_duration(dest), 3),
            **vol,
        }
        if not args.skip_asr:
            heard = asr_text(src)
            item["asr"] = heard
            item["match"] = normalize(heard) == normalize(segment["text"]) or (
                normalize(segment["text"]) in normalize(heard)
            )
        report.append(item)
        trimmed.append(dest)

    gap = project / "04_audio" / "gap.wav"
    subprocess.run(
        [str(FFMPEG), "-hide_banner", "-y", "-f", "lavfi",
         "-i", f"anullsrc=r=32000:cl=mono", "-t", str(args.gap), str(gap)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    concat_list = project / "07_metadata" / "concat_trim.txt"
    files = []
    for i, wav in enumerate(trimmed):
        files.append(f"file '{wav.resolve().as_posix()}'")
        if i < len(trimmed) - 1:
            files.append(f"file '{gap.resolve().as_posix()}'")
    concat_list.write_text("\n".join(files) + "\n", encoding="utf-8")
    final = project / "05_final" / f"{sketch['sketch_id']}_90s.wav"
    final.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(FFMPEG), "-hide_banner", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-ar", "32000", "-ac", "1", str(final)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    duration = probe_duration(final)
    out = {
        "final": str(final),
        "duration": duration,
        "target": sketch.get("target_seconds", 90),
        "segments": report,
    }
    (project / "07_metadata" / "qa_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
