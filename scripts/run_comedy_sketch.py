#!/usr/bin/env python
"""Generate a MiniMax H3 T8 comedy-sketch voice track, one speaker per clip."""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


COMFY_URL = "http://127.0.0.1:8188"
COMFY_ROOT = Path(r"E:\minimax-h3\ComfyUI")
DEFAULT_OUT = Path(r"E:\h3cspeed\output")
FFMPEG = Path(r"C:\ffmpeg\bin\ffmpeg.exe")
FFPROBE = Path(r"C:\ffmpeg\bin\ffprobe.exe")
FPS = 24
MIN_FRAMES = 124
MAX_FRAMES = 362
SPACE = (
    "a real furnished room, physically close to the listener, with subtle natural "
    "early reflections and intimate microphone perspective"
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        COMFY_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(path: str) -> dict:
    with urllib.request.urlopen(COMFY_URL + path, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def align_frames(seconds: float) -> int:
    frames = int(math.ceil(float(seconds) * FPS - 1e-9))
    # H3 trained window; keep even-ish alignment similar to T8 align_frame_count
    if frames % 4:
        frames += 4 - (frames % 4)
    return max(MIN_FRAMES, min(MAX_FRAMES, frames))


def speech_prompt(voice_description: str, direction: str, text: str, language: str) -> str:
    acting = "; ".join(part for part in (voice_description.strip(), direction.strip()) if part)
    return f"""integrated_multimodal_description:
[Shot 1] A static featureless dark scene in {SPACE}. A single adult speaker (S1) performs one clean voice take. Voice identity and acting direction only, never spoken aloud: {acting}. The performance is emotionally present, spontaneous, and unmistakably human, with connected phrasing, natural breaths, small timing variations, and no announcer or synthetic TTS cadence. Only the words inside the following dialogue block are audible. Speaker 1 (S1) says exactly and only: <d>[{language}] {text}</d> After the final word, the speaker closes their mouth. No label, voice description, acting note, instruction, or other prompt prose is spoken.

overall_soundscape:
Subtle room tone and believable close-microphone presence from the specified space. No music, effects, other voices, or speech outside the marked dialogue.

non_diegetic_music:
N/A
"""


def build_graph(prefix: str, prompt: str, frames: int, seed: int) -> dict:
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
            "weight_dtype": "default",
        }},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
            "type": "minimax", "device": "default",
        }},
        "3": {"class_type": "VAELoader", "inputs": {
            "vae_name": "minimax_h3_video_vae_fp16.safetensors",
        }},
        "4": {"class_type": "VAELoader", "inputs": {
            "vae_name": "minimax_h3_audio_vae_fp32.safetensors",
        }},
        "6": {"class_type": "MiniMaxH3AudioConditioningT8", "inputs": {
            "clip": ["2", 0], "video_vae": ["3", 0], "audio_vae": ["4", 0],
            "prompt": prompt, "width": 64, "height": 64, "length": frames,
            "task_type": "T2VA", "audio_mode": "native",
            "audio_denoise_strength": 1.0, "add_source_as_reference": False,
            "prompt_primary_audio_ordinal": 0, "strict_prompt_tags": True,
            "ref_image_size": "match", "reference_video_policy": "official_2_to_15s",
        }},
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "10": {"class_type": "MiniMaxH3DualClockSamplerT8", "inputs": {
            "model": ["1", 0], "av_latent": ["6", 1], "steps": 20,
            "shift_video": 12.0, "shift_audio": 3.0,
            "sampler_name": "dual_clock_euler", "scheduler": "native_flow",
        }},
        "12": {"class_type": "BasicGuider", "inputs": {
            "model": ["10", 0], "conditioning": ["6", 0],
        }},
        "13": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["9", 0], "guider": ["12", 0], "sampler": ["10", 1],
            "sigmas": ["10", 2], "latent_image": ["6", 1],
        }},
        "15": {"class_type": "MiniMaxH3SpeechDecodeT8", "inputs": {
            "av_latent": ["13", 0], "audio_vae": ["4", 0],
            "trim_mode": "none", "energy_threshold_dbfs": -50.0,
            "trim_padding_seconds": 0.10,
        }},
        "18": {"class_type": "SaveAudio", "inputs": {
            "audio": ["15", 0], "filename_prefix": prefix,
        }},
    }


def wait_for_prompt(prompt_id: str) -> dict:
    while True:
        history = get_json(f"/history/{prompt_id}")
        result = history.get(prompt_id)
        if result:
            status = result.get("status", {})
            if status.get("status_str") in {"success", "error"} or result.get("outputs"):
                if status.get("status_str") == "error":
                    raise RuntimeError(json.dumps(result, ensure_ascii=False)[:8000])
                return result
        time.sleep(15)


def locate_saved_audio(comfy_prefix: str, stem: str) -> Path:
    folder = COMFY_ROOT / "output" / comfy_prefix / "04_audio"
    candidates = []
    for pattern in (stem + "*.flac", stem + "*.wav", stem + "*.mp3"):
        candidates.extend(folder.glob(pattern))
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"no T8 speech audio found for {stem} in {folder}")
    return candidates[0]


