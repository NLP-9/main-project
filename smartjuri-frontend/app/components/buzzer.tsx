import React from "react";
import { Radio, Lock } from "lucide-react";

interface BuzzerProps {
  namaTim: string;
  isActive: boolean;
  isDisabled: boolean;
  isLockedOut: boolean;
  onClick: () => void;
  colorScheme: {
    bg: string;
    border: string;
    glow: string;
    text: string;
    badgeBg: string;
    badgeText: string;
  };
}

export default function Buzzer({
  namaTim,
  isActive,
  isDisabled,
  isLockedOut,
  onClick,
  colorScheme,
}: BuzzerProps) {
  return (
    <div className="flex flex-col items-center justify-center bg-slate-900/40 border border-slate-800 p-8 rounded-3xl backdrop-blur-xs shadow-xl relative overflow-hidden">
      
      {/* Badge Status di Atas Tombol */}
      <div className="mb-6 z-10">
        {isLockedOut ? (
          <span className="bg-red-500/10 text-red-400 border border-red-500/25 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
            ❌ Jawaban Salah
          </span>
        ) : isActive ? (
          <span className="bg-amber-500/10 text-amber-400 border border-amber-500/25 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider animate-pulse">
            AYO JAWAB!
          </span>
        ) : isDisabled ? (
          <span className="bg-slate-950 text-slate-600 border border-slate-800 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
            <Lock className="w-3 h-3" /> Terkunci
          </span>
        ) : (
          <span className={`${colorScheme.badgeBg} ${colorScheme.badgeText} border border-current/10 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5`}>
            <span className={`w-2 h-2 rounded-full ${colorScheme.text} bg-current animate-ping`} />
            Tekan!
          </span>
        )}
      </div>

      {/* Tombol Bulat Buzzer Utama */}
      <button
        disabled={isDisabled || isLockedOut}
        onClick={onClick}
        className={`w-40 h-40 rounded-full border-4 flex flex-col items-center justify-center gap-2 transition-all duration-300 relative select-none cursor-pointer outline-none ${
          isActive
            ? `${colorScheme.bg} ${colorScheme.border} ${colorScheme.glow} scale-105 active:scale-100`
            : isLockedOut
            ? 'bg-red-950/20 border-red-900/30 text-red-800 opacity-40 shadow-inner'
            : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:scale-102 active:scale-98 shadow-2xl'
        }`}
        style={{
          boxShadow: isActive 
            ? `0 0 40px ${colorScheme.text}40, inset 0 -8px 0 rgba(0,0,0,0.4), inset 0 8px 0 rgba(255,255,255,0.2)` 
            : isDisabled 
            ? 'none' 
            : 'inset 0 -8px 0 rgba(0,0,0,0.5), inset 0 4px 0 rgba(255,255,255,0.05)'
        }}
      >
        {/* Lapisan Mengkilap (Glossy Effect) */}
        {!isDisabled && !isLockedOut && (
          <div className="absolute top-0 left-0 w-full h-1/2 bg-white/5 rounded-t-full pointer-events-none" />
        )}

        <Radio className={`w-10 h-10 transition-transform ${isActive ? 'animate-bounce text-white' : ''}`} />
        <span className={`text-2xl font-black tracking-wider ${isActive ? 'text-white' : 'text-slate-200'}`}>
          BUZZ
        </span>
      </button>

      {/* Identitas Nama Regu Kontestan */}
      <div className="mt-5 font-black text-2xl tracking-wide text-slate-300 uppercase z-10">
        {namaTim}
      </div>
    </div>
  );
}