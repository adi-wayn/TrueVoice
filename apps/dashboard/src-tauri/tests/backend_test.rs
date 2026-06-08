#[cfg(test)]
mod tests {
    use appsdashboard_lib::{UiThreatAlert, AppState};
    use std::sync::Arc;
    use tokio::sync::Mutex;

    #[test]
    fn test_ui_threat_alert_serialization() {
        let alert = UiThreatAlert {
            matched_text: "Test match text".to_string(),
            risk_score: 0.95,
            threat_category: "OTP Theft".to_string(),
            suggested_action: "Hang up".to_string(),
        };

        let json = serde_json::to_string(&alert).expect("Failed to serialize UiThreatAlert");
        assert!(json.contains("matched_text"));
        assert!(json.contains("Test match text"));
        assert!(json.contains("risk_score"));
        assert!(json.contains("0.95"));
        assert!(json.contains("threat_category"));
        assert!(json.contains("OTP Theft"));
        assert!(json.contains("suggested_action"));
        assert!(json.contains("Hang up"));
    }

    #[tokio::test]
    async fn test_app_state_initialization() {
        let status = Arc::new(Mutex::new("disconnected".to_string()));
        let state = AppState {
            connection_status: status.clone(),
        };

        {
            let val = state.connection_status.lock().await;
            assert_eq!(*val, "disconnected");
        }

        {
            let mut val = status.lock().await;
            *val = "connected".to_string();
        }

        let val = state.connection_status.lock().await;
        assert_eq!(*val, "connected");
    }
}
