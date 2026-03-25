"""
Streaming engine - handles live stream proxying, HLS segment delivery,
FFmpeg process management, and stream health monitoring.
"""
import os
import json
import subprocess
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from src.core.config import settings
from src.core.logging.logger import logger


class StreamingEngine:
    def __init__(self):
        self._active_streams: Dict[int, Dict[str, Any]] = {}
        self._ffmpeg_processes: Dict[int, subprocess.Popen] = {}

    def get_ffmpeg_command(self, stream_id: int, source_url: str, output_path: str,
                          container: str = "ts", custom_ffmpeg: Optional[str] = None,
                          read_native: bool = False) -> List[str]:
        cmd = [settings.FFMPEG_PATH]

        if read_native:
            cmd.extend(["-re"])

        cmd.extend([
            "-i", source_url,
            "-y",
            "-nostats",
            "-hide_banner",
            "-loglevel", "error",
        ])

        if custom_ffmpeg:
            cmd.extend(custom_ffmpeg.split())
        else:
            if container == "ts":
                cmd.extend([
                    "-c", "copy",
                    "-f", "mpegts",
                    output_path,
                ])
            elif container == "m3u8":
                hls_dir = os.path.join(settings.CONTENT_DIR, "streams", str(stream_id))
                os.makedirs(hls_dir, exist_ok=True)
                cmd.extend([
                    "-c", "copy",
                    "-f", "hls",
                    "-hls_time", "2",
                    "-hls_list_size", "6",
                    "-hls_flags", "delete_segments+append_list",
                    "-hls_segment_filename", os.path.join(hls_dir, "seg_%03d.ts"),
                    os.path.join(hls_dir, "index.m3u8"),
                ])
            elif container == "rtmp":
                cmd.extend([
                    "-c", "copy",
                    "-f", "flv",
                    output_path,
                ])
        return cmd

    def start_stream(self, stream_id: int, source_url: str, container: str = "ts",
                     custom_ffmpeg: Optional[str] = None, read_native: bool = False,
                     server_id: Optional[int] = None) -> Optional[int]:
        if stream_id in self._active_streams:
            return self._active_streams[stream_id].get("pid")

        output_path = os.path.join(settings.CONTENT_DIR, "streams", str(stream_id))
        os.makedirs(output_path, exist_ok=True)

        if container == "ts":
            out = f"pipe:1"
        elif container == "m3u8":
            out = output_path
        else:
            out = output_path

        cmd = self.get_ffmpeg_command(stream_id, source_url, out, container, custom_ffmpeg, read_native)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if container == "ts" else subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
            )
            self._ffmpeg_processes[stream_id] = proc
            self._active_streams[stream_id] = {
                "pid": proc.pid,
                "source": source_url,
                "container": container,
                "server_id": server_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "output_path": output_path,
            }
            logger.info(f"Started stream {stream_id} (PID: {proc.pid}) from {source_url}")
            return proc.pid
        except Exception as e:
            logger.error(f"Failed to start stream {stream_id}: {e}")
            return None

    def stop_stream(self, stream_id: int) -> bool:
        proc = self._ffmpeg_processes.get(stream_id)
        if not proc:
            return False
        try:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            del self._ffmpeg_processes[stream_id]
            del self._active_streams[stream_id]
            logger.info(f"Stopped stream {stream_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop stream {stream_id}: {e}")
            return False

    def restart_stream(self, stream_id: int) -> Optional[int]:
        info = self._active_streams.get(stream_id)
        if not info:
            return None
        self.stop_stream(stream_id)
        return self.start_stream(
            stream_id, info["source"], info["container"],
            server_id=info.get("server_id"),
        )

    def is_active(self, stream_id: int) -> bool:
        proc = self._ffmpeg_processes.get(stream_id)
        if not proc:
            return False
        return proc.poll() is None

    def get_active_streams(self) -> Dict[int, Dict[str, Any]]:
        result = {}
        for sid, info in self._active_streams.items():
            result[sid] = {
                **info,
                "running": self.is_active(sid),
            }
        return result

    def get_stream_info(self, stream_id: int) -> Optional[Dict[str, Any]]:
        return self._active_streams.get(stream_id)

    def probe_stream(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(
                [settings.FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", url],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Probe failed for {url}: {e}")
        return None

    def stop_all(self):
        for stream_id in list(self._ffmpeg_processes.keys()):
            self.stop_stream(stream_id)

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for sid in self._ffmpeg_processes if self.is_active(sid))
        return {
            "total_tracked": len(self._active_streams),
            "active": active,
            "failed": len(self._active_streams) - active,
        }


streaming_engine = StreamingEngine()
