'use client';
import { useState, useRef, useCallback } from 'react';
import { useSessionStore } from '@/lib/store';

export default function Composer() {
  const [text, setText] = useState('');
  const [listening, setListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  const isThinking = useSessionStore((state) => state.isThinking);
  const sendMessage = useSessionStore((state) => state.sendMessage);
  const sessionId = useSessionStore((state) => state.sessionId);
  const addMessage = useSessionStore((state) => state.addMessage);
  const phase = useSessionStore((state) => state.phase);

  const toggleSTT = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert('Speech recognition is not supported in this browser. Try Chrome or Edge.'); return; }

    if (listening && recognitionRef.current) {
      const rec = recognitionRef.current;
      recognitionRef.current = null;  // clear first so onend doesn't restart
      rec.stop();
      setListening(false);
      return;
    }

    const rec = new SR();
    rec.lang = 'en-US';
    rec.continuous = true;
    rec.interimResults = false;

    rec.onresult = (e: any) => {
      const results = Array.from(e.results) as any[];
      const transcript = results
        .slice(e.resultIndex)
        .filter((r: any) => r.isFinal)
        .map((r: any) => r[0].transcript)
        .join(' ')
        .trim();
      if (transcript) setText(prev => prev ? prev + ' ' + transcript : transcript);
    };
    // Some browsers stop on silence even with continuous=true — restart automatically
    rec.onend = () => {
      if (recognitionRef.current === rec) {
        try { rec.start(); } catch { setListening(false); recognitionRef.current = null; }
      }
    };
    rec.onerror = (e: any) => {
      if (e.error !== 'no-speech') { setListening(false); recognitionRef.current = null; }
    };

    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  }, [listening]);

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const handleSend = async () => {
    if (!text.trim() || isThinking) return;
    const msg = text;
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }
    await sendMessage(msg);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !sessionId) return;

    // Show loading state
    const setIsThinking = useSessionStore.setState;
    setIsThinking({ isThinking: true, avatarState: 'thinking' });

    try {
      // Add user message
      addMessage({ role: 'user', content: '[Uploaded an anatomy image]' });

      // Upload the image
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`/api/sessions/${sessionId}/image`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Image upload failed');
      }

      const data = await res.json();

      // Add bot message with socratic question
      addMessage({
        role: 'bot',
        content: data.socratic_question,
        avatarState: 'asking',
      });

      setIsThinking({ isThinking: false, avatarState: 'idle' });
    } catch (err) {
      console.error('Image upload error:', err);
      addMessage({
        role: 'bot',
        content: '⚠️ Failed to process the image. Please try again.',
        avatarState: 'error',
      });
      setIsThinking({ isThinking: false, avatarState: 'error' });
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="composer">
      <div className="composer-inner">
        <div className="composer-box">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              handleInput();
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type your reasoning… UnMask reads your thinking, not just your answer."
          />
          <div className="composer-row">
            <div className="composer-tools">
              <button
                className="icon-btn"
                title={listening ? 'Stop listening' : 'Speak your answer'}
                onClick={toggleSTT}
                disabled={isThinking}
                style={listening ? { color: 'var(--accent)', animation: 'pulse 1s infinite' } : {}}
              >
                {listening ? (
                  <svg viewBox="0 0 24 24" fill="currentColor" stroke="none">
                    <circle cx="12" cy="12" r="8" opacity="0.2"/>
                    <circle cx="12" cy="12" r="4"/>
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <rect x="9" y="2" width="6" height="12" rx="3"/>
                    <path d="M19 10a7 7 0 0 1-14 0"/>
                    <line x1="12" y1="19" x2="12" y2="22"/>
                    <line x1="8" y1="22" x2="16" y2="22"/>
                  </svg>
                )}
              </button>
              <button
                className="icon-btn"
                title="Attach image"
                onClick={() => fileInputRef.current?.click()}
                disabled={isThinking}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M21 12.5l-8 8a5.5 5.5 0 0 1-7.8-7.8l8.5-8.5a3.7 3.7 0 0 1 5.2 5.2l-8.5 8.5a1.8 1.8 0 0 1-2.6-2.6l7.6-7.6"/>
                </svg>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                style={{ display: 'none' }}
              />
            </div>
            {phase !== 'wrapup' && (
              <button
                className="icon-btn"
                title="End session"
                onClick={() => sendMessage('end session')}
                disabled={isThinking}
                style={{ color: 'var(--ink-3)', fontSize: '12px', padding: '0 10px', height: '32px', borderRadius: 'var(--r)', border: '1px solid var(--rule)' }}
              >
                End
              </button>
            )}
            <button
              className="composer-send"
              onClick={handleSend}
              disabled={!text.trim() || isThinking}
            >
              Send →
            </button>
          </div>
        </div>
      </div>
      <div className="composer-foot">
        UnMask uses retrieval-grounded answers · check important info before clinical use
      </div>
    </div>
  );
}
