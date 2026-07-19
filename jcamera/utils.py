import os
import subprocess
import tempfile
from pathlib import Path


def get_resource_path(relative_path):
    base = Path(__file__).resolve().parent.parent
    return str(base / relative_path)


def get_captures_dir():
    captures = Path.home() / "Pictures" / "JCamera"
    captures.mkdir(parents=True, exist_ok=True)
    return str(captures)


def get_videos_dir():
    videos = Path.home() / "Videos" / "JCamera"
    videos.mkdir(parents=True, exist_ok=True)
    return str(videos)


def list_cameras():
    result = []
    for dev in Path("/dev").glob("video*"):
        try:
            out = subprocess.check_output(
                ["v4l2-ctl", "--list-formats", "--device", str(dev)],
                stderr=subprocess.DEVNULL
            ).decode()
            result.append((str(dev), out[:50]))
        except (subprocess.CalledProcessError, FileNotFoundError):
            result.append((str(dev), "Unknown"))
    return result


def list_audio_sources():
    try:
        out = subprocess.check_output(
            ["pactl", "list", "sources", "--short"],
            stderr=subprocess.DEVNULL
        ).decode()
        return [line.split("\t")[1] for line in out.strip().split("\n") if line]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def get_display_resolution():
    try:
        out = subprocess.check_output(["xdpyinfo"]).decode()
        for line in out.split("\n"):
            if "dimensions" in line:
                res = line.split()[1]
                return res
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "1920x1080"


def ffmpeg_capture_photo(device, output_path, width=1280, height=720, quality=95):
    cmd = [
        "ffmpeg", "-y",
        "-f", "v4l2",
        "-video_size", f"{width}x{height}",
        "-i", device,
        "-vframes", "1",
        "-q:v", str(int((100 - quality) / 10)),
        "-update", "1",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ffmpeg_record_video(device, output_path, width=1280, height=720, fps=30,
                        codec="libx264", audio_source=None, duration=None):
    cmd = ["ffmpeg", "-y"]
    cmd += ["-f", "v4l2", "-video_size", f"{width}x{height}", "-framerate", str(fps), "-i", device]
    if audio_source:
        cmd += ["-f", "pulse", "-i", audio_source]
    cmd += ["-c:v", codec, "-preset", "ultrafast"]
    if audio_source:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [output_path]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ffmpeg_screen_record(output_path, region=None, fps=30, codec="libx264",
                         audio_source=None, duration=None):
    cmd = ["ffmpeg", "-y"]
    if region:
        cmd += ["-video_size", region["size"], "-f", "x11grab",
                "-i", f":0.0+{region['x']},{region['y']}"]
    else:
        res = get_display_resolution()
        cmd += ["-video_size", res, "-f", "x11grab", "-i", ":0.0"]
    cmd += ["-framerate", str(fps)]
    if audio_source:
        cmd += ["-f", "pulse", "-i", audio_source]
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    cmd += ["-c:v", codec, "-preset", "ultrafast"]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [output_path]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
