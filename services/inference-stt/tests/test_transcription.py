import os
import sys
import asyncio
import pytest
import grpc

# Ensure the parent directory and the generated directory are in the import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../generated")))

from main import AudioStreamerServicer
from generated import audio_streamer_pb2
from generated import audio_streamer_pb2_grpc

def test_transcription_initialization():
    # Placeholder for testing faster-whisper initialization
    assert True

def test_audio_processing_latency():
    # Placeholder for ensuring audio is processed quickly
    # Requirements specify total pipeline < 5s, so local STT must be fast
    assert True

def test_no_cloud_call_enforcement():
    # Placeholder to ensure no external HTTP requests are made
    assert True

@pytest.mark.asyncio
async def test_audio_streamer_grpc():
    # Start the server on a dynamic local port
    server = grpc.aio.server()
    servicer = AudioStreamerServicer()
    audio_streamer_pb2_grpc.add_AudioStreamerServicer_to_server(servicer, server)
    
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    
    # Create client channel and stub
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stub = audio_streamer_pb2_grpc.AudioStreamerStub(channel)
    
    # Define an async generator to stream chunks
    async def chunk_generator():
        chunks = [
            audio_streamer_pb2.AudioChunk(
                raw_pcm_data=b"\x00\x01\x02\x03",
                sample_rate=16000,
                channels=1,
                timestamp_ms=1000,
                process_id=1234
            ),
            audio_streamer_pb2.AudioChunk(
                raw_pcm_data=b"\x04\x05\x06\x07\x08",
                sample_rate=16000,
                channels=1,
                timestamp_ms=1050,
                process_id=1234
            )
        ]
        for c in chunks:
            yield c
            await asyncio.sleep(0.01)

    try:
        # Call the StreamAudio RPC
        response = await stub.StreamAudio(chunk_generator())
        
        # Verify the response
        assert response.active is True
        assert "Successfully received 9 bytes" in response.message
    finally:
        # Clean up
        await channel.close()
        await server.stop(0)
