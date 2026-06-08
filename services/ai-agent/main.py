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
from generated import threat_notifier_pb2
from generated import threat_notifier_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ai-agent")

# Load environment variables from repo root
repo_root = os.path.abspath(os.path.join(current_dir, "../.."))
env_path = os.path.join(repo_root, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f"No .env file found at {env_path}, using defaults")

class ThreatNotifierServicer(threat_notifier_pb2_grpc.ThreatNotifierServicer):
    async def GetThreatAlerts(self, request, context):
        logger.info("GetThreatAlerts RPC connection established.")
        
        # Define mock alerts to send upon connection
        mock_alerts = [
            threat_notifier_pb2.ThreatAlert(
                matched_text="Can you confirm your OTP?",
                risk_score=0.95,
                threat_category="OTP Request",
                suggested_action="DO NOT share your OTP. Hang up immediately."
            ),
            threat_notifier_pb2.ThreatAlert(
                matched_text="I am calling from your bank to verify a suspicious transaction.",
                risk_score=0.85,
                threat_category="Bank Spoofing",
                suggested_action="Do not provide personal details. Verify calling identity independently."
            )
        ]

        # Yield mock alerts
        try:
            for alert in mock_alerts:
                logger.info(f"Yielding mock alert: {alert.threat_category} (Score: {alert.risk_score})")
                yield alert
                await asyncio.sleep(0.5)

            # Keep stream open to simulate real-time notification
            logger.info("Yielded initial mock alerts. Keeping stream open for live alerts...")
            while True:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.info("GetThreatAlerts RPC cancelled by client/server shutdown.")
            raise
        except Exception as e:
            logger.error(f"Error in GetThreatAlerts stream: {e}")
        finally:
            logger.info("GetThreatAlerts RPC stream closed.")

async def serve():
    # Read port, default to 50052 as per updated plan
    port = os.environ.get("AI_AGENT_GRPC_PORT", "50052")
    host = os.environ.get("AI_AGENT_GRPC_HOST", "127.0.0.1")
    address = f"{host}:{port}"

    server = grpc.aio.server()
    threat_notifier_pb2_grpc.add_ThreatNotifierServicer_to_server(
        ThreatNotifierServicer(), server
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
