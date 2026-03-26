"""FFmpeg command builder with preset support and path resolution."""
import os
from typing import Dict, List, Optional
from src.core.config import settings


class FfmpegPaths:
    @staticmethod
    def get_ffmpeg(version: str = "default") -> str:
        versioned = os.path.join(settings.BASE_DIR, "bin", "ffmpeg_bin", version, "ffmpeg")
        if os.path.exists(versioned):
            return versioned
        return settings.FFMPEG_PATH

    @staticmethod
    def get_ffprobe(version: str = "default") -> str:
        versioned = os.path.join(settings.BASE_DIR, "bin", "ffmpeg_bin", version, "ffprobe")
        if os.path.exists(versioned):
            return versioned
        return settings.FFPROBE_PATH


class FFmpegCommand:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg = ffmpeg_path or settings.FFMPEG_PATH
        self._args: List[str] = [self.ffmpeg]

    def input(self, url: str, options: Optional[Dict[str, str]] = None) -> "FFmpegCommand":
        if options:
            for k, v in options.items():
                self._args.extend([f"-{k}", str(v)])
        self._args.extend(["-i", url])
        return self

    def output(self, path: str, options: Optional[Dict[str, str]] = None) -> "FFmpegCommand":
        if options:
            for k, v in options.items():
                self._args.extend([f"-{k}", str(v)])
        self._args.append(path)
        return self

    def codec(self, video: str = "copy", audio: str = "copy") -> "FFmpegCommand":
        self._args.extend(["-c:v", video, "-c:a", audio])
        return self

    def format(self, fmt: str) -> "FFmpegCommand":
        self._args.extend(["-f", fmt])
        return self

    def overwrite(self) -> "FFmpegCommand":
        self._args.append("-y")
        return self

    def no_stats(self) -> "FFmpegCommand":
        self._args.extend(["-nostats", "-hide_banner", "-loglevel", "error"])
        return self

    def read_native(self) -> "FFmpegCommand":
        self._args.insert(1, "-re")
        return self

    def custom(self, args_str: str) -> "FFmpegCommand":
        self._args.extend(args_str.split())
        return self

    def hls(self, output_dir: str, segment_time: int = 2, list_size: int = 6) -> "FFmpegCommand":
        os.makedirs(output_dir, exist_ok=True)
        self._args.extend([
            "-c", "copy", "-f", "hls",
            "-hls_time", str(segment_time),
            "-hls_list_size", str(list_size),
            "-hls_flags", "delete_segments+append_list",
            "-hls_segment_filename", os.path.join(output_dir, "seg_%03d.ts"),
            os.path.join(output_dir, "index.m3u8"),
        ])
        return self

    def build(self) -> List[str]:
        return self._args

    def __str__(self) -> str:
        return " ".join(self._args)
