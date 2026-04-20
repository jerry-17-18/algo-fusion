export type User = {
  id: string;
  full_name: string;
  role: string;
  username?: string | null;
  external_id?: string | null;
  age?: number | null;
  gender?: string | null;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Patient = {
  id: string;
  external_id: string;
  full_name: string;
  age: number | null;
  gender: string | null;
  preferred_language: string | null;
  created_at: string;
};

export type PatientCreateInput = {
  external_id?: string;
  full_name: string;
  age?: number;
  gender?: string;
  preferred_language?: string;
};

export type ClinicalSession = {
  id: string;
  patient_id: string;
  doctor_id: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  transcript_text: string;
  detected_languages: string[];
};

export type StructuredClinicalData = {
  symptoms: string[];
  duration: string;
  diagnosis: string;
  medications: string[];
};

export type DoctorAssist = {
  suggested_diagnosis: string;
  missing_fields: string[];
  red_flags: string[];
};

export type RecordItem = {
  id: string;
  patient_id: string;
  session_id: string;
  raw_transcript: string;
  structured_data: StructuredClinicalData;
  suggested_diagnosis: string | null;
  missing_fields: string[];
  rag_summary: string | null;
  created_at: string;
  updated_at: string | null;
};

export type PatientHistoryRecord = {
  id: string;
  session_id: string;
  created_at: string;
  raw_transcript: string;
  structured_data: StructuredClinicalData;
  suggested_diagnosis: string | null;
  missing_fields: string[];
};

export type PatientHistory = {
  patient_id: string;
  records: PatientHistoryRecord[];
};

export type PatientPortalProfile = {
  id: string;
  external_id: string;
  full_name: string;
  age: number | null;
  gender: string | null;
};

export type VisitReportSummary = {
  id: string;
  session_id: string;
  created_at: string;
  structured_data: StructuredClinicalData;
  suggested_diagnosis: string | null;
};

export type PatientPortalDashboard = {
  patient: PatientPortalProfile;
  reports: VisitReportSummary[];
};

export type RagCitation = {
  record_id: string;
  session_id: string;
  excerpt: string;
  score: number;
};

export type RagAnswer = {
  answer: string;
  citations: RagCitation[];
};

export type ClinicalSocketUpdate = {
  type: "update";
  session_id: string;
  transcript_chunk: string;
  full_transcript: string;
  detected_languages: string[];
  structured_data: StructuredClinicalData;
  doctor_assist: DoctorAssist;
};
