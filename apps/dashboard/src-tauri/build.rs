fn main() {
    let proto_dir = std::path::Path::new("../../../protos")
        .canonicalize()
        .expect("Failed to canonicalize proto directory path");

    let protos = [
        proto_dir.join("audio_streamer.proto"),
        proto_dir.join("threat_notifier.proto"),
        proto_dir.join("control_stream.proto"),
    ];

    tonic_build::configure()
        .compile_protos(
            &protos,
            &[proto_dir],
        )
        .unwrap_or_else(|e| panic!("Failed to compile protos: {:?}", e));

    tauri_build::build()
}

