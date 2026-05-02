'use client';
import { useEffect, useRef, useId } from 'react';
import { AvatarState } from '@/lib/types';

interface Props {
  state?: AvatarState;
  size?: number;
  className?: string;
}

export default function Avatar({ state = 'idle', size = 32, className = '' }: Props) {
  const avatarRef = useRef<HTMLDivElement>(null);
  const pupilRef = useRef<SVGCircleElement>(null);
  const uid = useId().replace(/:/g, '');

  useEffect(() => {
    // Smooth lerp tracking — pupil lags behind mouse naturally
    let raf: number;
    let targetX = 32, targetY = 34;
    let currentX = 32, currentY = 34;
    // Micro-saccade offset — random tiny drift applied on top
    let microX = 0, microY = 0;
    let microTimer: ReturnType<typeof setTimeout>;

    const scheduleMicro = () => {
      microTimer = setTimeout(() => {
        // Small random glance offset (±0.4 SVG units)
        microX = (Math.random() - 0.5) * 0.8;
        microY = (Math.random() - 0.5) * 0.8;
        scheduleMicro();
      }, 1800 + Math.random() * 2400);
    };
    scheduleMicro();

    const handleMouseMove = (e: MouseEvent) => {
      if (!avatarRef.current) return;
      const rect = avatarRef.current.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height * 0.53125; // pupil at 34/64

      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);

      const pxPerSvg = rect.width / 64;
      const maxPx = 2.2 * pxPerSvg;
      const scale = dist > maxPx ? maxPx / dist : 1;

      targetX = 32 + (dx * scale) / pxPerSvg;
      targetY = 34 + (dy * scale) / pxPerSvg;
    };

    const tick = () => {
      // Ease toward target + micro offset (lazy ~6% per frame)
      const easedX = targetX + microX;
      const easedY = targetY + microY;
      currentX += (easedX - currentX) * 0.06;
      currentY += (easedY - currentY) * 0.06;

      if (pupilRef.current) {
        pupilRef.current.setAttribute('cx', currentX.toFixed(3));
        pupilRef.current.setAttribute('cy', currentY.toFixed(3));
      }
      raf = requestAnimationFrame(tick);
    };

    window.addEventListener('mousemove', handleMouseMove);
    raf = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(raf);
      clearTimeout(microTimer);
    };
  }, []);

  const clipId = `um-iris-clip-${uid}`;

  return (
    <div
      ref={avatarRef}
      className={`unmask-avatar state-${state} ${className}`}
      style={{ fontSize: size }}
    >
      <svg
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        strokeLinecap="round"
        strokeLinejoin="round"
        role="img"
        aria-label="UnMask"
      >
        <defs>
          <clipPath id={clipId}>
            <circle cx="32" cy="34" r="9" />
          </clipPath>
        </defs>

        {/* Outer ring */}
        <circle data-part="ring" cx="32" cy="32" r="26" />

        {/* Veil — arched brow / eyelid */}
        <path data-part="veil" d="M10 28 Q32 16 54 28" />

        {/* Iris */}
        <circle data-part="iris" cx="32" cy="34" r="9" />

        {/* Orbit dots — hidden normally, spin during thinking */}
        <g data-part="orbit">
          <circle cx="32" cy="26" r="2" fill="var(--um-accent)" stroke="none" />
          <circle cx="38.9" cy="37" r="2" fill="var(--um-accent)" stroke="none" />
          <circle cx="25.1" cy="37" r="2" fill="var(--um-accent)" stroke="none" />
        </g>

        {/* Pupil — mouse-tracked via JS */}
        <g clipPath={`url(#${clipId})`}>
          <circle ref={pupilRef} data-part="pupil" cx="32" cy="34" r="3" />
        </g>

        {/* Specular highlight */}
        <path d="M28 31.5 l1.6 -1.6" strokeWidth="1.6" stroke="currentColor" fill="none" />
      </svg>
    </div>
  );
}
