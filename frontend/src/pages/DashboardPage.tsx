import { useEffect, useRef, useState } from "react";
import { Mic, Stethoscope, LogOut } from "lucide-react";

import DoctorAssistPanel from "../components/DoctorAssistPanel";
import NewPatientForm from "../components/NewPatientForm";
import PatientHistoryPanel from "../components/PatientHistoryPanel";
import PatientSelector from "../components/PatientSelector";
import RagChatPanel from "../components/RagChatPanel";
import RecordingControls from "../components/RecordingControls";
import StructuredDataPanel from "../components/StructuredDataPanel";
import TranscriptPanel from "../components/TranscriptPanel";
import { useAuth } from "../context/AuthContext";
import { apiClient } from "../lib/api";
import type {
  ClinicalSession,
  DoctorAssist,
  Patient,
  PatientCreateInput,
  PatientHistory,
  RagAnswer,
  StructuredClinicalData,
} from "../lib/types";

const emptyStructured: StructuredClinicalData = {
  symptoms: [],
  duration: "",
  diagnosis: "",
  medications: [],
};

const emptyAssist: DoctorAssist = {
  suggested_diagnosis: "",
  missing_fields: [],
  red_flags: [],
};

export default function DashboardPage() {
  const { token, user, logout } = useAuth();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [transcript, setTranscript] = useState("");
  const [transcriptChunks, setTranscriptChunks] = useState<string[]>([]);
  const [structuredData, setStructuredData] = useState<StructuredClinicalData>(emptyStructured);
  const [doctorAssist, setDoctorAssist] = useState<DoctorAssist>(emptyAssist);
  const [languages, setLanguages] = useState<string[]>([]);
  const [currentSession, setCurrentSession] = useState<ClinicalSession | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingTranscription, setIsProcessingTranscription] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Ready to capture a consultation.");
  const [ragAnswer, setRagAnswer] = useState<RagAnswer | null>(null);
  const [patientHistory, setPatientHistory] = useState<PatientHistory | null>(null);
  const [loadingRag, setLoadingRag] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [creatingPatient, setCreatingPatient] = useState(false);
  const [speechLanguage, setSpeechLanguage] = useState("en-IN");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (!token) {
      return;
    }

    apiClient
      .getPatients()
      .then((response) => {
        setPatients(response);
        if (response[0]) {
          setSelectedPatientId(response[0].id);
        }
        setError(null);
      })
      .catch((fetchError) => {
        setError(fetchError instanceof Error ? fetchError.message : "Unable to load patients");
      });
  }, [token]);

  useEffect(() => {
    setRagAnswer(null);
    setPatientHistory(null);
  }, [selectedPatientId]);

  useEffect(() => {
    return () => {
      stopRecorder(mediaRecorderRef.current);
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function startRecording() {
    if (!token || !selectedPatientId) {
      setError("Select a patient before starting the consultation.");
      return;
    }

    if (!("mediaDevices" in navigator) || typeof MediaRecorder === "undefined") {
      setError("This browser does not support microphone recording for the live transcript.");
      return;
    }

    let startedSession: ClinicalSession | null = null;
    try {
      setError(null);
      setStatusMessage("Preparing consultation recording...");
      setTranscript("");
      setTranscriptChunks([]);
      setStructuredData(emptyStructured);
      setDoctorAssist(emptyAssist);
      setLanguages([]);
      recordedChunksRef.current = [];

      const session = await apiClient.createSession(selectedPatientId);
      startedSession = session;
      setCurrentSession(session);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      mediaStreamRef.current = stream;

      const mimeType = getSupportedMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current = [...recordedChunksRef.current, event.data];
        }
      };
      recorder.onerror = () => {
        setError("Microphone capture failed while recording audio.");
        setStatusMessage("Recording error. Try refreshing and starting again.");
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setStatusMessage("Recording started. Sarvam transcription will run after you stop the consultation.");
    } catch (startError) {
      if (startedSession) {
        try {
          await apiClient.stopSession(startedSession.id);
        } catch {
          // Best-effort cleanup for partially created sessions.
        }
      }
      setCurrentSession(null);
      setError(startError instanceof Error ? startError.message : "Unable to start recording");
      setStatusMessage("Unable to start capture.");
    }
  }

  async function stopRecording() {
    if (!currentSession || !mediaRecorderRef.current) {
      return;
    }

    try {
      setError(null);
      setIsProcessingTranscription(true);
      setStatusMessage("Finalizing the recording and uploading audio to Sarvam...");

      const recordedBlob = await stopRecorderAndCollectBlob(mediaRecorderRef.current);
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaRecorderRef.current = null;
      mediaStreamRef.current = null;

      setStatusMessage("Sarvam is transcribing the complete consultation. This can take a few moments...");
      const update = await apiClient.uploadSessionAudio(
        currentSession.id,
        recordedBlob,
        `consultation${extensionForMimeType(recordedBlob.type)}`,
        normalizeBrowserLanguage(speechLanguage),
      );
      setTranscript(update.full_transcript);
      setTranscriptChunks(splitTranscriptIntoCards(update.full_transcript));
      setLanguages(update.detected_languages);
      setStructuredData(update.structured_data);
      setDoctorAssist(update.doctor_assist);

      await apiClient.stopSession(currentSession.id);
      setStatusMessage("Sarvam transcript generated and saved to the patient record.");
    } catch (stopError) {
      try {
        await apiClient.stopSession(currentSession.id);
      } catch {
        // Best-effort session closure when post-recording transcription fails.
      }
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaRecorderRef.current = null;
      mediaStreamRef.current = null;
      setError(stopError instanceof Error ? stopError.message : "Unable to finalize session audio");
      setStatusMessage("Recording stopped, but Sarvam transcription did not complete.");
    } finally {
      recordedChunksRef.current = [];
      setIsRecording(false);
      setIsProcessingTranscription(false);
      setCurrentSession(null);
    }
  }

  async function handleCreatePatient(payload: PatientCreateInput) {
    try {
      setCreatingPatient(true);
      setError(null);
      const patient = await apiClient.createPatient(payload);
      setPatients((current) => [patient, ...current]);
      setSelectedPatientId(patient.id);
      setStatusMessage(`Patient ${patient.full_name} created with ID ${patient.external_id} and selected.`);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to create patient");
      throw createError;
    } finally {
      setCreatingPatient(false);
    }
  }

  async function handleRagQuestion(question: string) {
    if (!selectedPatientId) {
      return;
    }
    try {
      setLoadingRag(true);
      setRagAnswer(await apiClient.queryRag(selectedPatientId, question));
    } catch (ragError) {
      setError(ragError instanceof Error ? ragError.message : "RAG request failed");
    } finally {
      setLoadingRag(false);
    }
  }

  async function handleLoadHistory() {
    if (!selectedPatientId) {
      return;
    }
    try {
      setLoadingHistory(true);
      setError(null);
      setPatientHistory(await apiClient.getPatientHistory(selectedPatientId));
      setStatusMessage("Patient history loaded from database.");
    } catch (historyError) {
      setError(historyError instanceof Error ? historyError.message : "Unable to load patient history");
    } finally {
      setLoadingHistory(false);
    }
  }

  async function handleDownloadHistory() {
    if (!selectedPatientId) {
      return;
    }
    try {
      setLoadingHistory(true);
      setError(null);
      const blob = await apiClient.downloadPatientHistory(selectedPatientId);
      const selectedPatient = patients.find((patient) => patient.id === selectedPatientId);
      const filename = `${selectedPatient?.external_id ?? selectedPatientId}-history.json`;
      downloadBlob(blob, filename);
      setStatusMessage("Patient history downloaded locally.");
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Unable to download patient history");
    } finally {
      setLoadingHistory(false);
    }
  }

  async function handleDownloadVisitReport(recordId: string) {
    try {
      setError(null);
      const blob = await apiClient.downloadVisitReport(recordId);
      const selectedPatient = patients.find((patient) => patient.id === selectedPatientId);
      const filename = `${selectedPatient?.external_id ?? "patient"}-visit-report.pdf`;
      downloadBlob(blob, filename);
      setStatusMessage("Visit report downloaded as PDF.");
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Unable to download visit report");
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 glass-panel flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="rounded-3xl bg-slate-950 p-4 text-white">
              <Stethoscope className="h-7 w-7" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Doctor Dashboard</p>
              <h1 className="text-3xl font-extrabold text-ink">Voice-driven clinical workspace</h1>
              <p className="text-sm text-slate-600">
                Signed in as {user?.full_name ?? "Doctor"} • multilingual live capture with strict JSON extraction
              </p>
            </div>
          </div>

          <button
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            onClick={logout}
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </header>

        {error ? (
          <div className="mb-6 rounded-3xl bg-rose-50 px-5 py-4 text-sm font-medium text-rose-700">{error}</div>
        ) : null}

        <section className="mb-6 grid gap-4 lg:grid-cols-[1fr_1fr]">
          <PatientSelector
            patients={patients}
            selectedPatientId={selectedPatientId}
            onChange={setSelectedPatientId}
          />
          <RecordingControls
            isRecording={isRecording || isProcessingTranscription}
            isConnected={!isProcessingTranscription && !!currentSession}
            statusText={statusMessage}
            speechLanguage={speechLanguage}
            onSpeechLanguageChange={setSpeechLanguage}
            onStart={startRecording}
            onStop={stopRecording}
          />
        </section>

        <section className="mb-6">
          <NewPatientForm isSubmitting={creatingPatient} onCreate={handleCreatePatient} />
        </section>

        <section className="mb-6 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <TranscriptPanel transcript={transcript} transcriptChunks={transcriptChunks} languages={languages} />
          <div className="space-y-6">
            <StructuredDataPanel data={structuredData} />
            <DoctorAssistPanel assist={doctorAssist} />
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="glass-panel flex items-center gap-4 p-6">
            <div className="rounded-3xl bg-accent/10 p-4 text-accent">
              <Mic className="h-8 w-8" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Assist Mode</p>
              <h2 className="text-xl font-bold text-ink">Missing-field awareness stays visible during the encounter.</h2>
              <p className="text-sm text-slate-600">
                Use the panels to spot absent duration, medications, allergies, or vitals before closing the note.
              </p>
            </div>
          </div>

          <RagChatPanel disabled={loadingRag || !selectedPatientId} answer={ragAnswer} onSubmit={handleRagQuestion} />
        </section>

        <section className="mt-6">
          <PatientHistoryPanel
            disabled={loadingHistory || !selectedPatientId}
            history={patientHistory}
            onDownload={handleDownloadHistory}
            onDownloadReport={handleDownloadVisitReport}
            onLoad={handleLoadHistory}
          />
        </section>
      </div>
    </main>
  );
}

function getSupportedMimeType(): string | undefined {
  const candidates = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"];
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate));
}

