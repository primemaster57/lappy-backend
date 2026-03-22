from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import json
import uuid
import time

app = FastAPI()

# Enable CORS (so Base44 frontend can connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Models
# ---------------------------

class Device(BaseModel):
    brand: str
    model: str
    board_pn: str

class Symptom(BaseModel):
    title: str
    description: str
    onset: str
    power_state: str
    os_behavior: List[str] = Field(default_factory=list)

class DiagnoseRequest(BaseModel):
    device: Device
    symptom: Symptom
    user_actions_tried: List[str] = Field(default_factory=list)

class ProbableComponent(BaseModel):
    ref: str
    type: str
    section: Optional[str] = None

class Hypothesis(BaseModel):
    title: str
    confidence: float
    board_section: str
    probable_components: List[ProbableComponent] = Field(default_factory=list)
    root_cause_pattern: Optional[str] = None

class RecommendedTest(BaseModel):
    step: int
    tool: str
    expected_result: str

class Explainability(BaseModel):
    en: str
    hi: str

class DiagnoseResponse(BaseModel):
    hypotheses: List[Hypothesis]
    recommended_tests: List[RecommendedTest]
    explainability: Explainability


# ---------------------------
# Health Check
# ---------------------------

@app.get("/health")
async def health():
    return {"ok": True, "time": time.time()}


# ---------------------------
# Diagnose API
# ---------------------------

@app.post("/api/diagnose", response_model=DiagnoseResponse)
async def diagnose(req: DiagnoseRequest):

    # Example hypothesis (dummy for now)
    hypothesis = Hypothesis(
        title="CPU VRM instability under load",
        confidence=92.0,
        board_section="CPU_VRM",
        probable_components=[
            ProbableComponent(ref="PQ305", type="MOSFET", section="CPU_VRM"),
            ProbableComponent(ref="PL306", type="Inductor", section="CPU_VRM"),
        ],
        root_cause_pattern="Stable in BIOS but unstable under OS load"
    )

    tests = [
        RecommendedTest(
            step=1,
            tool="Multimeter",
            expected_result="Check VCORE at PL306 (~1V stable)"
        ),
        RecommendedTest(
            step=2,
            tool="Thermal camera",
            expected_result="Check overheating MOSFET"
        ),
        RecommendedTest(
            step=3,
            tool="Visual inspection",
            expected_result="Check burned or damaged components"
        ),
    ]

    explanation = Explainability(
        en="System is stable in BIOS but fails under load, indicating VRM or power instability.",
        hi="BIOS में सिस्टम ठीक है लेकिन लोड में फेल हो रहा है, जो VRM समस्या दर्शाता है।"
    )

    return DiagnoseResponse(
        hypotheses=[hypothesis],
        recommended_tests=tests,
        explainability=explanation
    )


# ---------------------------
# Provider API
# ---------------------------

@app.get("/api/llm/providers")
async def get_providers():
    return {
        "providers": [
            {
                "id": "openai",
                "display_name": "OpenAI GPT",
                "platform": "openai",
                "active": True,
                "meta": {
                    "weight": 1.0,
                    "last_test": {
                        "latency_s": 0.8,
                        "ok": True
                    }
                }
            },
            {
                "id": "mock",
                "display_name": "Mock Model",
                "platform": "local",
                "active": False,
                "meta": {
                    "weight": 0.2,
                    "last_test": {
                        "latency_s": 1.5,
                        "ok": False
                    }
                }
            }
        ]
    }


# ---------------------------
# WebSocket Trace
# ---------------------------

@app.websocket("/ws/trace")
async def websocket_trace(ws: WebSocket):
    await ws.accept()

    try:
        # First message should be init
        init_data = await ws.receive_json()
        session_id = init_data.get("session_id", str(uuid.uuid4()))

        await ws.send_json({
            "type": "init_ack",
            "session_id": session_id
        })

        while True:
            msg = await ws.receive_json()

            if msg.get("type") == "start_llm_stream":

                # Simulated streaming response
                await ws.send_json({
                    "type": "llm_stream",
                    "event": {"type": "chunk", "text": "Analyzing system...\n"}
                })

                await ws.send_json({
                    "type": "llm_stream",
                    "event": {"type": "chunk", "text": "Checking VRM stability...\n"}
                })

                await ws.send_json({
                    "type": "llm_stream",
                    "event": {
                        "type": "done",
                        "parsed": {
                            "hypotheses": [
                                {
                                    "title": "CPU VRM failure",
                                    "confidence": 92
                                }
                            ]
                        }
                    }
                })

    except WebSocketDisconnect:
        print("Client disconnected")