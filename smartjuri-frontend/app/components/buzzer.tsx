import React from "react";
import { Radio, Lock } from "lucide-react";
import { Badge } from "@/components/ui/badge";

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
    <div className="flex flex-col items-center justify-center bg-card border rounded-3xl p-8 shadow-sm relative overflow-hidden">
      {/* Badge Status di Atas Tombol */}
      <div className="mb-6 z-10">
        {isLockedOut ? (
          <Badge variant="destructive" className="uppercase tracking-wider gap-1">
            <Lock className="w-3 h-3" /> Jawaban Salah
          </Badge>
        ) : isActive ? (
          <Badge className={`${colorScheme.badgeBg} ${colorScheme.badgeText} border-0 uppercase tracking-wider animate-pulse`}>
            Ayo Jawab!
          </Badge>
        ) : isDisabled ? (
          <Badge variant="secondary" className="uppercase tracking-wider gap-1 text-muted-foreground">
            <Lock className="w-3 h-3" /> Terkunci
          </Badge>
        ) : (
          <Badge variant="outline" className={`${colorScheme.badgeText} uppercase tracking-wider gap-1.5`}>
            <span className={`w-2 h-2 rounded-full ${colorScheme.text} bg-current animate-ping`} />
            Tekan!
          </Badge>
        )}
      </div>

      {/* Tombol Bulat Buzzer Utama */}
      <button
        disabled={isDisabled || isLockedOut}
        onClick={onClick}
        className={`w-40 h-40 rounded-full border-4 flex flex-col items-center justify-center gap-2 transition-all duration-300 relative select-none cursor-pointer outline-none ${
          isActive
            ? `${colorScheme.bg} ${colorScheme.border} ${colorScheme.glow} scale-105 active:scale-100 text-white`
            : isLockedOut
            ? "bg-destructive/10 border-destructive/20 text-destructive/50 opacity-60 shadow-inner"
            : "bg-muted border-border text-muted-foreground hover:border-foreground/20 hover:scale-102 active:scale-98 shadow-md"
        }`}
        style={{
          boxShadow: isActive
            ? `0 0 40px var(--tw-shadow-color, rgba(0,0,0,0.2)), inset 0 -8px 0 rgba(0,0,0,0.25), inset 0 8px 0 rgba(255,255,255,0.15)`
            : isDisabled
            ? "none"
            : "inset 0 -6px 0 rgba(0,0,0,0.08), inset 0 3px 0 rgba(255,255,255,0.4)",
        }}
      >
        {/* Lapisan Mengkilap (Glossy Effect) */}
        {!isDisabled && !isLockedOut && (
          <div className="absolute top-0 left-0 w-full h-1/2 bg-white/10 rounded-t-full pointer-events-none" />
        )}

        <Radio className={`w-10 h-10 transition-transform ${isActive ? "animate-bounce" : ""}`} />
        <span className="text-2xl font-black tracking-wider">BUZZ</span>
      </button>

      {/* Identitas Nama Regu Kontestan */}
      <div className="mt-5 font-black text-2xl tracking-wide text-foreground uppercase z-10">
        {namaTim}
      </div>
    </div>
  );
}