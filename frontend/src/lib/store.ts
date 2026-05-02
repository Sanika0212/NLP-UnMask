'use client';
import { create } from 'zustand';
import { SessionStore, Message, AvatarState, Phase, LearningMode } from './types';
import { saveMastery, loadUser } from './userStore';

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
  participantId: '',
  participantRole: '',
  preQuizAnswers: [] as number[],
  preQuizScore: 0,
};

export const useSessionStore = create<SessionStore>((set, get) => ({
  ...initialState,

  reset: () => set(initialState),

  setAvatarState: (s) => set({ avatarState: s }),

  setStudentName: (name) => {
    const userData = loadUser(name);
    set({ studentName: name, mastery: Object.keys(userData.mastery).length > 0 ? userData.mastery : get().mastery });
  },

  setParticipantInfo: (id, role) => set({ participantId: id, participantRole: role }),

  setPreQuizResults: (answers, score) => set({ preQuizAnswers: answers, preQuizScore: score }),

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
    return {
      firstQuestion: data.first_question ?? '',
      welcomeMessage: data.welcome_message ?? '',
      diagTotal: data.diag_total ?? 2,
    };
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
            const newMastery = (su.mastery as Record<string, number>) ?? get().mastery;
            saveMastery(get().studentName, newMastery);
            const newPhase = (su.phase as Phase) ?? get().phase;
            const pcrMap: Record<string, string> = {
              rapport: 'diagnostic',
              tutoring: 'prerequisite_first',
              assessment: 'assessment',
              wrapup: 'complete',
            };
            set({
              phase: newPhase,
              pcrMode: (pcrMap[newPhase] ?? get().pcrMode) as typeof initialState.pcrMode,
              mastery: newMastery,
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

          } else if (type === 'phase_change') {
            const newPhase = evt.to as string;
            const pcrMap: Record<string, string> = {
              rapport: 'diagnostic', tutoring: 'prerequisite_first',
              assessment: 'assessment', wrapup: 'complete',
            };
            set({ phase: newPhase as Phase, pcrMode: (pcrMap[newPhase] ?? get().pcrMode) as typeof initialState.pcrMode });
            if (evt.banner) {
              get().addMessage({ role: 'bot', content: evt.banner as string, avatarState: 'speaking' });
            }
            set({ isThinking: true, avatarState: 'thinking' });

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
            if (msg === 'Session not found') {
              // Backend restarted — silently recreate session and retry
              set({ isThinking: true, avatarState: 'thinking' });
              try {
                const { studyFocus, learningMode } = get();
                const topic = (studyFocus ?? '').replace('topic:', '') || 'brachial_plexus';
                const mode = learningMode ?? 'text';
                await get().createSession();
                await get().setupSession(topic, mode);
                // Retry the message with the new session
                const newSessionId = get().sessionId!;
                const retryResp = await fetch(`/api/sessions/${newSessionId}/messages`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ content }),
                });
                // Drain the retry stream (best-effort)
                if (retryResp.body) {
                  const retryReader = retryResp.body.getReader();
                  const retryDec = new TextDecoder();
                  let retryBuf = '';
                  while (true) {
                    const { done: rd, value: rv } = await retryReader.read();
                    if (rd) break;
                    retryBuf += retryDec.decode(rv, { stream: true });
                    const rparts = retryBuf.split('\n\n');
                    retryBuf = rparts.pop() ?? '';
                    for (const rp of rparts) {
                      const rline = rp.trim();
                      if (!rline.startsWith('data:')) continue;
                      const rraw = rline.slice(5).trim();
                      if (!rraw || rraw === '[DONE]') continue;
                      let revt: Record<string, unknown>;
                      try { revt = JSON.parse(rraw); } catch { continue; }
                      if (revt.type === 'message') {
                        const av: AvatarState = AGENT_AVATAR[(revt.agent as string) ?? ''] ?? 'speaking';
                        get().addMessage({ role: 'bot', content: revt.content as string, author: revt.author as string, avatarState: av });
                        set({ isThinking: false, avatarState: av });
                      } else if (revt.type === 'done') {
                        set({ isThinking: false, avatarState: 'idle' });
                      }
                    }
                  }
                }
              } catch {
                get().addMessage({ role: 'bot', content: '⚠️ Session lost. Please refresh the page to continue.', avatarState: 'error' });
                set({ isThinking: false, avatarState: 'error' });
              }
              return;
            }
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
