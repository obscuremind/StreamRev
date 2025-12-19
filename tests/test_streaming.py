"""
Streaming tests for StreamRev
"""

import pytest
from src.streaming.transcoder import FFmpegTranscoder
from src.streaming.load_balancer import LoadBalancer


class TestFFmpegTranscoder:
    """Test FFmpeg transcoder"""
    
    def test_transcoder_init(self):
        """Test transcoder initialization"""
        transcoder = FFmpegTranscoder()
        assert transcoder.ffmpeg_path is not None
    
    def test_build_transcode_command(self):
        """Test building transcode command"""
        transcoder = FFmpegTranscoder()
        cmd = transcoder._build_transcode_command(
            'http://input.com/stream.m3u8',
            'http://output.com/stream.m3u8',
            'medium'
        )
        
        assert 'ffmpeg' in cmd[0] or 'ffmpeg' in str(cmd)
        assert 'http://input.com/stream.m3u8' in cmd
        assert 'http://output.com/stream.m3u8' in cmd


class TestLoadBalancer:
    """Test load balancer"""
    
    def test_load_balancer_init(self):
        """Test load balancer initialization"""
        # This would need a mock database
        pass
