'use client';
import { create } from 'zustand';
import { SessionStore, Message, AvatarState, Phase, LearningMode } from './types';

const AGENT_AVATAR: Record<string, AvatarState> = {
  diagnostic: 'asking',
  tutor: 'speaking',
  assessment: 'assess',
  wrapup: 'idle',
};

const initialState = {
  sessionId: null,
  phase: 'rapport' as Phase,
  messages: [] as Message[],
  mastery: {} as Record<string, number>,
  currentTopic: null,
  diagnosticComplete: false,
  consecutiveIncorrect: 0,
  weakTopics: [] as string[],
  misconceptions: [],
  avatarState: 'idle' as AvatarState,
  isThinking: false,
  studyFocus: null,
  learningMode: null as LearningMode | null,
  diagTotal: 2,
  setupDone: false,
  pcrMode: 'prerequisite_first' as const,
  studentName: 'Student',
};

export const useSessionStore = create<SessionStore>((set, get) => ({
  ...initialState,

  reset: () => set(initialState),

  setAvatarState: (s) => set({ avatarState: s }),

  setStudentName: (name) => set({ studentName: name }),

  addMessage: (msg) => {
    const full: Message = {
      ...msg,
      id: crypto.randomUUID(),
      timestamp: new Date(),
    };
    set((state) => ({ messages: [...state.messages, full] }));
  },

  updateLastBotMessage: (patch) => {
    set((state) => {
      const msgs = [...state.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'bot') {
          msgs[i] = { ...msgs[i], ...patch };
          break;
        }
      }
      return { messages: msgs };
    });
  },

  createSession: async () => {
    const res = await fetch('/api/sessions', { method: 'POST' });
    const data = await res.json();
    set({ sessionId: data.session_id });
  },

  setupSession: async (topic, mode) => {
    const { sessionId } = get();
    if (!sessionId) throw new Error('No session');
    const res = await fetch(`/api/sessions/${sessionId}/setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, mode }),
    });
    const data = await res.json();
    set({
      studyFocus: topic,
      learningMode: mode,
      diagTotal: data.diag_total ?? 2,
      setupDone: true,
    });
    return { firstQuestion: data.first_question ?? '', diagTotal: data.diag_total ?? 2 };
  },

  sendMessage: async (content) => {
    const { sessionId } = get();
    if (!sessionId) return;

    get().addMessage({ role: 'user', content });
    set({ isThinking: true, avatarState: 'thinking' });

    try {
      const resp = await fetch(`/api/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });

      if (!resp.body) throw new Error('No response body');
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? '';

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data:')) continue;
          const raw = line.slice(5).trim();
          if (!raw || raw === '[DONE]') continue;
          let evt: Record<string, unknown>;
          try { evt = JSON.parse(raw); } catch { continue; }

          const type = evt.type as string;

          if (type === 'thinking') {
            set({ avatarState: 'thinking' });

          } else if (type === 'supervisor') {
            get().addMessage({
              role: 'bot',
              content: '',
              supervisorStep: {
                agent: evt.agent as string,
                reasoning: evt.reasoning as string,
                phase: evt.phase as string,
              },
              avatarState: 'thinking',
            });

          } else if (type === 'state_update') {
            const su = evt as Record<string, unknown>;
            const newMisconceptions = Array.isArray(su.mistake_log)
              ? (su.mistake_log as Array<{topic:string;misconception:string;turn:number}>).map(m => ({
                  topic: m.topic,
                  note: m.misconception,
                  turn: m.turn,
                }))
              : get().misconceptions;
            set({
              phase: (su.phase as Phase) ?? get().phase,
              mastery: (su.mastery as Record<string, number>) ?? get().mastery,
              diagnosticComplete: (su.diagnostic_complete as boolean) ?? false,
              consecutiveIncorrect: (su.consecutive_incorrect as number) ?? 0,
              currentTopic: (su.current_topic as string | null) ?? null,
              weakTopics: (su.weak_topics as string[]) ?? [],
              misconceptions: newMisconceptions,
            });

          } else if (type === 'message') {
            const agent = evt.agent as string ?? '';
            const av: AvatarState = AGENT_AVATAR[agent] ?? 'speaking';
            get().addMessage({
              role: 'bot',
              content: evt.content as string,
              author: evt.author as string,
              avatarState: av,
            });
            set({ isThinking: false, avatarState: av });

          } else if (type === 'visual_hint') {
            get().updateLastBotMessage({
              visualHint: {
                concept: evt.concept as string,
                imageUrl: evt.image_url as string | undefined,
                caption: evt.caption as string | undefined,
                hintText: (evt.study_notes || evt.hint_text) as string | undefined,
              },
            });

          } else if (type === 'done') {
            set({ isThinking: false, avatarState: 'idle' });

          } else if (type === 'error') {
            const msg = (evt.message as string) ?? 'Something went wrong.';
            get().addMessage({ role: 'bot', content: `⚠️ ${msg}`, avatarState: 'error' });
            set({ isThinking: false, avatarState: 'error' });
          }
        }
      }
    } catch (err) {
      console.error('SSE error', err);
      set({ isThinking: false, avatarState: 'error' });
    }
  },
}));
