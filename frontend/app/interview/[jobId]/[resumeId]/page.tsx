"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient, LiveTranscriptionEvents } from "@deepgram/sdk";

interface Message {
  sender: "ai" | "you";
  text: string;
  timestamp?: Date;
}

interface InterviewStatus {
  question_count: number;
  max_questions: number;
  is_complete: boolean;
}
interface DeepgramTranscriptData {
  channel: {
    alternatives: Array<{
      transcript: string;
    }>;
  };
  is_final: boolean;
}

interface DeepgramConnection {
  on: (event: string, callback: (data: DeepgramTranscriptData) => void) => void;
  send: (data: ArrayBuffer) => void;
  finish: () => void;
}

export default function InterviewPage({
  params,
}: {
  params: Promise<{ jobId: string; resumeId: string }>;
}) {
  // Interview state
  const router = useRouter();
  const [jobId, setJobId] = useState("");
  const [resumeId, setResumeId] = useState("");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<InterviewStatus>({
    question_count: 0,
    max_questions: 8,
    is_complete: false,
  });

  // --- Webcam ---
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((stream) => {
        setVideoStream(stream);
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch(() => setError("Could not access webcam"));
    return () => {
      if (videoRef.current) videoRef.current.srcObject = null;
      if (videoStream) videoStream.getTracks().forEach(track => track.stop());
    };
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    if (videoRef.current && videoStream) videoRef.current.srcObject = videoStream;
  }, [videoStream]);

  // --- Deepgram Voice Input: FIXED! ---
  // const dgClientRef = useRef<ReturnType<typeof createClient> | null>(null);
  const dgConnRef = useRef<DeepgramConnection | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const bufferRef = useRef(""); // buffer persists per session

  // useEffect(() => {
  //   fetch("/api/deepgram-token")
  //     .then((res) => res.json())
  //     .then(({ token, error: tokErr }) => {
  //       if (tokErr) throw new Error(tokErr);
  //       dgClientRef.current = createClient({ accessToken: token });
  //     })
  //     .catch(() => setError("Could not fetch STT token"));
  // }, []);
  const cleanupVoice = () => {
    try { recorderRef.current?.stop(); } catch {}
    try { dgConnRef.current?.finish(); } catch {}
    recorderRef.current = null;
    dgConnRef.current = null;
    setIsVoiceActive(false);
    setLiveTranscript("");
    bufferRef.current = "";
  };
  
  const startVoice = async () => {
    // Check if screen sharing is active first
    if (!isScreenSharing) {
      setError("Please start screen sharing first before using voice input.");
      return;
    }
    
    cleanupVoice();
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
  
    setIsVoiceActive(true);
    setLiveTranscript("");
    bufferRef.current = "";
  
    // 🔥 Fetch a NEW Deepgram token EVERY TIME!
    let token;
    try {
      const tokenRes = await fetch("/api/deepgram-token");
      const tokenJson = await tokenRes.json();
      if (!tokenJson.token) throw new Error("No Deepgram token");
      token = tokenJson.token;
    } catch (err : unknown) {
      setError("Could not fetch Deepgram token" + err);
      setIsVoiceActive(false);
      return;
    }
  
    // 🔥 Create a new Deepgram client and connection
    const dgClient = createClient({ accessToken: token });
  
    // Setup mic
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err : unknown) {
      setError("Could not access microphone" + err);
      setIsVoiceActive(false);
      return;
    }
  
    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
    recorderRef.current = recorder;
  
    const dgConn = dgClient.listen.live({
      model: "nova-3",
      interim_results: true,
      punctuate: true,
    });
    dgConnRef.current = dgConn;
  
    dgConn.on(LiveTranscriptionEvents.Open, () => recorder.start(250));
  
    dgConn.on(LiveTranscriptionEvents.Transcript, (data: DeepgramTranscriptData) => {
      const txt = data.channel.alternatives[0]?.transcript.trim();
      if (txt && data.is_final) {
        bufferRef.current += (bufferRef.current ? " " : "") + txt;
        setLiveTranscript(bufferRef.current);
        setInput(bufferRef.current); // Fill the input box with the transcript
      } else if (txt) {
        setLiveTranscript(bufferRef.current + " " + txt);
      }
    });
  
    recorder.addEventListener("dataavailable", async (e) => {
      const buf = await e.data.arrayBuffer();
      dgConn.send(buf);
    });
  
    recorder.onstop = () => {
      setIsVoiceActive(false);
      stream.getTracks().forEach((track) => track.stop());
      try { dgConn.finish(); } catch {}
    };
  };
  
  const stopVoice = () => {
    cleanupVoice();
    // input is already set in startVoice's final result
  };
  // --- Enhanced Proctoring ---
  const [tabSwitchCount, setTabSwitchCount] = useState(0);
  const [proctorWarning, setProctorWarning] = useState<string | null>(null);
  const [interviewEndedByProctor, setInterviewEndedByProctor] = useState(false);

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.hidden) {
        const newCount = tabSwitchCount + 1;
        setTabSwitchCount(newCount);
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "tab-switch", count: newCount }));
        }
        if (newCount === 1) setProctorWarning("⚠️ Warning: You left the tab. 2 chances left before interview ends!");
        if (newCount === 2) setProctorWarning("⚠️ Last warning: Next tab switch will end your interview!");
        if (newCount >= 3) {
          ws?.send(JSON.stringify({ answer: "end interview" }));
          setError("Interview ended: You left the tab too many times.");
          setInterviewEndedByProctor(true);
        }
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
    // eslint-disable-next-line
  }, [ws, tabSwitchCount]);

  // --- Screen Share Proctoring ---
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const screenShareRef = useRef<MediaStream | null>(null);

  const startScreenShare = async () => {
    if (!navigator.mediaDevices.getDisplayMedia) {
      setError("Screen sharing not supported by your browser.");
      return;
    }
    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      screenShareRef.current = screenStream;
      setIsScreenSharing(true);
      setError(null); // Clear any previous errors
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "screen-share", action: "started" }));
      }
      screenStream.getVideoTracks()[0].onended = () => {
        setIsScreenSharing(false);
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "screen-share", action: "ended" }));
        }
      };
    } catch {
      setError("Screen sharing was declined. For proctoring, please share your screen.");
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "screen-share", action: "declined" }));
      }
    }
  };

  // Prompt for screen share on mount if not already sharing
  useEffect(() => {
    if (!isScreenSharing && isConnected && !status.is_complete && !interviewEndedByProctor) {
      startScreenShare();
    }
    // eslint-disable-next-line
  }, [isConnected, isScreenSharing, status.is_complete, interviewEndedByProctor]);

  // --- WebSocket Lifecycle ---
  useEffect(() => {
    (async () => {
      const p = await params;
      setJobId(p.jobId);
      setResumeId(p.resumeId);
    })();
    // eslint-disable-next-line
  }, [params]);

  useEffect(() => {
    if (!jobId || !resumeId) return;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const socket = new WebSocket(`${protocol}://${window.location.host}/api/ws/interview/${jobId}/${resumeId}`);

    socket.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    socket.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.error) {
          setError(data.error);
          setIsLoading(false);
          return;
        }
        const { text, question_count, max_questions } = data;
        setStatus({
          question_count,
          max_questions: max_questions || status.max_questions,
          is_complete: question_count >= (max_questions || status.max_questions),
        });
        setMessages((ms) => [
          ...ms,
          { sender: "ai", text, timestamp: new Date() },
        ]);
        setIsLoading(false);
      } catch {
        setError("Invalid response from server");
        setIsLoading(false);
      }
    };

    socket.onclose = (ev) => {
      setIsConnected(false);
      if (ev.code !== 1000) setError("Connection lost. Please refresh.");
    };

    socket.onerror = () => setError("Connection error. Please try again.");

    setWs(socket);
    return () => {
      socket.close();
    };
    // eslint-disable-next-line
  }, [jobId, resumeId]);

  // Auto-scroll
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // TTS
  function speakText(text: string) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utter = new window.SpeechSynthesisUtterance(text);
    utter.rate = 1.0;
    utter.pitch = 1.08;
    window.speechSynthesis.speak(utter);
  }

  useEffect(() => {
    if (messages.length && messages[messages.length - 1].sender === "ai") {
      speakText(messages[messages.length - 1].text);
    }
  }, [messages]);

  const sendAnswer = () => {
    if (interviewEndedByProctor) return;
    
    // Check if screen sharing is active first
    if (!isScreenSharing) {
      setError("Please start screen sharing first before sending messages.");
      return;
    }
    
    if (!ws || ws.readyState !== WebSocket.OPEN || !input.trim() || isLoading)
      return;
    setIsLoading(true);
    setError(null);
    ws.send(JSON.stringify({ answer: input.trim() }));
    setMessages((ms) => [
      ...ms,
      { sender: "you", text: input.trim(), timestamp: new Date() },
    ]);
    setInput("");
    setLiveTranscript("");
    bufferRef.current = "";
  };

  const progress = (status.question_count / status.max_questions) * 100;

  // --- TIMER (10 MINUTES AUTO END) ---
  const TIMER_SEC = 600; // 10 min = 600 sec
  const [timerSec, setTimerSec] = useState(TIMER_SEC);
  const [timerActive, setTimerActive] = useState(true);

  useEffect(() => {
    if (!timerActive || status.is_complete || interviewEndedByProctor) return;
    if (timerSec <= 0) {
      // End interview if timer hits 0
      setTimerActive(false);
      ws?.send(JSON.stringify({ answer: "end interview" }));
      setError("Interview ended: Time limit reached.");
      setInterviewEndedByProctor(true);
      return;
    }
    const t = setTimeout(() => setTimerSec(s => s - 1), 1000);
    return () => clearTimeout(t);
    // eslint-disable-next-line
  }, [timerSec, timerActive, status.is_complete, interviewEndedByProctor]);

  // Timer display: MM:SS
  const timerMMSS = `${String(Math.floor(timerSec / 60)).padStart(2, "0")}:${String(timerSec % 60).padStart(2, "0")}`;

  // --- UI ---
  // Auto-stop screen share when interview ends
  useEffect(() => {
    if ((status.is_complete || interviewEndedByProctor) && isScreenSharing) {
      try {
        screenShareRef.current?.getTracks().forEach((t) => t.stop());
      } catch {}
      setIsScreenSharing(false);
      if (ws && ws.readyState === WebSocket.OPEN) {
        try { ws.send(JSON.stringify({ type: "screen-share", action: "ended" })); } catch {}
      }
    }
    // eslint-disable-next-line
  }, [status.is_complete, interviewEndedByProctor]);

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Enhanced Header */}
      <div className="bg-white/90 backdrop-blur-md shadow-lg border-b border-white/20 relative">
        <div className="max-w-6xl mx-auto px-8 py-6">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <div className="flex items-center space-x-4 mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 rounded-full bg-gradient-to-r from-emerald-400 to-blue-500 animate-pulse"></div>
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
                    AI Interview Session
                  </h1>
                </div>
                {isConnected ? (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                    <div className="w-2 h-2 bg-emerald-400 rounded-full mr-2 animate-pulse"></div>
                    Connected
                  </span>
                ) : (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                    <div className="w-2 h-2 bg-red-400 rounded-full mr-2"></div>
                    Disconnected
                  </span>
                )}
                {/* --- TIMER VISUAL --- */}
                <span className="ml-4 inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/><path stroke="currentColor" strokeWidth="2" d="M12 6v6l4 2"/></svg>
                  <span className={timerSec < 60 ? "font-bold text-red-600" : ""}>{timerMMSS}</span>
                </span>
              </div>
              
              {/* Enhanced Progress Bar */}
              <div className="flex items-center space-x-4">
                <div className="flex-1 max-w-md">
                  <div className="flex justify-between text-sm text-slate-600 mb-2">
                    <span>Progress</span>
                    <span>{status.question_count} of {status.max_questions}</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full transition-all duration-500 ease-out relative"
                      style={{ width: `${progress}%` }}
                    >
                      <div className="absolute inset-0 bg-white/30 rounded-full animate-pulse"></div>
                    </div>
                  </div>
                </div>
                
                {/* Status Indicators */}
                <div className="flex space-x-2">
                  {isScreenSharing && (
                    <div className="inline-flex items-center px-3 py-1.5 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-full text-xs font-medium shadow-lg">
                      <svg className="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M3 4a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 13a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1H4a1 1 0 01-1-1v-3zM12 4a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1V4zM12 13a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-3z" clipRule="evenodd" />
                      </svg>
                      Screen Sharing
                    </div>
                  )}
                  {tabSwitchCount > 0 && (
                    <div className="inline-flex items-center px-3 py-1.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-full text-xs font-medium">
                      <svg className="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      {tabSwitchCount} Warning{tabSwitchCount > 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Enhanced Video Preview */}
            <div className="ml-8 relative">
              <div className="relative group">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-40 h-32 rounded-2xl border-4 border-white shadow-xl object-cover transition-transform group-hover:scale-105"
                  style={{ background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}
                />
                <div className="absolute -bottom-2 -right-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white px-3 py-1 rounded-full text-xs font-medium shadow-lg">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                    <span>Live</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Enhanced Action Bar */}
        <div className="border-t border-slate-200/50 bg-white/50 backdrop-blur-sm">
          <div className="max-w-6xl mx-auto px-8 py-4">
            <div className="flex justify-between items-center">
              <div className="flex space-x-3">
                <button
                  onClick={startVoice}
                  disabled={!isConnected || isVoiceActive || interviewEndedByProctor || !isScreenSharing}
                  className={`inline-flex items-center px-4 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 shadow-lg ${
                    isVoiceActive 
                      ? 'bg-gradient-to-r from-red-500 to-red-600 text-white shadow-red-200' 
                      : !isScreenSharing
                      ? 'bg-gradient-to-r from-slate-300 to-slate-400 text-slate-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:from-emerald-600 hover:to-teal-700 disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed'
                  }`}
                >
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                  </svg>
                  {isVoiceActive ? 'Recording...' : !isScreenSharing ? 'Start Screen Share First' : 'Start Voice'}
                </button>
                
                <button
                  onClick={stopVoice}
                  disabled={!isVoiceActive || interviewEndedByProctor}
                  className="inline-flex items-center px-4 py-2.5 rounded-xl font-medium text-sm bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700 disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed transition-all duration-200 shadow-lg"
                >
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Done Speaking
                </button>
                
                <button
                  onClick={startScreenShare}
                  disabled={isScreenSharing || interviewEndedByProctor}
                  className="inline-flex items-center px-4 py-2.5 rounded-xl font-medium text-sm bg-gradient-to-r from-purple-500 to-indigo-600 text-white hover:from-purple-600 hover:to-indigo-700 disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed transition-all duration-200 shadow-lg"
                >
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 4a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 13a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1H4a1 1 0 01-1-1v-3zM12 4a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1V4zM12 13a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-3z" clipRule="evenodd" />
                  </svg>
                  {isScreenSharing ? 'Sharing...' : 'Share Screen'}
                </button>
              </div>
              
              <button
                onClick={() => ws?.send(JSON.stringify({ answer: "end interview" }))}
                disabled={!isConnected || interviewEndedByProctor}
                className="inline-flex items-center px-6 py-2.5 rounded-xl font-medium text-sm bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed transition-all duration-200 shadow-lg"
              >
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
                End Interview
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced Alerts */}
      {(proctorWarning || error) && (
        <div className="mx-auto my-6 max-w-4xl px-8">
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-l-4 border-amber-400 rounded-xl p-6 shadow-lg">
            <div className="flex items-start">
              <svg className="w-6 h-6 text-amber-500 mr-3 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                {proctorWarning && <div className="text-amber-800 font-medium">{proctorWarning}</div>}
                {error && <div className="text-amber-800">{error}</div>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Screen Share Required Alert */}
      {!isScreenSharing && isConnected && !status.is_complete && !interviewEndedByProctor && (
        <div className="mx-auto my-6 max-w-4xl px-8">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-400 rounded-xl p-6 shadow-lg">
            <div className="flex items-start">
              <svg className="w-6 h-6 text-blue-500 mr-3 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <div className="text-blue-800 font-medium mb-2">Screen Sharing Required</div>
                <div className="text-blue-700 text-sm">
                  Please start screen sharing to begin the interview. This is required for proctoring purposes.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Live Transcript */}
      {isVoiceActive && (
        <div className="mx-auto my-4 max-w-4xl px-8">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 shadow-lg">
            <div className="flex items-center space-x-3">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
              </div>
              <span className="font-semibold text-slate-700">Live Transcript:</span>
              <span className="text-slate-600 flex-1">{liveTranscript || "Listening..."}</span>
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Chat Messages */}
      <div className="flex-1 overflow-y-auto px-8 py-4">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.sender === "you" ? "justify-end" : "justify-start"}`}
            >
              <div className={`max-w-3xl ${m.sender === "you" ? "ml-16" : "mr-16"}`}>
                <div
                  className={`px-6 py-4 rounded-2xl shadow-lg backdrop-blur-sm transition-all duration-200 hover:shadow-xl ${
                    m.sender === "you"
                      ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
                      : "bg-white/80 border border-white/60 text-slate-800"
                  }`}
                >
                  <div className="whitespace-pre-wrap leading-relaxed">{m.text}</div>
                  {m.timestamp && (
                    <div
                      className={`text-xs mt-3 ${
                        m.sender === "you" ? "text-blue-100" : "text-slate-400"
                      }`}
                    >
                      {m.timestamp.toLocaleTimeString()}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/80 backdrop-blur-sm border border-white/60 px-6 py-4 rounded-2xl shadow-lg flex items-center space-x-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                </div>
                <span className="text-slate-600 font-medium">AI is thinking...</span>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {/* Enhanced Input Area */}
      {!status.is_complete && !interviewEndedByProctor && (
        <div className="bg-white/90 backdrop-blur-md border-t border-white/20 p-8">
          <div className="flex items-end space-x-4 max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <textarea
                className={`w-full border-2 rounded-2xl px-6 py-4 resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-white/80 backdrop-blur-sm shadow-lg placeholder-slate-400 ${
                  !isScreenSharing 
                    ? 'border-slate-300 bg-slate-50 cursor-not-allowed' 
                    : 'border-slate-200'
                }`}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendAnswer();
                  }
                }}
                placeholder={!isScreenSharing ? "Please start screen sharing first..." : "Type your response or use voice input..."}
                rows={3}
                disabled={!isConnected || isLoading || interviewEndedByProctor || !isScreenSharing}
              />
              {input.length > 0 && (
                <div className="absolute bottom-2 right-2 text-xs text-slate-400">
                  {input.length} characters
                </div>
              )}
            </div>
            <button
              onClick={sendAnswer}
              disabled={!input.trim() || !isConnected || isLoading || interviewEndedByProctor || !isScreenSharing}
              className="inline-flex items-center px-8 py-4 rounded-2xl font-semibold bg-gradient-to-r from-blue-600 to-indigo-700 text-white hover:from-blue-700 hover:to-indigo-800 disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Sending...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                  </svg>
                  Send
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Enhanced Completion Screen */}
      {(status.is_complete || interviewEndedByProctor) && (
        <div className="bg-gradient-to-br from-emerald-50 via-teal-50 to-blue-50 border-t border-emerald-200 p-12">
          <div className="max-w-2xl mx-auto text-center">
            <div className="mb-8">
              {interviewEndedByProctor ? (
                <div className="w-20 h-20 bg-gradient-to-r from-red-400 to-red-600 rounded-full flex items-center justify-center mx-auto mb-6">
                  <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </div>
              ) : (
                <div className="w-20 h-20 bg-gradient-to-r from-emerald-400 to-teal-600 rounded-full flex items-center justify-center mx-auto mb-6">
                  <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </div>
            
            <h3 className={`text-3xl font-bold mb-4 bg-gradient-to-r bg-clip-text text-transparent ${
              interviewEndedByProctor 
                ? 'from-red-600 to-red-800' 
                : 'from-emerald-600 to-teal-800'
            }`}>
              {interviewEndedByProctor ? 'Interview Terminated' : 'Interview Complete!'}
            </h3>
            
            <p className={`text-lg leading-relaxed ${
              interviewEndedByProctor ? 'text-red-700' : 'text-emerald-700'
            }`}>
              {interviewEndedByProctor
                ? "Your session was ended due to proctoring violations or time limit. Please contact support if you believe this was a mistake."
                : "Thank you for completing the interview. We'll review your responses and be in touch with next steps soon."}
            </p>
            
            {!interviewEndedByProctor && (
              <div className="mt-8 p-6 bg-white/60 backdrop-blur-sm rounded-2xl border border-white/80 shadow-lg">
                <h4 className="font-semibold text-slate-800 mb-2">What happens next?</h4>
                <div className="text-sm text-slate-600 space-y-2">
                  <p>• Our team will review your interview within 24-48 hours</p>
                  <p>• Youll receive an email update on your application status</p>
                  <p>• If selected, well schedule a follow-up interview</p>
                </div>
              </div>
            )}
            
            <div className="mt-8">
              <button
                onClick={() => router.push('/interview/over')}
                className="inline-flex items-center px-6 py-3 rounded-xl font-medium bg-gradient-to-r from-slate-600 to-slate-700 text-white hover:from-slate-700 hover:to-slate-800 transition-all duration-200 shadow-lg"
              >
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                </svg>
                Return to Dashboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
