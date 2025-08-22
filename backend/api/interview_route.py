# app/api/interview.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from datetime import datetime
from bson import ObjectId
import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI

from db.database import job_profiles, interview_scores, interview_sessions

from utils.getuser import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = SystemMessage(
    content=(
        "You are an experienced technical interviewer conducting a structured, professional interview. "
        "Your goal is to assess the candidate's technical skills, cultural fit, and potential for growth. "
        "Maintain a conversational, supportive tone while gathering meaningful insights."
    )
)

class InterviewSession:
    def __init__(self, job_description: str, resume_text: str, max_questions: int = 8):
        self.job_description = job_description
        self.resume_text = resume_text
        self.max_questions = max_questions
        self.conversation_history: list[dict] = []
        self.question_count = 0
        
        # More detailed stage definitions with specific purposes
        self.interview_stages = [
            {
                "name": "introduction",
                "purpose": "Build rapport and understand motivation",
                "question_style": "Open-ended, welcoming questions about background and interest"
            },
            {
                "name": "experience_deep_dive", 
                "purpose": "Explore relevant past experience with specific examples",
                "question_style": "STAR method questions focusing on specific situations and outcomes"
            },
            {
                "name": "technical_assessment",
                "purpose": "Evaluate technical competency and problem-solving approach", 
                "question_style": "Scenario-based questions requiring detailed technical explanations"
            },
            {
                "name": "role_specific_fit",
                "purpose": "Assess fit for specific job requirements and challenges",
                "question_style": "Job-specific scenarios and hypothetical situations"
            },
            {
                "name": "behavioral_insights",
                "purpose": "Understand work style, collaboration, and growth mindset",
                "question_style": "Behavioral questions using past examples to predict future performance"
            },
            {
                "name": "closing_exploration",
                "purpose": "Address questions and assess genuine interest",
                "question_style": "Open dialogue about expectations and mutual fit"
            }
        ]
        
        self.current_stage = 0
        # swapped in OpenAI's GPT-3.5-turbo with deterministic output
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

    def build_enhanced_prompt(self) -> list[HumanMessage | SystemMessage]:
        current_stage_info = self.interview_stages[self.current_stage]  
        stage_name = current_stage_info["name"]
        stage_purpose = current_stage_info["purpose"]
        question_style = current_stage_info["question_style"]
        
        progress = f"{self.question_count}/{self.max_questions}"
        
        recent_context = ""
        if self.conversation_history:
            last_qa = self.conversation_history[-1]
            recent_context = f"\nLast Q&A for context:\nQ: {last_qa['question']}\nA: {last_qa['answer'][:200]}..."
        
        context_msg = SystemMessage(content=f"""
INTERVIEW CONTEXT:
Progress: {progress} questions completed
Current Stage: {stage_name} ({stage_purpose})
Question Style: {question_style}

JOB REQUIREMENTS:
{self.job_description}

CANDIDATE BACKGROUND:
{self.resume_text}

GUIDELINES:
- Ask ONE focused question that builds on previous answers
- Reference specific details from their resume or previous responses
- Use follow-up questions to dig deeper into interesting points
- Maintain professional but conversational tone
- For technical questions, ask for specific examples and explanations
- For behavioral questions, use "Tell me about a time when..." format
- Keep questions concise (2-3 sentences max)
- Avoid yes/no questions - seek detailed responses

{recent_context}
""")
        
        msgs: list[HumanMessage | SystemMessage] = [SYSTEM_MESSAGE, context_msg]
        
        for i, turn in enumerate(self.conversation_history):
            msgs.append(HumanMessage(content=f"Previous Question {i+1}: {turn['question']}"))
            msgs.append(HumanMessage(content=f"Candidate Response {i+1}: {turn['answer']}"))
        
        instruction = f"""
Based on the {stage_name} stage focus and the conversation so far, ask your next question.
If this is a follow-up, reference something specific from their last answer.
Question {self.question_count + 1} of {self.max_questions}:
"""
        msgs.append(HumanMessage(content=instruction))
        return msgs

    def create_personalized_opening(self) -> str:
        return (
            "Hello! I'm excited to speak with you today about this opportunity. "
            "I've reviewed your background and I'm particularly interested in your experience. "
            "Could you start by telling me what drew you to apply for this role and "
            "what aspects of your background make you most excited about this opportunity?"
        )
    
    def refine_question(self, question: str, candidate_input: str) -> str:
        prefixes_to_remove = [
            "Great question!", "That's interesting.", "Thank you for sharing.",
            "I see.", "Excellent.", "Perfect."
        ]
        for prefix in prefixes_to_remove:
            if question.startswith(prefix):
                question = question[len(prefix):].strip()
        if not question.endswith(('?', '.', '!')):
            question += '?'
        return question
    
    def get_fallback_question(self) -> str:
        stage_name = self.interview_stages[self.current_stage]["name"]
        fallbacks = {
            "introduction": "What interests you most about this role and our company?",
            "experience_deep_dive": "Can you walk me through a challenging project you've worked on recently?",
            "technical_assessment": "How would you approach solving a complex technical problem in this domain?",
            "role_specific_fit": "What do you see as the biggest challenges in this role, and how would you address them?",
            "behavioral_insights": "Tell me about a time when you had to collaborate with a difficult team member.",
            "closing_exploration": "What questions do you have about the role or our team?"
        }
        return fallbacks.get(stage_name, "Could you tell me more about your relevant experience?")
    
    def advance_stage(self):
        questions_per_stage = max(1, self.max_questions // len(self.interview_stages))
        expected_stage = min(
            (self.question_count - 1) // questions_per_stage,
            len(self.interview_stages) - 1
        )
        self.current_stage = expected_stage

    async def get_response(self, candidate_input: str = None) -> str:
        if self.question_count == 0:
            opening = self.create_personalized_opening()
            self.question_count += 1
            return opening
        
        try:
            messages = self.build_enhanced_prompt()
            resp = await self.llm.agenerate([messages])
            llm_message = resp.generations[0][0].message
            question = self.refine_question(llm_message.content.strip(), candidate_input)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            question = self.get_fallback_question()
        
        self.question_count += 1
        self.advance_stage()
        return question

    async def score_answer(self, question: str, answer: str) -> int | None:
        current_stage_info = self.interview_stages[self.current_stage]
        scoring_prompt = f"""
You are evaluating a candidate's interview response. Consider the following:

QUESTION: {question}
ANSWER: {answer}

EVALUATION CRITERIA:
- Stage: {current_stage_info['name']} ({current_stage_info['purpose']})
- Relevance: How well does the answer address the question?
- Depth: Does the answer provide sufficient detail and examples?
- Clarity: Is the response well-structured and easy to follow?
- Technical accuracy: (For technical questions) Are the concepts correct?
- Behavioral indicators: (For behavioral questions) Does it show good judgment/skills?

Score from 1-10 where:
1-3: Poor (vague, irrelevant, or incorrect)
4-6: Average (basic response, some relevance)
7-8: Good (solid response with good detail)
9-10: Excellent (comprehensive, insightful, well-articulated)

Respond with only the number.
"""
        try:
            prompts = [SystemMessage(content=scoring_prompt)]
            res = await self.llm.agenerate([prompts])
            content = res.generations[0][0].message.content.strip()
            score = int(content)
            return max(1, min(10, score))
        except Exception as e:
            logger.warning(f"Scoring failed: {e}")
            return None

    def add_to_history(self, question: str, answer: str, score: int | None):
        self.conversation_history.append({
            "question": question,
            "answer": answer,
            "score": score,
            "stage": self.interview_stages[self.current_stage]["name"],
            "question_number": self.question_count
        })

async def finalize_interview(session: InterviewSession,
                             session_id,
                             websocket: WebSocket):
    """Compute final score & summary, persist, send wrap-up, and close WS."""
    doc = interview_sessions.find_one({"_id": session_id})
    scores = [h["score"] for h in doc.get("history", []) if h.get("score") is not None]
    avg = sum(scores) / len(scores) if scores else None

    # 1) Build summary
    if avg is not None:
        # Stage-by-stage breakdown
        stage_breakdown: dict[str, list[int]] = {}
        for item in doc.get("history", []):
            stg = item.get("stage", "unknown")
            if item.get("score") is not None:
                stage_breakdown.setdefault(stg, []).append(item["score"])
        # Summarize averages
        stage_summary = ""
        for stg, stg_scores in stage_breakdown.items():
            if stg_scores:
                s_avg = sum(stg_scores) / len(stg_scores)
                stage_summary += f"{stg}: {s_avg:.1f}/10, "

        # Generate the narrative summary
        summary_prompt = f"""
The candidate completed an interview with an overall average score of {avg:.1f}/10.

Stage-by-stage performance:
{stage_summary}

Please provide a comprehensive but concise summary covering:
1. Key strengths demonstrated
2. Areas for improvement
3. Overall assessment for the role
4. Specific recommendations

Keep it professional and constructive.
"""
        resp_sum = await session.llm.agenerate([[SystemMessage(content=summary_prompt)]])
        summary = resp_sum.generations[0][0].message.content
    else:
        summary = "Not enough scored answers to generate a comprehensive summary."
        stage_breakdown = None

    # 2) Only ask for a recommendation if we have an average
    recommendation = None
    if avg is not None:
        rec_prompt = f"""
Based on the candidate’s overall average score of {avg:.1f}/10 and the stage-by-stage
summary provided, would you recommend advancing this candidate to the next stage?
Respond with EXACTLY one word: “Yes” or “No”, and then in 1–2 sentences justify your choice.
"""
        resp_rec = await session.llm.agenerate([[SystemMessage(content=rec_prompt)]])
        recommendation = resp_rec.generations[0][0].message.content.strip()

    # 3) Persist everything
    interview_sessions.update_one(
        {"_id": session_id},
        {"$set": {
            "ended_at":        datetime.utcnow(),
            "average_score":   avg,
            "summary":         summary,
            "stage_breakdown": stage_breakdown,
            "recommendation":  recommendation
        }}
    )
    job_profiles.update_one(
        {"_id": ObjectId(doc["job_id"]), "scoredResumes.resumeId": doc["resume_id"]},
        {"$set": {
            "scoredResumes.$.interviewDone": True,
            "scoredResumes.$.sessionId":     session_id
        }}
    )

    # 4) Send back over the WebSocket
    payload = {
        "text":            "⏰ Interview completed! Here's your comprehensive assessment:",
        "summary":         summary,
        "average_score":   avg,
        "stage_breakdown": stage_breakdown,
    }
    if recommendation is not None:
        payload["recommendation"] = recommendation

    await websocket.send_json(payload)
    await websocket.close()



async def finalize_after_10min(session, session_id, websocket):
    try:
        await asyncio.sleep(600)  # 10 minutes
        await finalize_interview(session, session_id, websocket)
    except asyncio.CancelledError:
        pass


@router.websocket("/ws/interview/{job_id}/{resume_id}")
async def interview_ws(websocket: WebSocket, job_id: str, resume_id: str):
    # 1) Fetch job & candidate entry
    job = job_profiles.find_one({"_id": ObjectId(job_id)})
    if not job:
        await websocket.accept()
        await websocket.send_json({"error": "Job not found"})
        await websocket.close()
        return

    entry = next(
        (r for r in job.get("scoredResumes", []) if str(r.get("resumeId")) == resume_id),
        None
    )
    if not entry:
        await websocket.accept()
        await websocket.send_json({"error": "Resume not found"})
        await websocket.close()
        return

    # 2) Enforce schedule window
    sched = entry.get("interview_schedule")
    now = datetime.utcnow()
    if not sched:
        await websocket.accept()
        await websocket.send_json({"error": "Interview not scheduled for this candidate"})
        await websocket.close()
        return
    start, end = sched["start"], sched["end"]
    if now < start:
        await websocket.accept()
        await websocket.send_json({
            "error":    "Interview window hasn't opened yet",
            "startsAt": start.isoformat()
        })
        await websocket.close()
        return
    if now > end:
        await websocket.accept()
        await websocket.send_json({"error": "Interview window has expired"})
        await websocket.close()
        return

    # 3) Accept WS and create session doc
    await websocket.accept()
    sess_doc = {
        "job_id":           job_id,
        "resume_id":        resume_id,
        "scheduled_start":  start,
        "scheduled_end":    end,
        "started_at":       now,
        "history":          [],
        "stage_progression": []
    }
    session_id = interview_sessions.insert_one(sess_doc).inserted_id
    session = InterviewSession(job["description"], entry["text"], max_questions=8)

    # 4) Auto-finalize timer
    auto_task = asyncio.create_task(finalize_after_10min(session, session_id, websocket))

    async def send_response(text: str):
        await websocket.send_json({
            "text":            text,
            "question_count":  session.question_count,
            "max_questions":   session.max_questions,
            "current_stage":   session.interview_stages[session.current_stage]["name"],
            "stage_progress":  f"{session.current_stage+1}/{len(session.interview_stages)}"
        })

    try:
        # Initial question
        last_q = await session.get_response()
        await send_response(last_q)

        # Main loop
        while True:
            msg = await websocket.receive_json()

            # Telemetry events
            if msg.get("type") in {"tab-switch", "gaze", "object-detect", "not-looking"}:
                field = {
                    "tab-switch": "tabEvents",
                    "gaze": "gazeData",
                    "object-detect": "objectEvents",
                    "not-looking": "warningEvents"
                }[msg["type"]]
                interview_sessions.update_one(
                    {"_id": session_id},
                    {"$push": {field: {**msg, "timestamp": datetime.utcnow()}}}
                )
                continue

            answer = msg.get("answer", "").strip()
            if not answer:
                await websocket.send_json({"error": "Empty answer received"})
                continue
            if answer.lower() in {"quit", "exit", "end interview"}:
                break

            # Score & record
            score = await session.score_answer(last_q, answer)
            interview_scores.insert_one({
                "job_id":         job_id,
                "resume_id":      resume_id,
                "question_number":session.question_count,
                "question":       last_q,
                "answer":         answer,
                "score":          score,
                "timestamp":      datetime.utcnow(),
                "stage":          session.interview_stages[session.current_stage]["name"]
            })
            session.add_to_history(last_q, answer, score)
            interview_sessions.update_one(
                {"_id": session_id},
                {"$push": {"history": {
                    "question_number":session.question_count,
                    "question":       last_q,
                    "answer":         answer,
                    "score":          score,
                    "timestamp":      datetime.utcnow(),
                    "stage":          session.interview_stages[session.current_stage]["name"]
                }}}
            )
            interview_sessions.update_one(
                {"_id": session_id},
                {"$push": {"stage_progression": {
                    "stage":          session.interview_stages[session.current_stage]["name"],
                    "question_number":session.question_count,
                    "timestamp":      datetime.utcnow()
                }}}
            )

            # Next question with retry
            backoff = 1
            for attempt in range(3):
                try:
                    last_q = await session.get_response(answer)
                    break
                except Exception as e:
                    logger.error(f"Error generating question: {e}")
                    if attempt == 2:
                        last_q = session.get_fallback_question()
                        break
                    await asyncio.sleep(backoff)
                    backoff *= 2

            await send_response(last_q)
            if session.question_count >= session.max_questions:
                break

    except WebSocketDisconnect:
        return
    finally:
        if not auto_task.done():
            auto_task.cancel()
            await finalize_interview(session, session_id, websocket)
        await websocket.close()


@router.get("/session/{session_id}")
async def get_interview_session(session_id: str):
    """Fetch the full interview session document by its ID."""
    doc = interview_sessions.find_one({"_id": ObjectId(session_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Interview session not found")
    doc["_id"] = str(doc["_id"])
    doc["job_id"] = str(doc["job_id"])
    doc["resume_id"] = str(doc["resume_id"])
    return {"session": doc}


@router.post("/admin/reset-interview/{session_id}")
async def reset_interview(
    session_id: str,
    admin = Depends(get_current_user)
):
    """
    Deletes the in-flight session and clears the interviewDone flag
    so the candidate can be re-interviewed.
    """
    interview_sessions.delete_one({"_id": ObjectId(session_id)})
    job_profiles.update_one(
        { "scoredResumes.sessionId": ObjectId(session_id) },
        { "$unset": {
            "scoredResumes.$.interviewDone": "",
            "scoredResumes.$.sessionId": ""
        }}
    )
    return {"ok": True, "message": "Interview session reset"}


@router.get("/analytics/{job_id}")
async def get_interview_analytics(job_id: str):
    """Get analytics for all interviews for a specific job"""
    pipeline = [
        {"$match": {"job_id": job_id}},
        {"$unwind": "$history"},
        {"$group": {
            "_id": "$history.stage",
            "avg_score": {"$avg": "$history.score"},
            "question_count": {"$sum": 1},
            "scores": {"$push": "$history.score"}
        }},
        {"$sort": {"_id": 1}}
    ]
    stage_analytics = list(interview_sessions.aggregate(pipeline))
    overall_pipeline = [
        {"$match": {"job_id": job_id}},
        {"$group": {
            "_id": None,
            "total_interviews": {"$sum": 1},
            "avg_score": {"$avg": "$average_score"},
            "completion_rate": {"$avg": {"$cond": [{"$ne": ["$ended_at", None]}, 1, 0]}}
        }}
    ]
    overall_stats = list(interview_sessions.aggregate(overall_pipeline))
    return {
        "stage_analytics": stage_analytics,
        "overall_stats": overall_stats[0] if overall_stats else None,
        "job_id": job_id
    }


@router.get("/session/by-resume/{resume_id}")
async def get_full_session_by_resume(resume_id: str):
    """
    Fetch the latest interview session for a given resume_id,
    including the full Q&A history, average score, recommendation, and summary.
    """
    doc = interview_sessions.find_one(
        {"resume_id": resume_id},
        sort=[("started_at", -1)]
    )
    if not doc:
        raise HTTPException(status_code=404, detail="No interview session found for that resume_id")

    session = {
        "session_id":       str(doc["_id"]),
        "job_id":           str(doc["job_id"]),
        "resume_id":        doc["resume_id"],
        "scheduled_start":  doc["scheduled_start"].isoformat(),
        "scheduled_end":    doc["scheduled_end"].isoformat(),
        "started_at":       doc["started_at"].isoformat(),
        "ended_at":         doc.get("ended_at").isoformat() if doc.get("ended_at") else None,
        "average_score":    doc.get("average_score"),
        "recommendation":   doc.get("recommendation"),
        "summary":          doc.get("summary"),
        "stage_breakdown":  doc.get("stage_breakdown"),
        "history": [
            {
                "question_number": h["question_number"],
                "question":        h["question"],
                "answer":          h["answer"],
                "score":           h.get("score"),
                "stage":           h.get("stage"),
                "timestamp":       h["timestamp"].isoformat(),
            }
            for h in doc.get("history", [])
        ],
        "stage_progression": [
            {
                "stage":           sp["stage"],
                "question_number": sp["question_number"],
                "timestamp":       sp["timestamp"].isoformat(),
            }
            for sp in doc.get("stage_progression", [])
        ],
    }

    return {"session": session}
