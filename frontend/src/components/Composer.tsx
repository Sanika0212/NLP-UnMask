'use client';
import { useState, useRef } from 'react';
import { useSessionStore } from '@/lib/store';

export default function Composer() {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isThinking = useSessionStore((state) => state.isThinking);
  const sendMessage = useSessionStore((state) => state.sendMessage);
  const sessionId = useSessionStore((state) => state.sessionId);
  const addMessage = useSessionStore((state) => state.addMessage);

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
