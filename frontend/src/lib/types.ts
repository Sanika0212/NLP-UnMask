export type AvatarState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'asking' | 'reveal' | 'assess' | 'celebrate' | 'error';
export type Phase = 'rapport' | 'tutoring' | 'assessment' | 'wrapup';
export type LearningMode = 'visual' | 'text';
export type PCRMode = 'context_only' | 'prerequisite_first' | 'full_reveal';

export interface YouTubeResource {
  concept: string;
  title: string;
  creator: string;
  search_query: string;
  description: string;
}

export interface VisualHint {
  concept: string;
  imageUrl?: string;   // full URL: /static/anatomy/x.html or https://... (web fallback)
  caption?: string;
  hintText?: string;
}

export interface SupervisorStep {
  agent: string;
  reasoning: string;
  phase?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  author?: string;
  avatarState?: AvatarState;
  visualHint?: VisualHint;
  supervisorStep?: SupervisorStep;
  isThinking?: boolean;
  timestamp: Date;
  _streaming?: boolean;
  quickReplies?: string[];
}

export interface Misconception {
  topic: string;
  note: string;
  turn: number;
}

export interface SessionState {
  sessionId: string | null;
  phase: Phase;
  messages: Message[];
  mastery: Record<string, number>;
  currentTopic: string | null;
  diagnosticComplete: boolean;
  consecutiveIncorrect: number;
  weakTopics: string[];
  misconceptions: Misconception[];
  avatarState: AvatarState;
  isThinking: boolean;
  studyFocus: string | null;
  learningMode: LearningMode | null;
  diagTotal: number;
  setupDone: boolean;
  pcrMode: PCRMode;
  studentName: string;
  participantId: string;
  participantRole: string;
  preQuizAnswers: number[];
  preQuizScore: number;
  youtubeResources: YouTubeResource[];
  composerDraft: string;
}

export interface SessionStore extends SessionState {
  createSession: () => Promise<void>;
  setupSession: (topic: string, mode: LearningMode) => Promise<{ firstQuestion: string; welcomeMessage: string; diagTotal: number }>;
  sendMessage: (content: string) => Promise<void>;
  setAvatarState: (s: AvatarState) => void;
  addMessage: (msg: Omit<Message, 'id' | 'timestamp'>) => void;
  updateLastBotMessage: (patch: Partial<Message>) => void;
  setStudentName: (name: string) => void;
  setParticipantInfo: (id: string, role: string) => void;
  setPreQuizResults: (answers: number[], score: number) => void;
  reset: () => void;
  setComposerDraft: (text: string) => void;
}
