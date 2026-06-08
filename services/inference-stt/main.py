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

class AudioStreamerServicer(audio_streamer_pb2_grpc.AudioStreamerServicer):
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
    # Read port, default to 50051 as per updated plan
    port = os.environ.get("INFERENCE_STT_GRPC_PORT", "50051")
    host = os.environ.get("INFERENCE_STT_GRPC_HOST", "127.0.0.1")
    address = f"{host}:{port}"

    server = grpc.aio.server()
    audio_streamer_pb2_grpc.add_AudioStreamerServicer_to_server(
        AudioStreamerServicer(), server
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

def main():
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server terminated by user.")

if __name__ == "__main__":
    main()
