import type {
  ClinicalSession,
  ClinicalSocketUpdate,
  LoginResponse,
  Patient,
  PatientCreateInput,
  PatientPortalDashboard,
  PatientHistory,
  RagAnswer,
  RecordItem,
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (typeof window !== "undefined" &&
  !["localhost", "127.0.0.1"].includes(window.location.hostname)
    ? "/api"
    : "http://localhost:8000/api/v1");

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  async login(username: string, password: string): Promise<LoginResponse> {
    const body = new URLSearchParams();
    body.set("username", username);
    body.set("password", password);

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return this.handleResponse<LoginResponse>(response);
  }

  async patientLogin(patientId: string, fullName: string, age: number): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/patient-login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_id: patientId,
        full_name: fullName,
        age,
      }),
    });
    return this.handleResponse<LoginResponse>(response);
  }

  async getPatients(): Promise<Patient[]> {
    const response = await fetch(`${API_BASE_URL}/patients`, {
      headers: this.authHeaders(),
    });
    return this.handleResponse<Patient[]>(response);
  }

  async createPatient(payload: PatientCreateInput): Promise<Patient> {
    const response = await fetch(`${API_BASE_URL}/patients`, {
      method: "POST",
      headers: this.jsonHeaders(),
      body: JSON.stringify(payload),
    });
    return this.handleResponse<Patient>(response);
  }

  async createSession(patientId: string): Promise<ClinicalSession> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      method: "POST",
      headers: this.jsonHeaders(),
      body: JSON.stringify({ patient_id: patientId }),
    });
    return this.handleResponse<ClinicalSession>(response);
  }

  async stopSession(sessionId: string): Promise<ClinicalSession> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/stop`, {
      method: "POST",
      headers: this.authHeaders(),
    });
    return this.handleResponse<ClinicalSession>(response);
  }

  async syncSessionTranscript(
    sessionId: string,
    transcriptText: string,
    detectedLanguage?: string,
  ): Promise<ClinicalSocketUpdate> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/transcript`, {
      method: "POST",
      headers: this.jsonHeaders(),
      body: JSON.stringify({
        transcript_text: transcriptText,
        detected_language: detectedLanguage,
      }),
    });
    const update = await this.handleResponse<Omit<ClinicalSocketUpdate, "type">>(response);
    return { type: "update", ...update };
  }

  async uploadSessionAudio(
    sessionId: string,
    audioBlob: Blob,
    filename: string,
    languageHint?: string,
  ): Promise<ClinicalSocketUpdate> {
    const formData = new FormData();
    formData.append("audio_file", audioBlob, filename);
    if (languageHint) {
      formData.append("language_hint", languageHint);
    }

    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/audio`, {
      method: "POST",
      headers: this.authHeaders(),
      body: formData,
    });
    const update = await this.handleResponse<Omit<ClinicalSocketUpdate, "type">>(response);
    return { type: "update", ...update };
  }

  async getRecords(patientId: string): Promise<RecordItem[]> {
    const response = await fetch(`${API_BASE_URL}/records/patient/${patientId}`, {
      headers: this.authHeaders(),
    });
    return this.handleResponse<RecordItem[]>(response);
  }

  async getPatientHistory(patientId: string): Promise<PatientHistory> {
    const response = await fetch(`${API_BASE_URL}/records/patient/${patientId}/history`, {
      headers: this.authHeaders(),
    });
    return this.handleResponse<PatientHistory>(response);
  }

  async downloadPatientHistory(patientId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/records/patient/${patientId}/history/download`, {
      headers: this.authHeaders(),
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || "Download failed");
    }
    return response.blob();
  }

  async downloadVisitReport(recordId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/records/${recordId}/report/pdf`, {
      headers: this.authHeaders(),
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || "Report download failed");
    }
    return response.blob();
  }

  async queryRag(patientId: string, question: string): Promise<RagAnswer> {
    const response = await fetch(`${API_BASE_URL}/rag/query`, {
      method: "POST",
      headers: this.jsonHeaders(),
      body: JSON.stringify({ patient_id: patientId, question }),
    });
    return this.handleResponse<RagAnswer>(response);
  }

  async getPatientPortalDashboard(): Promise<PatientPortalDashboard> {
    const response = await fetch(`${API_BASE_URL}/records/portal/me/reports`, {
      headers: this.authHeaders(),
    });
    return this.handleResponse<PatientPortalDashboard>(response);
  }

  async downloadPatientPortalReport(recordId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/records/portal/reports/${recordId}/pdf`, {
      headers: this.authHeaders(),
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || "Report download failed");
    }
    return response.blob();
  }

  private authHeaders(): HeadersInit {
    return {
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
    };
  }

  private jsonHeaders(): HeadersInit {
    return {
      ...this.authHeaders(),
      "Content-Type": "application/json",
    };
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || "Request failed");
    }
    return response.json() as Promise<T>;
  }
}

export const apiClient = new ApiClient();
