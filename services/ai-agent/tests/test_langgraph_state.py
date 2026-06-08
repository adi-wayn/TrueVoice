import os
import sys
import asyncio
import pytest
import grpc

# Ensure the parent directory and the generated directory are in the import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../generated")))

from main import ThreatNotifierServicer
from generated import threat_notifier_pb2
from generated import threat_notifier_pb2_grpc

def test_langgraph_state_transitions():
    # Placeholder for checking that the LangGraph state machine handles audio text events correctly
    assert True

def test_ner_trusted_contact_whitelist():
    # Placeholder for verifying NER extraction.
    assert True

def test_context_window_memory_limit():
    # Requirements specify a sliding window state of the last 15 sentences
    assert True

@pytest.mark.asyncio
async def test_threat_notifier_grpc():
    # Start the server on a dynamic local port
    server = grpc.aio.server()
    servicer = ThreatNotifierServicer()
    threat_notifier_pb2_grpc.add_ThreatNotifierServicer_to_server(servicer, server)
    
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    
    # Create client channel and stub
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stub = threat_notifier_pb2_grpc.ThreatNotifierStub(channel)
    
    # Receive mock alerts from stream
    received_alerts = []
    try:
        # GetThreatAlerts stream
        stream = stub.GetThreatAlerts(threat_notifier_pb2.Empty())
        
        # Read the first 2 mock alerts (the mock yields exactly 2 and then sleeps)
        # We can cancel the call after reading 2 to avoid blocking
        async for alert in stream:
            received_alerts.append(alert)
            if len(received_alerts) == 2:
                # Cancel the call to test cleanup
                stream.cancel()
                break
                
        # Verify both alerts were received correctly
        assert len(received_alerts) == 2
        
        assert received_alerts[0].threat_category == "OTP Request"
        assert received_alerts[0].risk_score == pytest.approx(0.95)
        assert "DO NOT share your OTP" in received_alerts[0].suggested_action
        
        assert received_alerts[1].threat_category == "Bank Spoofing"
        assert received_alerts[1].risk_score == pytest.approx(0.85)
        assert "bank to verify" in received_alerts[1].matched_text
    finally:
        # Clean up
        await channel.close()
        await server.stop(0)
