import grpc
import time
from concurrent import futures
import sys
import os

# Add parent directory to path to allow relative imports in generated package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import generated.audio_streamer_pb2 as audio_streamer_pb2
import generated.audio_streamer_pb2_grpc as audio_streamer_pb2_grpc

class AudioStreamerServicer(audio_streamer_pb2_grpc.AudioStreamerServicer):
    def StreamAudio(self, request_iterator, context):
        print("[Python STT Server] StreamAudio RPC initialized.")
        chunk_count = 0
        try:
            for chunk in request_iterator:
                chunk_count += 1
                pcm_data_len = len(chunk.raw_pcm_data)
                print(f"[Python STT Server] Received chunk #{chunk_count}: "
                      f"{pcm_data_len} bytes, sample_rate={chunk.sample_rate}, "
                      f"channels={chunk.channels}, PID={chunk.process_id}")
        except Exception as e:
            print(f"[Python STT Server] Error reading stream: {e}")
            
        status = audio_streamer_pb2.StreamStatus()
        status.active = True
        status.message = f"Successfully received {chunk_count} chunks."
        return status

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    audio_streamer_pb2_grpc.add_AudioStreamerServicer_to_server(AudioStreamerServicer(), server)
    server.add_insecure_port("127.0.0.1:50051")
    server.start()
    print("[Python STT Server] Running on 127.0.0.1:50051...")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    serve()
