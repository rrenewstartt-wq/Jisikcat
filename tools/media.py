#!/usr/bin/env python3
"""Build comparable, inspectable observations for the editorial desk."""
import argparse
import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path

CHANNEL = "UCi9Sl8GnFdYoqEVXnojBPJw"
CLOCK = r"(?:\d{1,}:)?\d{2}:\d{2}[.,]\d{3}"


def run(*args, binary=False):
    result = subprocess.run(args, capture_output=True, text=not binary)
    if result.returncode:
        error = result.stderr.decode(errors="replace") if binary else result.stderr
        raise ValueError(error.strip() or f"{args[0]} failed")
    return result.stdout


def sample(args):
    url = f"https://www.youtube.com/channel/{args.channel}/{args.format}"
    listing = run("yt-dlp", "--flat-playlist", "--dump-json", "--ignore-config",
                  "--playlist-end", str(args.limit), "--", url)
    entries = [json.loads(line) for line in listing.splitlines() if line.strip()]
    if not entries:
        raise ValueError("No videos returned for this channel tab")
    return {"channel_tab": url, "selection": "first entries in returned tab order",
            "videos": [{"url": f"https://www.youtube.com/watch?v={entry['id']}",
                        "title": entry.get("title"), "duration_s": entry.get("duration"),
                        "views": entry.get("view_count")} for entry in entries]}


def seconds(clock):
    parts = [float(part.replace(",", ".")) for part in clock.split(":")]
    return sum(value * 60 ** power for power, value in enumerate(reversed(parts)))


def caption_metrics(path):
    content = Path(path).read_text(encoding="utf-8-sig")
    cues = []
    for block in re.split(r"\n\s*\n", content.strip()):
        match = re.search(rf"^({CLOCK})\s+-->\s+({CLOCK})[^\n]*\n", block, re.M)
        if not match:
            continue
        start, end = (seconds(value) for value in match.groups())
        if end <= start:
            raise ValueError("Invalid caption cue duration")
        lines = [re.sub(r"<[^>]*>", "", line).strip()
                 for line in block[match.end():].splitlines()]
        cues.append((start, end, [line for line in lines if line]))
    if not cues:
        raise ValueError("No timed SRT/VTT cues found")
    return {"cue_count": len(cues),
            "median_duration_s": round(statistics.median(end-start for start,end,_ in cues), 3),
            "median_lines": statistics.median(len(lines) for _,_,lines in cues),
            "median_chars_per_cue": statistics.median(
                sum(len(line) for line in lines) for _,_,lines in cues)}


def thumbnail_metrics(path):
    probe = json.loads(run("ffprobe", "-v", "error", "-select_streams", "v:0",
                           "-show_entries", "stream=width,height", "-of", "json", path))
    dims = probe["streams"][0]
    gray = run("ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-vf",
               "scale=160:90:flags=area,format=gray", "-f", "rawvideo", "-", binary=True)
    if len(gray) != 160 * 90:
        raise ValueError("Thumbnail could not be decoded")
    return {**dims, "mean_gray_0_255": round(statistics.mean(gray), 1),
            "gray_stddev": round(statistics.pstdev(gray), 1),
            "dark_fraction_lt64": round(sum(x < 64 for x in gray)/len(gray), 3),
            "bright_fraction_ge192": round(sum(x >= 192 for x in gray)/len(gray), 3)}


def scene_metrics(path, threshold):
    probe = json.loads(run("ffprobe", "-v", "error", "-select_streams", "v:0",
                           "-show_entries", "stream=start_time,duration,width,height:format=duration",
                           "-of", "json", path))
    if not probe["streams"]:
        raise ValueError("No video stream")
    stream = probe["streams"][0]
    duration = float(stream.get("duration") or probe["format"]["duration"])
    metadata = run("ffmpeg", "-nostdin", "-v", "error", "-i", path, "-map", "0:v:0",
                   "-an", "-vf", f"setpts=PTS-STARTPTS,scale=320:-2,select='gt(scene,{threshold})',metadata=print:file=-",
                   "-f", "null", "-")
    cuts = sorted({float(t) for t in re.findall(r"pts_time:([0-9.eE+-]+)", metadata)
                   if 0 < float(t) < duration})
    edges = [0, *cuts, duration]
    return {"duration_s": duration, "width": stream["width"], "height": stream["height"],
            "scene_threshold": threshold, "candidate_cut_seconds": cuts,
            "median_candidate_shot_s": round(statistics.median(
                b-a for a,b in zip(edges, edges[1:])), 3)}


def analyze(args):
    result = {"source": args.source, "input_video": Path(args.video).name,
              "video": scene_metrics(args.video, args.threshold)}
    if args.thumbnail:
        result["thumbnail"] = thumbnail_metrics(args.thumbnail)
    if args.captions:
        result["captions"] = caption_metrics(args.captions)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(required=True)
    listing = commands.add_parser("sample", help="Read channel tab metadata with yt-dlp")
    listing.set_defaults(fn=sample)
    listing.add_argument("--channel", default=CHANNEL)
    listing.add_argument("--format", choices=["videos", "shorts"], default="videos")
    listing.add_argument("--limit", type=int, default=12)
    local = commands.add_parser("inspect", help="Measure supplied local media")
    local.set_defaults(fn=analyze)
    local.add_argument("video")
    local.add_argument("--source", required=True, help="Reference URL or local fixture identifier")
    local.add_argument("--thumbnail")
    local.add_argument("--captions")
    local.add_argument("--threshold", type=float, default=.30)
    args = parser.parse_args()
    if args.fn == sample and args.limit < 1:
        parser.error("--limit must be positive")
    if args.fn == analyze and not (math.isfinite(args.threshold) and 0 < args.threshold < 1):
        parser.error("--threshold must be between 0 and 1")
    try:
        print(json.dumps(args.fn(args), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, IndexError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
