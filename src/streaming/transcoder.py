"""
FFmpeg transcoding wrapper
"""

import subprocess
import logging
import json
from typing import Optional, Dict, Any, List
import os

logger = logging.getLogger(__name__)


class FFmpegTranscoder:
    """FFmpeg transcoding handler"""
    
    def __init__(self, ffmpeg_path: str = '/usr/bin/ffmpeg'):
        """
        Initialize FFmpeg transcoder
        
        Args:
            ffmpeg_path: Path to FFmpeg binary
        """
        self.ffmpeg_path = ffmpeg_path
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self):
        """Verify FFmpeg installation"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"FFmpeg verified: {self.ffmpeg_path}")
            else:
                logger.error("FFmpeg not found or not working")
        except Exception as e:
            logger.error(f"FFmpeg verification failed: {str(e)}")
    
    def transcode_stream(self, input_url: str, output_url: str, 
                        profile: Optional[str] = None) -> bool:
        """
        Transcode stream using FFmpeg
        
        Args:
            input_url: Input stream URL
            output_url: Output stream URL
            profile: Transcoding profile name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Build FFmpeg command
            cmd = self._build_transcode_command(input_url, output_url, profile)
            
            logger.info(f"Starting transcode: {input_url} -> {output_url}")
            
            # Start FFmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # TODO: Monitor process and handle errors
            return True
            
        except Exception as e:
            logger.error(f"Transcoding failed: {str(e)}")
            return False
    
    def _build_transcode_command(self, input_url: str, output_url: str,
                                 profile: Optional[str] = None) -> List[str]:
        """
        Build FFmpeg command
        
        Args:
            input_url: Input stream URL
            output_url: Output stream URL  
            profile: Transcoding profile name
            
        Returns:
            List of command arguments
        """
        cmd = [
            self.ffmpeg_path,
            '-re',  # Read input at native frame rate
            '-i', input_url,
            '-c:v', 'libx264',  # Video codec
            '-preset', 'veryfast',  # Encoding preset
            '-b:v', '2000k',  # Video bitrate
            '-c:a', 'aac',  # Audio codec
            '-b:a', '128k',  # Audio bitrate
            '-f', 'mpegts',  # Output format
            output_url
        ]
        
        # Apply profile-specific settings
        if profile == 'low':
            cmd[cmd.index('-b:v') + 1] = '800k'
        elif profile == 'high':
            cmd[cmd.index('-b:v') + 1] = '4000k'
            cmd[cmd.index('-preset') + 1] = 'medium'
        
        return cmd
    
    def get_stream_info(self, stream_url: str) -> Optional[Dict[str, Any]]:
        """
        Get stream information using FFprobe
        
        Args:
            stream_url: Stream URL
            
        Returns:
            Dictionary with stream information or None
        """
        try:
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
            
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                stream_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get stream info: {str(e)}")
            return None
    
    def generate_thumbnail(self, video_url: str, output_path: str, 
                          timestamp: str = '00:00:01') -> bool:
        """
        Generate thumbnail from video
        
        Args:
            video_url: Video URL
            output_path: Output image path
            timestamp: Timestamp to capture (format: HH:MM:SS)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cmd = [
                self.ffmpeg_path,
                '-ss', timestamp,
                '-i', video_url,
                '-vframes', '1',
                '-q:v', '2',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {str(e)}")
            return False
