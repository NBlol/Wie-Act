// Typed client for the EdNova AI REST API (docs/API.md).

export const TOKEN_KEY = 'ednova_token';
export const LOGOUT_EVENT = 'ednova:logout';

export type Language = 'en' | 'fr' | 'ar' | 'tn';
export type LearningStyle = 'visual' | 'analogy' | 'step_by_step' | 'examples' | 'repetition' | 'problem_solving';
export type Level = 'beginner' | 'intermediate' | 'advanced';
export type Role = 'learner' | 'teacher';
export type Tier = 'compact' | 'large' | 'none';

export const LEARNING_STYLES: LearningStyle[] = ['visual', 'analogy', 'step_by_step', 'examples', 'repetition', 'problem_solving'];
export const LEVELS: Level[] = ['beginner', 'intermediate', 'advanced'];
export const LANGUAGES: Language[] = ['en', 'fr', 'ar', 'tn'];

export interface AiMeta {
  tier: Tier;
  model: string;
  provider: 'live' | 'offline';
  cached: boolean;
  fallback: boolean;
  fallback_reason: null | 'large_unavailable' | 'rate_limited' | 'provider_error' | 'no_api_key';
  latency_ms: number;
  notice: string | null;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  preferred_language: Language;
  darija_script: 'arabic' | 'latin';
  learning_style: LearningStyle | null;
  level: Level | null;
  diagnostic_completed: boolean;
  xp: number;
  level_number: number;
  streak_days: number;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface HealthResponse {
  status: string;
  version: string;
  db: string;
}

export interface SystemStatus {
  provider_mode: 'live' | 'offline';
  compact_model: string;
  large_model: string;
  large_available: boolean;
  large_breaker_open_until: string | null;
  queue_depth: number;
  queue_capacity: number;
  stats: {
    calls_total: number;
    calls_compact: number;
    calls_large: number;
    calls_offline: number;
    cache_hits: number;
    fallbacks: number;
    errors: number;
    avg_latency_ms_compact: number;
    avg_latency_ms_large: number;
  };
}

export interface RoutingEntry {
  task: string;
  tier: Tier;
  rationale: string;
}

export interface DiagnosticOption {
  id: string;
  text: string;
  style?: LearningStyle;
}

export interface DiagnosticQuestion {
  id: string;
  kind: 'preference' | 'exercise';
  text: string;
  options: DiagnosticOption[];
  correct_option_id?: string;
  difficulty?: Level;
}

export interface DiagnosticProfile {
  learning_style: LearningStyle;
  secondary_style: LearningStyle | null;
  level: Level;
  style_scores: Record<string, number>;
  exercise_score: number;
  exercise_total: number;
}

export interface DiagnosticResult {
  profile: DiagnosticProfile;
  recommendations: string[];
  explanation: string;
  ai: AiMeta;
  user: User;
}

export interface Conversation {
  id: string;
  title: string;
  language: Language;
  document_id: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Source {
  chunk_id: string;
  document_id?: string;
  page: number | null;
  excerpt: string;
  score?: number;
}

export interface Triage {
  intent: 'explain' | 'exercise_help' | 'answer_request' | 'quiz_request' | 'chit_chat' | 'other';
  confusion: 'none' | 'mild' | 'high';
  complexity: 'low' | 'high';
  language: string;
}

export interface MessageMeta {
  ai?: AiMeta;
  triage?: Triage;
  hint_level?: number;
  sources?: Source[];
  next_step?: string | null;
  guiding_question?: string | null;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  meta: MessageMeta;
}

export interface SendMessageResponse {
  user_message: Message;
  assistant_message: Message;
  stages: string[];
}

export interface Stage {
  key: string;
  label_key: string;
  typical_ms: number;
}

export interface QuizOption {
  id: string;
  text: string;
}

export interface QuizQuestion {
  id: string;
  type: 'mcq' | 'short';
  text: string;
  options?: QuizOption[];
  skill: string;
}

export interface Quiz {
  id: string;
  topic: string;
  language: Language;
  difficulty: string;
  created_at: string;
  source: 'topic' | 'document';
  document_id: string | null;
  questions: QuizQuestion[];
  ai?: AiMeta;
}

export interface QuizSummary {
  id: string;
  topic: string;
  language: Language;
  difficulty: string;
  num_questions: number;
  created_at: string;
  best_score: number | null;
  attempts: number;
}

export type QuizAnswer = { question_id: string; option_id: string } | { question_id: string; text: string };

export interface QuizResultItem {
  question_id: string;
  correct: boolean;
  score: number;
  your_answer: string;
  correct_answer: string;
  explanation: string;
  skill: string;
}

export interface QuizSubmitResponse {
  attempt_id: string;
  score: number;
  total: number;
  percent: number;
  results: QuizResultItem[];
  feedback: string;
  xp_gained: number;
  badges_unlocked: string[];
  ai: AiMeta;
}

export interface RoomSummary {
  id: string;
  code: string;
  name: string;
  topic: string;
  language: Language;
  member_count: number;
  created_at: string;
  is_owner: boolean;
}

export interface RoomMember {
  user_id: string;
  display_name: string;
  joined_at: string;
  message_count: number;
}

export interface Participation {
  balance_score: number;
  dominant_member: string | null;
  quiet_members: string[];
  total_messages: number;
}

export interface Room {
  id: string;
  code: string;
  name: string;
  topic: string;
  language: Language;
  owner_id: string;
  created_at: string;
  members: RoomMember[];
  participation: Participation;
  quiz_id: string | null;
}

export interface RoomMessage {
  id: string;
  room_id: string;
  user_id: string | null;
  display_name: string;
  role: 'member' | 'moderator';
  content: string;
  created_at: string;
  meta: { ai?: AiMeta; action?: string; [k: string]: unknown };
}

export interface RoomMessagesResponse {
  messages: RoomMessage[];
  participation: Participation;
}

export interface LeaderboardEntry {
  display_name: string;
  percent: number;
  submitted_at: string;
}

export interface Document {
  id: string;
  title: string;
  filename: string;
  mime: string;
  pages: number;
  chunk_count: number;
  chars: number;
  language: string | null;
  created_at: string;
  status: 'ready' | 'failed';
  error: string | null;
  preview?: string;
}

export interface SearchResult {
  chunk_id: string;
  page: number | null;
  score: number;
  excerpt: string;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
  ai: AiMeta;
}

export interface Activity {
  id: string;
  text: string;
  kind: 'read' | 'practice' | 'quiz' | 'discuss' | 'watch' | 'recall';
  done: boolean;
}

export interface Milestone {
  id: string;
  week: number;
  title: string;
  objective: string;
  activities: Activity[];
  checkpoint: string;
}

export interface Roadmap {
  id: string;
  goal: string;
  weeks: number;
  language: Language;
  created_at: string;
  progress_percent: number;
  milestones: Milestone[];
  ai?: AiMeta;
}

export interface Flashcard {
  q: string;
  a: string;
}

export interface Note {
  id: string;
  title: string;
  source: 'conversation' | 'document' | 'room' | 'topic';
  source_id: string | null;
  language: Language;
  content_md: string;
  flashcards: Flashcard[];
  created_at: string;
  ai?: AiMeta;
}

export interface Skill {
  skill: string;
  mastery_percent: number;
  attempts: number;
  trend: 'up' | 'flat' | 'down';
}

export interface Badge {
  id: string;
  name_key: string;
  unlocked_at: string | null;
}

export interface AnalyticsOverview {
  xp: number;
  level_number: number;
  level_progress_percent: number;
  streak_days: number;
  totals: {
    questions_asked: number;
    quizzes_taken: number;
    avg_score_percent: number;
    documents: number;
    rooms: number;
    notes: number;
    study_minutes: number;
  };
  skills: Skill[];
  activity_last_14_days: { date: string; questions: number; quiz_points: number; minutes: number }[];
  confusion_events: { date: string; topic: string; level: 'mild' | 'high' }[];
  learning_style: LearningStyle | null;
  style_scores: Record<string, number>;
  badges: Badge[];
  next_step: { text: string; text_key?: string; action: 'tutor' | 'quiz' | 'roadmap' | 'room' | 'document' | 'onboarding'; target_id: string | null };
  ai_efficiency: {
    calls_compact: number;
    calls_large: number;
    calls_offline: number;
    cache_hits: number;
    fallbacks: number;
    large_share_percent: number;
  };
}

export interface ActivityEvent {
  id: string;
  type: string;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface ClassRoom {
  id: string;
  code: string;
  name: string;
  created_at?: string;
  member_count?: number;
}

export interface ClassDashboard {
  members: number;
  avg_score_percent: number;
  quizzes_taken: number;
  style_distribution: Record<string, number>;
  weak_skills: { skill: string; mastery_percent: number }[];
  confusion_hotspots: { topic: string; count: number }[];
  participation_balance_avg: number;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

/** Human-readable message from an unknown error. */
export function errorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (err instanceof ApiError) {
    if (typeof err.detail === 'string') return err.detail;
    if (Array.isArray(err.detail)) {
      return err.detail
        .map((d) => (typeof d === 'object' && d && 'msg' in d ? String((d as { msg: unknown }).msg) : JSON.stringify(d)))
        .join('; ');
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

const BASE = '/api';

async function request<T>(method: string, path: string, body?: unknown, opts: { auth?: boolean; raw?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
  const token = getToken();
  if (opts.auth !== false && token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    });
  } catch (e) {
    throw new ApiError(0, 'Cannot reach the EdNova server. Check that the backend is running.');
  }

  if (res.status === 401 && opts.auth !== false) {
    setToken(null);
    window.dispatchEvent(new CustomEvent(LOGOUT_EVENT));
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? (data as { detail: unknown }).detail : data || res.statusText;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const api = {
  // system
  health: () => request<HealthResponse>('GET', '/health', undefined, { auth: false }),
  systemStatus: () => request<SystemStatus>('GET', '/system/status', undefined, { auth: false }),
  routingTable: () => request<{ tasks: RoutingEntry[] }>('GET', '/system/routing', undefined, { auth: false }),

  // auth
  register: (body: { email: string; password: string; display_name: string; preferred_language: Language; role: Role }) =>
    request<AuthResponse>('POST', '/auth/register', body, { auth: false }),
  login: (body: { email: string; password: string }) => request<AuthResponse>('POST', '/auth/login', body, { auth: false }),
  me: () => request<User>('GET', '/auth/me'),
  updateMe: (body: Partial<Pick<User, 'display_name' | 'preferred_language' | 'learning_style' | 'level' | 'darija_script'>>) =>
    request<User>('PATCH', '/auth/me', body),
  deleteMe: () => request<void>('DELETE', '/auth/me'),

  // diagnostic
  diagnosticQuestions: (language: Language) => request<{ questions: DiagnosticQuestion[] }>('GET', `/diagnostic/questions?language=${language}`),
  diagnosticSubmit: (body: { answers: { question_id: string; option_id: string }[]; self_reported_level: Level | null; goal: string }) =>
    request<DiagnosticResult>('POST', '/diagnostic/submit', body),

  // tutor
  conversations: () => request<Conversation[]>('GET', '/tutor/conversations'),
  createConversation: (body: { title?: string; language: Language; document_id: string | null }) =>
    request<Conversation>('POST', '/tutor/conversations', body),
  conversation: (id: string) => request<{ conversation: Conversation; messages: Message[] }>('GET', `/tutor/conversations/${id}`),
  deleteConversation: (id: string) => request<void>('DELETE', `/tutor/conversations/${id}`),
  sendMessage: (id: string, body: { content: string; mode: 'guided' | 'direct'; use_documents: boolean; style_override: LearningStyle | null }) =>
    request<SendMessageResponse>('POST', `/tutor/conversations/${id}/messages`, body),
  revealAnswer: (id: string) => request<SendMessageResponse>('POST', `/tutor/conversations/${id}/reveal`, {}),
  stages: () => request<{ stages: Stage[] }>('GET', '/tutor/stages'),

  // quizzes
  generateQuiz: (body: {
    topic: string;
    document_id: string | null;
    num_questions: number;
    difficulty: Level | 'auto';
    language: Language;
    question_types: ('mcq' | 'short')[];
    room_id: string | null;
  }) => request<Quiz>('POST', '/quizzes/generate', body),
  quizzes: () => request<QuizSummary[]>('GET', '/quizzes'),
  quiz: (id: string) => request<Quiz>('GET', `/quizzes/${id}`),
  submitQuiz: (id: string, body: { answers: QuizAnswer[]; time_spent_s: number }) =>
    request<QuizSubmitResponse>('POST', `/quizzes/${id}/submit`, body),

  // rooms
  rooms: () => request<RoomSummary[]>('GET', '/rooms'),
  createRoom: (body: { name: string; topic: string; language: Language }) => request<Room>('POST', '/rooms', body),
  joinRoom: (code: string) => request<Room>('POST', '/rooms/join', { code }),
  room: (id: string) => request<Room>('GET', `/rooms/${id}`),
  roomMessages: (id: string, after: string, limit = 50) =>
    request<RoomMessagesResponse>('GET', `/rooms/${id}/messages?after=${encodeURIComponent(after)}&limit=${limit}`),
  sendRoomMessage: (id: string, content: string) =>
    request<{ message: RoomMessage; moderator_message: RoomMessage | null }>('POST', `/rooms/${id}/messages`, { content }),
  moderate: (id: string, action: 'nudge' | 'check_explanation' | 'summarize' | 'guiding_question', message_id: string | null) =>
    request<{ moderator_message: RoomMessage; ai: AiMeta }>('POST', `/rooms/${id}/moderate`, { action, message_id }),
  roomQuiz: (id: string, num_questions: number) => request<Quiz>('POST', `/rooms/${id}/quiz`, { num_questions }),
  leaderboard: (id: string) => request<LeaderboardEntry[]>('GET', `/rooms/${id}/leaderboard`),

  // documents
  uploadDocument: (file: File, title?: string, language?: Language) => {
    const form = new FormData();
    form.append('file', file);
    if (title) form.append('title', title);
    if (language) form.append('language', language);
    return request<Document>('POST', '/documents', form);
  },
  documents: () => request<Document[]>('GET', '/documents'),
  document: (id: string) => request<Document>('GET', `/documents/${id}`),
  deleteDocument: (id: string) => request<void>('DELETE', `/documents/${id}`),
  searchDocument: (id: string, query: string, k = 5) => request<{ results: SearchResult[] }>('POST', `/documents/${id}/search`, { query, k }),
  askDocument: (id: string, question: string, language: Language) =>
    request<AskResponse>('POST', `/documents/${id}/ask`, { question, language }),

  // roadmaps
  createRoadmap: (body: { goal: string; weeks: number; hours_per_week: number; language: Language; document_id: string | null }) =>
    request<Roadmap>('POST', '/roadmaps', body),
  roadmaps: () => request<Roadmap[]>('GET', '/roadmaps'),
  roadmap: (id: string) => request<Roadmap>('GET', `/roadmaps/${id}`),
  toggleActivity: (id: string, activityId: string, done: boolean) =>
    request<Roadmap>('PATCH', `/roadmaps/${id}/activities/${activityId}`, { done }),

  // notes
  generateNote: (body: {
    source: 'conversation' | 'document' | 'room' | 'topic';
    source_id: string | null;
    topic: string | null;
    language: Language;
    format: 'summary' | 'flashcards' | 'both';
  }) => request<Note>('POST', '/notes/generate', body),
  notes: () => request<Note[]>('GET', '/notes'),
  note: (id: string) => request<Note>('GET', `/notes/${id}`),
  deleteNote: (id: string) => request<void>('DELETE', `/notes/${id}`),

  // analytics
  analytics: () => request<AnalyticsOverview>('GET', '/analytics/overview'),
  events: (limit = 50) => request<ActivityEvent[]>('GET', `/analytics/events?limit=${limit}`),

  // teacher / classes
  createClass: (name: string) => request<ClassRoom>('POST', '/classes', { name }),
  classes: () => request<ClassRoom[]>('GET', '/classes'),
  joinClass: (code: string) => request<{ joined: boolean }>('POST', '/classes/join', { code }),
  classDashboard: (id: string) => request<ClassDashboard>('GET', `/classes/${id}/dashboard`),
};
