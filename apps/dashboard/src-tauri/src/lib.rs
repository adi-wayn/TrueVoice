use tauri::Emitter;
use std::sync::Arc;
use tokio::sync::Mutex;

pub mod truevoice {
    pub mod agent {
        tonic::include_proto!("truevoice.agent");
    }
    pub mod control {
        tonic::include_proto!("truevoice.control");
    }
    pub mod audio {
        tonic::include_proto!("truevoice.audio");
    }
}

#[derive(Clone, serde::Serialize)]
pub struct UiThreatAlert {
    pub matched_text: String,
    pub risk_score: f32,
    pub threat_category: String,
    pub suggested_action: String,
}

pub struct AppState {
    pub connection_status: Arc<Mutex<String>>,
}

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
async fn get_connection_status(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let status = state.connection_status.lock().await;
    Ok(status.clone())
}

#[derive(Clone, serde::Serialize)]
pub struct ServicesStatus {
    pub capture_service: bool,
    pub stt_service: bool,
    pub agent_service: bool,
}

#[tauri::command]
async fn get_services_status() -> Result<ServicesStatus, String> {
    use std::net::TcpStream;
    use std::time::Duration;

    let timeout = Duration::from_millis(200);

    let capture_service = TcpStream::connect_timeout(
        &"127.0.0.1:50051".parse().unwrap(),
        timeout,
    ).is_ok();

    let stt_service = TcpStream::connect_timeout(
        &"127.0.0.1:50052".parse().unwrap(),
        timeout,
    ).is_ok();

    let agent_service = TcpStream::connect_timeout(
        &"127.0.0.1:50053".parse().unwrap(),
        timeout,
    ).is_ok();

    Ok(ServicesStatus {
        capture_service,
        stt_service,
        agent_service,
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let connection_status = Arc::new(Mutex::new("disconnected".to_string()));
    let status_for_setup = connection_status.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            connection_status,
        })
        .invoke_handler(tauri::generate_handler![greet, get_connection_status, get_services_status])
        .setup(move |app| {
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                loop {
                    // Update status to reconnecting
                    {
                        let mut status = status_for_setup.lock().await;
                        *status = "reconnecting".to_string();
                    }
                    let _ = app_handle.emit("grpc-status", "reconnecting");

                    match truevoice::agent::threat_notifier_client::ThreatNotifierClient::connect("http://127.0.0.1:50053").await {
                        Ok(mut client) => {
                            {
                                let mut status = status_for_setup.lock().await;
                                *status = "connected".to_string();
                            }
                            let _ = app_handle.emit("grpc-status", "connected");

                            match client.get_threat_alerts(truevoice::agent::Empty {}).await {
                                Ok(response) => {
                                    let mut stream = response.into_inner();
                                    while let Ok(Some(alert)) = stream.message().await {
                                        let ui_alert = UiThreatAlert {
                                            matched_text: alert.matched_text,
                                            risk_score: alert.risk_score,
                                            threat_category: alert.threat_category,
                                            suggested_action: alert.suggested_action,
                                        };
                                        let _ = app_handle.emit("threat-alert", ui_alert);
                                    }
                                }
                                Err(e) => {
                                    eprintln!("gRPC stream error: {:?}", e);
                                }
                            }
                        }
                        Err(e) => {
                            eprintln!("Failed to connect to gRPC: {:?}", e);
                        }
                    }

                    {
                        let mut status = status_for_setup.lock().await;
                        *status = "disconnected".to_string();
                    }
                    let _ = app_handle.emit("grpc-status", "disconnected");

                    tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
