import os
import sys
import asyncio
import logging
import httpx
from dotenv import load_dotenv

# Ensure the directory of this script is in pythonpath so we can import 'generated'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import grpc
from generated import threat_notifier_pb2
from generated import threat_notifier_pb2_grpc
from generated import transcript_stream_pb2
from generated import transcript_stream_pb2_grpc

from agent import get_agent_graph

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

async def trigger_webhook(text: str, risk_score: float, category: str, action: str):
    webhook_url = os.environ.get("MAKE_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("MAKE_WEBHOOK_URL is not set. Skipping Make.com webhook trigger.")
        return
        
    payload = {
        "text": text,
        "risk_score": risk_score,
        "threat_category": category,
        "suggested_action": action
    }
    
    logger.info(f"Sending webhook notification to Make.com (URL: {webhook_url})...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code in [200, 201, 202]:
                logger.info("Make.com webhook triggered successfully.")
            else:
                logger.error(f"Make.com webhook failed with status code {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error triggering Make.com webhook: {e}")

class ThreatNotifierServicer(threat_notifier_pb2_grpc.ThreatNotifierServicer):
    def __init__(self):
        self.subscribers = set()

    async def GetThreatAlerts(self, request, context):
        queue = asyncio.Queue()
        self.subscribers.add(queue)
        logger.info(f"New subscriber registered for threat alerts. Total subscribers: {len(self.subscribers)}")
        try:
            while True:
                alert = await queue.get()
                yield alert
        except asyncio.CancelledError:
            logger.info("Subscriber disconnected.")
            raise
        finally:
            self.subscribers.remove(queue)

    async def broadcast_alert(self, alert):
        for queue in list(self.subscribers):
            await queue.put(alert)

class TranscriptStreamServicer(transcript_stream_pb2_grpc.TranscriptStreamServicer):
    def __init__(self, threat_notifier):
        self.threat_notifier = threat_notifier
        self.agent_graph = get_agent_graph()
        self.states = {}  # pid -> AgentState dictionary

    async def SendTranscript(self, request, context):
        pid = request.process_id
        text = request.text
        
        # Get or initialize state for this pid
        if pid not in self.states:
            self.states[pid] = {
                "transcript": [],
                "new_sentence": "",
                "risk_score": 0.0,
                "threat_category": "Safe",
                "suggested_action": "No action required.",
                "whitelist_detected": False,
                "process_id": pid
            }
            
        current_state = self.states[pid]
        current_state["new_sentence"] = text
        
        logger.info(f"Running LangGraph agent on new transcript: '{text}' (PID: {pid})")
        # Run state machine
        new_state = await self.agent_graph.ainvoke(current_state)
        
        # Update our cached state
        self.states[pid] = new_state
        
        # If whitelist was detected, purge memory cache for this PID
        if new_state.get("whitelist_detected", False):
            logger.info(f"Whitelist detected. Purging state cache for PID {pid}.")
            self.states.pop(pid, None)
            
        # Broadcast the alert to keep the UI informed in real-time (helps show active listening)
        risk_score = new_state.get("risk_score", 0.0)
        alert = threat_notifier_pb2.ThreatAlert(
            matched_text=text,
            risk_score=risk_score,
            threat_category=new_state.get("threat_category", "Safe"),
            suggested_action=new_state.get("suggested_action", "")
        )
        logger.info(f"Broadcasting transcript alert: {alert.threat_category} (Score: {alert.risk_score})")
        await self.threat_notifier.broadcast_alert(alert)
        
        if risk_score > 0.8:
            # Fire-and-forget Webhook triggering for high risk
            asyncio.create_task(
                trigger_webhook(
                    text=text,
                    risk_score=risk_score,
                    category=alert.threat_category,
                    action=alert.suggested_action
                )
            )
            
        return transcript_stream_pb2.Empty()

async def serve():
    # Read port, default to 50052 as per updated plan
    port = os.environ.get("AI_AGENT_GRPC_PORT", "50052")
    host = os.environ.get("AI_AGENT_GRPC_HOST", "127.0.0.1")
    address = f"{host}:{port}"

    server = grpc.aio.server()
    
    # Register both servicers
    threat_notifier = ThreatNotifierServicer()
    threat_notifier_pb2_grpc.add_ThreatNotifierServicer_to_server(threat_notifier, server)
    
    transcript_servicer = TranscriptStreamServicer(threat_notifier)
    transcript_stream_pb2_grpc.add_TranscriptStreamServicer_to_server(transcript_servicer, server)
    
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