def append_progress(project: Path, record: dict) -> None:
    path = project / "07_metadata" / "segment-progress.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_segment(sketch: dict, segment: dict, project: Path) -> Path:
    voices = sketch["voices"]
    voice = voices[segment["speaker"]]
    language = sketch.get("language", "Chinese")
    frames = align_frames(segment.get("render_seconds", 10))
    prompt = speech_prompt(voice["description"], segment["direction"], segment["text"], language)
    stem = f"seg_{segment['id']:02d}_t8_20step"
    comfy_prefix = sketch["sketch_id"]
    prefix = f"{comfy_prefix}/04_audio/{stem}"
    prompt_path = project / "02_prompts" / f"{stem}.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    seed_offset = int(segment.get("_seed_offset", 0))
    graph = build_graph(prefix, prompt, frames, seed=2026081900 + int(segment["id"]) + seed_offset)
    payload = {
        "prompt": graph,
        "client_id": f"hermes-{comfy_prefix}-t8",
        "extra_data": {"extra_pnginfo": {
            "project": comfy_prefix, "segment": segment["id"], "steps": 20,
            "sampler": "dual_clock_euler", "scheduler": "native_flow",
            "speech": True, "turbo_lora": False, "mode": "t8-speech",
            "beat": segment.get("beat"), "speaker": segment["speaker"],
        }},
    }
    started = time.time()
    response = post_json("/prompt", payload)
    prompt_id = response["prompt_id"]
    append_progress(project, {
        "time": now(), "segment": segment["id"], "status": "queued",
        "mode": "t8-speech", "prompt_id": prompt_id, "frames": frames,
        "text": segment["text"],
    })
    try:
        wait_for_prompt(prompt_id)
    except Exception as exc:
        append_progress(project, {
            "time": now(), "segment": segment["id"], "status": "error",
            "mode": "t8-speech", "prompt_id": prompt_id,
            "elapsed_seconds": round(time.time() - started, 3), "error": str(exc),
        })
        raise
    source = locate_saved_audio(comfy_prefix, stem)
    destination = project / "04_audio" / f"{stem}.wav"
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(FFMPEG), "-hide_banner", "-y", "-i", str(source),
         "-ac", "1", "-ar", "32000", str(destination)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    append_progress(project, {
        "time": now(), "segment": segment["id"], "status": "completed",
        "mode": "t8-speech", "prompt_id": prompt_id,
        "elapsed_seconds": round(time.time() - started, 3),
        "source": str(source), "wav": str(destination),
    })
    return destination


def write_concat(project: Path, wavs: list[Path]) -> Path:
    concat = project / "07_metadata" / "concat.txt"
    lines = [f"file '{wav.resolve().as_posix()}'" for wav in wavs]
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return concat


def assemble(project: Path, wavs: list[Path], sketch_id: str) -> Path:
    concat = write_concat(project, wavs)
    final = project / "05_final" / f"{sketch_id}_90s.wav"
    final.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(FFMPEG), "-hide_banner", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat), "-c:a", "pcm_s16le", "-ar", "32000", "-ac", "1", str(final)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return final


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sketch", required=True)
    parser.add_argument("--from-segment", type=int, default=1)
    parser.add_argument("--to-segment", type=int, default=0)
    parser.add_argument("--only-segments", default="", help="comma list, e.g. 7,11")
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--assemble-only", action="store_true")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    sketch = json.loads(Path(args.sketch).read_text(encoding="utf-8"))
    project = Path(args.out_root) / sketch["sketch_id"]
    for name in ("01_sources", "02_prompts", "04_audio", "05_final", "07_metadata"):
        (project / name).mkdir(parents=True, exist_ok=True)
    (project / "01_sources" / "sketch.json").write_text(
        json.dumps(sketch, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    segments = list(sketch["segments"])
    only = {int(x) for x in args.only_segments.split(",") if x.strip()} if args.only_segments else set()
    last = args.to_segment or max(s["id"] for s in segments)
    wavs: list[Path] = []
    if not args.assemble_only:
        get_json("/system_stats")
    for segment in segments:
        segment = dict(segment)
        segment["_seed_offset"] = args.seed_offset
        dest = project / "04_audio" / f"seg_{segment['id']:02d}_t8_20step.wav"
        if only and segment["id"] not in only:
            if dest.exists():
                wavs.append(dest)
            continue
        if not only and (segment["id"] < args.from_segment or segment["id"] > last):
            if dest.exists():
                wavs.append(dest)
            continue
        if args.assemble_only or (args.resume and dest.exists()):
            if not dest.exists():
                raise FileNotFoundError(dest)
            print(json.dumps({"segment": segment["id"], "skipped": str(dest)}, ensure_ascii=False), flush=True)
            wavs.append(dest)
            continue
        dest = run_segment(sketch, segment, project)
        print(json.dumps({"segment": segment["id"], "completed": str(dest)}, ensure_ascii=False), flush=True)
        wavs.append(dest)
    if wavs and (args.assemble_only or args.from_segment == 1 and last >= max(s["id"] for s in segments)):
        final = assemble(project, wavs, sketch["sketch_id"])
        probe = subprocess.run(
            [str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(final)],
            check=True, stdout=subprocess.PIPE, text=True,
        )
        print(json.dumps({"final": str(final), "duration": probe.stdout.strip()}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
