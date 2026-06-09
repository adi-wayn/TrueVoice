import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Ensure the directory of this script is in pythonpath so we can import 'generated'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import grpc
from generated import audio_streamer_pb2
from generated import audio_streamer_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("inference-stt")

# Load environment variables from repo root
repo_root = os.path.abspath(os.path.join(current_dir, "../.."))
env_path = os.path.join(repo_root, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f"No .env file found at {env_path}, using defaults")

import numpy as np
from faster_whisper import WhisperModel
from generated import transcript_stream_pb2
from generated import transcript_stream_pb2_grpc

class AudioStreamerServicer(audio_streamer_pb2_grpc.AudioStreamerServicer):
    def __init__(self):
        # Initialize Whisper Model
        model_path = os.environ.get("WHISPER_MODEL_PATH", "tiny")
        if not os.path.exists(model_path):
            logger.info(f"Model path '{model_path}' not found on disk. Falling back to downloading 'tiny' model.")
            model_path = "tiny"
        logger.info(f"Loading Whisper model from '{model_path}'...")
        self.model = WhisperModel(model_path, device="cpu", compute_type="int8")
        logger.info("Whisper model loaded successfully.")

        # Initialize gRPC Client connection to ai-agent
        agent_host = os.environ.get("AI_AGENT_GRPC_HOST", "127.0.0.1")
        agent_port = os.environ.get("AI_AGENT_GRPC_PORT", "50053")
        self.agent_address = f"{agent_host}:{agent_port}"
        logger.info(f"Connecting to ai-agent at {self.agent_address}...")
        self.agent_channel = grpc.aio.insecure_channel(self.agent_address)
        self.agent_stub = transcript_stream_pb2_grpc.TranscriptStreamStub(self.agent_channel)

    async def StreamAudio(self, request_iterator, context):
        total_bytes = 0
        logger.info("StreamAudio RPC connection established.")
        try:
            async for chunk in request_iterator:
                chunk_len = len(chunk.raw_pcm_data)
                total_bytes += chunk_len
                logger.info(
                    f"Received AudioChunk: {chunk_len} bytes, "
                    f"sample_rate={chunk.sample_rate}, "
                    f"channels={chunk.channels}, "
                    f"timestamp_ms={chunk.timestamp_ms}, "
                    f"process_id={chunk.process_id}"
                )

                raw_data = chunk.raw_pcm_data
                if len(raw_data) % 2 != 0:
                    raw_data = raw_data[:-1]

                if len(raw_data) == 0:
                    continue

                # 1. Convert PCM to numpy array normalized to [-1.0, 1.0]
                pcm_data = np.frombuffer(raw_data, dtype=np.int16)
                audio_np = pcm_data.astype(np.float32) / 32768.0

                # Resample to 16000Hz (Whisper's expected rate)
                if chunk.sample_rate != 16000:
                    logger.info(f"Resampling audio from {chunk.sample_rate}Hz to 16000Hz...")
                    if chunk.sample_rate == 48000:
                        audio_np = audio_np[::3]
                    elif chunk.sample_rate == 32000:
                        audio_np = audio_np[::2]
                    else:
                        # Simple linear interpolation resampling in numpy
                        xp = np.arange(len(audio_np))
                        x_new = np.linspace(0, len(audio_np) - 1, int(len(audio_np) * 16000 / chunk.sample_rate))
                        audio_np = np.interp(x_new, xp, audio_np).astype(np.float32)

                # 2. Transcribe using faster-whisper
                logger.info("Running local STT transcription...")
                segments, info = self.model.transcribe(audio_np, beam_size=5)
                transcript_text = "".join(segment.text for segment in segments).strip()

                # 3. Forward transcript to ai-agent if speech is transcribed
                if transcript_text:
                    logger.info(f"Transcribed Text: '{transcript_text}' (language: {info.language})")
                    fragment = transcript_stream_pb2.TranscriptFragment(
                        text=transcript_text,
                        process_id=chunk.process_id,
                        timestamp_ms=chunk.timestamp_ms
                    )
                    try:
                        await self.agent_stub.SendTranscript(fragment)
                        logger.info("Transcript successfully forwarded to ai-agent.")
                    except Exception as e:
                        logger.error(f"Failed to forward transcript to ai-agent: {e}")
                else:
                    logger.info("STT completed: No speech transcribed in this chunk.")

        except Exception as e:
            logger.error(f"Error during StreamAudio RPC execution: {e}")
            return audio_streamer_pb2.StreamStatus(
                active=False,
                message=f"Error in stream: {e}"
            )
        
        logger.info(f"StreamAudio RPC finished. Total bytes received: {total_bytes}")
        return audio_streamer_pb2.StreamStatus(
            active=True,
            message=f"Successfully received {total_bytes} bytes"
        )

async def serve():
    # Read port, default to 50052 as per updated plan
    port = os.environ.get("INFERENCE_STT_GRPC_PORT", "50052")
    host = os.environ.get("INFERENCE_STT_GRPC_HOST", "127.0.0.1")
    address = f"{host}:{port}"

    server = grpc.aio.server()
    audio_streamer_servicer = AudioStreamerServicer()
    audio_streamer_pb2_grpc.add_AudioStreamerServicer_to_server(
        audio_streamer_servicer, server
    )
    server.add_insecure_port(address)
    logger.info(f"Starting async gRPC server on {address}...")
    await server.start()
    logger.info("Server started successfully.")
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        logger.info("Shutting down server...")
        await server.stop(0)
    finally:
        await audio_streamer_servicer.agent_channel.close()

def main():
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server terminated by user.")

if __name__ == "__main__":
    main()