function stopRecorder(recorder: MediaRecorder | null) {
  if (!recorder || recorder.state === "inactive") {
    return;
  }
  recorder.stop();
}

function normalizeBrowserLanguage(language: string): string {
  const normalized = language.toLowerCase();
  if (normalized.startsWith("en")) {
    return "english";
  }
  if (normalized.startsWith("hi")) {
    return "hindi";
  }
  if (normalized.startsWith("mr")) {
    return "marathi";
  }
  return normalized;
}

function stopRecorderAndCollectBlob(recorder: MediaRecorder): Promise<Blob> {
  if (recorder.state === "inactive") {
    return Promise.resolve(new Blob());
  }

  return new Promise((resolve, reject) => {
    const chunks: Blob[] = [];

    const handleData = (event: BlobEvent) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    const handleStop = () => {
      recorder.removeEventListener("dataavailable", handleData);
      recorder.removeEventListener("stop", handleStop);
      recorder.removeEventListener("error", handleError);
      resolve(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
    };

    const handleError = () => {
      recorder.removeEventListener("dataavailable", handleData);
      recorder.removeEventListener("stop", handleStop);
      recorder.removeEventListener("error", handleError);
      reject(new Error("Unable to finalize the recorded consultation audio."));
    };

    recorder.addEventListener("dataavailable", handleData);
    recorder.addEventListener("stop", handleStop);
    recorder.addEventListener("error", handleError);
    recorder.stop();
  });
}

function extensionForMimeType(mimeType: string): string {
  const normalized = mimeType.split(";", 1)[0].trim().toLowerCase();
  const mapping: Record<string, string> = {
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
    "audio/m4a": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
  };
  return mapping[normalized] ?? ".webm";
}

function splitTranscriptIntoCards(transcript: string): string[] {
  return transcript
    .split(/(?<=[.!?])\s+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .slice(0, 20);
}

function downloadBlob(blob: Blob, filename: string) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
