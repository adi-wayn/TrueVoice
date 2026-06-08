fn main() {
    tonic_build::configure()
        .compile_protos(
            &[
                "../../protos/audio_streamer.proto",
                "../../protos/threat_notifier.proto",
                "../../protos/control_stream.proto",
            ],
            &["../../protos"],
        )
        .unwrap_or_else(|e| panic!("Failed to compile protos: {:?}", e));

    tauri_build::build()
}

