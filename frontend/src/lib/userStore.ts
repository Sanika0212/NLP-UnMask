'use client';

const PREFIX = 'unmask_user_';

export interface SavedMessage {
  role: 'user' | 'bot';
  content: string;
  author?: string;
}

export interface LastSession {
  topic: string;
  date: string;
  messages: SavedMessage[];
}

interface UserData {
  mastery: Record<string, number>;
  cardRatings: Record<string, Record<number, 'known' | 'review'>>;
  quizScores: Record<string, number[]>;
  weakTopics: string[];
  misconceptions: { topic: string; note: string; turn: number }[];
  lastSession: LastSession | null;
}

function key(name: string) {
  return PREFIX + name.toLowerCase().trim();
}

export function loadUser(name: string): UserData {
  if (typeof window === 'undefined') return empty();
  try {
    const raw = localStorage.getItem(key(name));
    if (!raw) return empty();
    return { ...empty(), ...JSON.parse(raw) };
  } catch {
    return empty();
  }
}

export function saveUser(name: string, patch: Partial<UserData>) {
  if (typeof window === 'undefined') return;
  const current = loadUser(name);
  localStorage.setItem(key(name), JSON.stringify({ ...current, ...patch }));
}

export function saveMastery(name: string, mastery: Record<string, number>) {
  if (!name || name === 'Student') return;
  const current = loadUser(name);
  // Merge — only update keys that improved
  const merged = { ...current.mastery };
  for (const [k, v] of Object.entries(mastery)) {
    if (v > (merged[k] ?? 0)) merged[k] = v;
  }
  saveUser(name, { mastery: merged });
}

export function saveCardRating(name: string, topic: string, cardIdx: number, rating: 'known' | 'review') {
  const current = loadUser(name);
  const topicRatings = { ...(current.cardRatings[topic] ?? {}) };
  topicRatings[cardIdx] = rating;
  saveUser(name, { cardRatings: { ...current.cardRatings, [topic]: topicRatings } });
}

export function saveQuizScore(name: string, topic: string, score: number, total: number) {
  const current = loadUser(name);
  const scores = [...(current.quizScores[topic] ?? []), Math.round((score / total) * 100)];
  saveUser(name, { quizScores: { ...current.quizScores, [topic]: scores } });
}

export function saveSessionContext(
  name: string,
  weakTopics: string[],
  misconceptions: { topic: string; note: string; turn: number }[],
) {
  if (!name || name === 'Student') return;
  saveUser(name, { weakTopics, misconceptions });
}

export function saveLastSession(name: string, topic: string, messages: SavedMessage[]) {
  if (!name || name === 'Student') return;
  const relevant = messages
    .filter(m => !('supervisorStep' in m) && m.content?.trim())
    .map(m => ({ role: m.role, content: m.content, author: m.author }));
  saveUser(name, {
    lastSession: {
      topic,
      date: new Date().toISOString(),
      messages: relevant.slice(-60),
    },
  });
}

function empty(): UserData {
  return { mastery: {}, cardRatings: {}, quizScores: {}, weakTopics: [], misconceptions: [], lastSession: null };
}
