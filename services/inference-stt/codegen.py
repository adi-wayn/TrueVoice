import os
import subprocess
import sys

def main():
    print("Running Python gRPC Codegen...")
    # Paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proto_dir = os.path.abspath(os.path.join(script_dir, "../../protos"))
    out_dir = os.path.abspath(os.path.join(script_dir, "generated"))

    os.makedirs(out_dir, exist_ok=True)

    # Compile all proto files
    proto_files = [
        os.path.join(proto_dir, "audio_streamer.proto"),
        os.path.join(proto_dir, "threat_notifier.proto"),
        os.path.join(proto_dir, "control_stream.proto"),
        os.path.join(proto_dir, "transcript_stream.proto"),
    ]

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{proto_dir}",
        f"--python_out={out_dir}",
        f"--grpc_python_out={out_dir}",
    ] + proto_files

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Codegen Failed!")
        print(result.stderr)
        sys.exit(1)
    else:
        print("Codegen Succeeded!")
        # Create __init__.py in generated to make it a module
        with open(os.path.join(out_dir, "__init__.py"), "w") as f:
            f.write("# Generated gRPC stubs\n")
        
        # Fixing the relative import issue in grpc_tools generated files for python3
        # E.g. import audio_streamer_pb2 as audio__streamer__pb2 -> from . import audio_streamer_pb2 as audio__streamer__pb2
        for filename in os.listdir(out_dir):
            if filename.endswith("_pb2_grpc.py"):
                filepath = os.path.join(out_dir, filename)
                with open(filepath, "r") as f:
                    content = f.read()
                
                # Replace imports of pb2 with local imports
                content = content.replace("import audio_streamer_pb2", "from . import audio_streamer_pb2")
                content = content.replace("import threat_notifier_pb2", "from . import threat_notifier_pb2")
                content = content.replace("import control_stream_pb2", "from . import control_stream_pb2")
                content = content.replace("import transcript_stream_pb2", "from . import transcript_stream_pb2")
                
                with open(filepath, "w") as f:
                    f.write(content)
                print(f"Patched imports in {filename}")

if __name__ == "__main__":
    main()
