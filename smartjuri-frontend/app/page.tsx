"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Shield,
  Crown,
  RefreshCw,
  Clock,
  Clipboard,
  Mic,
  MicOff,
  BookOpen,
  ArrowRight,
  Sparkles,
} from "lucide-react";

interface Kontestan {
  id: number;
  nama: string;
  skorAkumulasi: number;
}

interface EvaluationResult {
  kunci_jawaban: string;
  sumber_dokumen: string;
  skor: number;
  alasan: string;
  raw_context: string;
}

interface TeamTheme {
  emblem: string;
  color: string;
  glow: string;
}

const TEAM_THEMES: { [key: number]: TeamTheme } = {
  1: { emblem: "🦅", color: "#F94144", glow: "#F9414466" },
  2: { emblem: "🌿", color: "#43AA8B", glow: "#43AA8B66" },
  3: { emblem: "⚡", color: "#F9C74F", glow: "#F9C74F66" },
  4: { emblem: "🔥", color: "#F8961E", glow: "#F8961E66" },
  5: { emblem: "🛡️", color: "#577590", glow: "#57759066" },
  6: { emblem: "⚔️", color: "#F3722C", glow: "#F3722C66" },
};

function themeFor(id: number): TeamTheme {
  return TEAM_THEMES[id] || TEAM_THEMES[1];
}

function scoreColor10(skor: number) {
  if (skor >= 7.5) return "#90BE6D";
  if (skor >= 5) return "#F9C74F";
  return "#F94144";
}

function gradeEmoji10(skor: number) {
  if (skor >= 9) return "🏆";
  if (skor >= 7.5) return "🎖️";
  if (skor >= 5) return "⚡";
  if (skor >= 2.5) return "🛡️";
  return "💔";
}

function FlameBar() {
  return (
    <div className="flex justify-center gap-3 py-1 select-none">
      {["🔥", "🗡️", "🔥", "⚔️", "🔥", "🗡️", "🔥"].map((s, i) => (
        <span key={i} className="text-sm opacity-50">
          {s}
        </span>
      ))}
    </div>
  );
}

function GoldDivider() {
  return (
    <div className="flex items-center gap-3 my-1">
      <div className="flex-1 h-px bg-gradient-to-r from-transparent to-[#F9C74F]/30" />
      <span className="text-[#F9C74F]/50 text-xs">⚜</span>
      <div className="flex-1 h-px bg-gradient-to-l from-transparent to-[#F9C74F]/30" />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Buzzer — gaya visual dari kode kanan, props/perilaku dari kode kiri
// ─────────────────────────────────────────────────────────────────────────────

interface BuzzerProps {
  namaTim: string;
  isActive: boolean;
  isDisabled: boolean;
  isLockedOut: boolean;
  onClick: () => void;
  colorScheme: TeamTheme;
}

function Buzzer({ namaTim, isActive, isDisabled, isLockedOut, onClick, colorScheme }: BuzzerProps) {
  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      className="relative flex flex-col items-center justify-center py-8 px-4 rounded-2xl font-bold text-white transition-all duration-200 hover:scale-105 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 select-none"
      style={{
        background: isActive
          ? `radial-gradient(circle at 50% 30%, ${colorScheme.color}dd, ${colorScheme.color}88)`
          : `radial-gradient(circle at 50% 30%, ${colorScheme.color}55, ${colorScheme.color}22)`,
        border: `2px solid ${isActive ? colorScheme.color : colorScheme.color + "55"}`,
        boxShadow: isActive
          ? `0 0 40px ${colorScheme.glow}, 0 0 80px ${colorScheme.glow}, inset 0 1px 0 ${colorScheme.color}88`
          : `0 4px 20px rgba(0,0,0,0.5), inset 0 1px 0 ${colorScheme.color}33`,
      }}
    >
      {isActive && (
        <span
          className="absolute inset-0 rounded-2xl animate-ping"
          style={{ border: `2px solid ${colorScheme.color}`, opacity: 0.4 }}
        />
      )}

      <div className="text-5xl mb-3 drop-shadow-lg">{colorScheme.emblem}</div>
      <div
        className="text-xl font-bold tracking-widest text-center mb-2 leading-tight"
        style={{ fontFamily: "'', serif", color: isActive ? "#fff" : colorScheme.color }}
      >
        {namaTim}
      </div>

      {isLockedOut ? (
        <div className="px-3 py-0.5 rounded-full text-[10px] font-bold mt-1 bg-black/40 text-white/40 tracking-widest">
          TERKUNCI
        </div>
      ) : (
        <div
          className="mt-1 text-[15px] tracking-[0.25em] opacity-70 font-bold"
          style={{ fontFamily: "'', serif", color: isActive ? "#fff" : colorScheme.color }}
        >
          TEKAN!
        </div>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Komponen Utama — state & logika 100% dari kode kiri
// ─────────────────────────────────────────────────────────────────────────────

export default function LCCDashboard() {
  const [jumlahPeserta, setJumlahPeserta] = useState<number>(3);
  const [kontestans, setKontestans] = useState<Kontestan[]>([
    { id: 1, nama: "Tim A", skorAkumulasi: 0 },
    { id: 2, nama: "Tim B", skorAkumulasi: 0 },
    { id: 3, nama: "Tim C", skorAkumulasi: 0 },
  ]);

  const [gameStarted, setGameStarted] = useState<boolean>(false);
  const [pertanyaan, setPertanyaan] = useState<string>("");
  const [buzzerWinner, setBuzzerWinner] = useState<number | null>(null);
  const [jawabanInput, setJawabanInput] = useState<string>("");
  const [lockedOutUsers, setLockedOutUsers] = useState<number[]>([]);

  const [secondsLeft, setSecondsLeft] = useState<number>(45);
  const [isTimerActive, setIsTimerActive] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(false);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);

  // Voice to Text States
  const [isListeningPertanyaan, setIsListeningPertanyaan] = useState<boolean>(false);
  const [isListeningJawaban, setIsListeningJawaban] = useState<boolean>(false);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    audioRef.current = new Audio("/bzzz.mp3");

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.lang = "id-ID";
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      recognitionRef.current = rec;
    }
  }, []);

  useEffect(() => {
    if (isTimerActive && secondsLeft > 0) {
      timerRef.current = setInterval(() => {
        setSecondsLeft((prev) => prev - 1);
      }, 1000);
    } else if (secondsLeft === 0) {
      if (timerRef.current) clearInterval(timerRef.current);
      handleTimeOut();
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isTimerActive, secondsLeft]);

  const handleTimeOut = () => {
    setIsTimerActive(false);
    if (buzzerWinner !== null) {
      setLockedOutUsers((prev) => [...prev, buzzerWinner]);
      setBuzzerWinner(null);
      setJawabanInput("");
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleSetupGame = () => {
    const list: Kontestan[] = [];
    for (let i = 1; i <= jumlahPeserta; i++) {
      list.push({ id: i, nama: `Tim ${String.fromCharCode(64 + i)}`, skorAkumulasi: 0 });
    }
    setKontestans(list);
    setGameStarted(true);
  };

  const handleBuzzerClick = (id: number) => {
    if (buzzerWinner === null && !lockedOutUsers.includes(id)) {
      if (audioRef.current) {
        audioRef.current.currentTime = 0;
        audioRef.current.play().catch(() => {});
      }
      setBuzzerWinner(id);
      setSecondsLeft(45);
      setIsTimerActive(true);
    }
  };

  const handlePastePertanyaan = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setPertanyaan(text);
    } catch (err) {
      alert("Gagal mengakses clipboard! Pastikan izin browser sudah aktif.");
    }
  };

  const toggleVoicePertanyaan = () => {
    if (!recognitionRef.current) {
      alert("Browser kamu tidak mendukung fitur Speech Recognition.");
      return;
    }
    if (isListeningPertanyaan) {
      recognitionRef.current.stop();
      setIsListeningPertanyaan(false);
    } else {
      setIsListeningPertanyaan(true);
      recognitionRef.current.onresult = (event: any) => {
        const speechToText = event.results[0][0].transcript;
        setPertanyaan(speechToText);
        setIsListeningPertanyaan(false);
      };
      recognitionRef.current.onerror = () => setIsListeningPertanyaan(false);
      recognitionRef.current.onend = () => setIsListeningPertanyaan(false);
      recognitionRef.current.start();
    }
  };

  const toggleVoiceJawaban = () => {
    if (!recognitionRef.current) {
      alert("Browser kamu tidak mendukung fitur Speech Recognition.");
      return;
    }
    if (isListeningJawaban) {
      recognitionRef.current.stop();
      setIsListeningJawaban(false);
    } else {
      setIsListeningJawaban(true);
      recognitionRef.current.onresult = (event: any) => {
        const speechToText = event.results[0][0].transcript;
        setJawabanInput(speechToText);
        setIsListeningJawaban(false);
      };
      recognitionRef.current.onerror = () => setIsListeningJawaban(false);
      recognitionRef.current.onend = () => setIsListeningJawaban(false);
      recognitionRef.current.start();
    }
  };

  const handleProsesPenilaian = async () => {
    if (!buzzerWinner || !jawabanInput.trim()) return;
    setIsTimerActive(false);
    setLoading(true);
    setEvaluation(null);

    const activeTeam = kontestans.find((k) => k.id === buzzerWinner);

    try {
      const res = await fetch("http://localhost:8000/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pertanyaan: pertanyaan,
          nama_kontestan: activeTeam?.nama || "Kontestan",
          jawaban_kontestan: jawabanInput,
        }),
      });

      const data: EvaluationResult = await res.json();
      setEvaluation(data);

      if (data.skor > 0) {
        setKontestans((prev) =>
          prev.map((k) =>
            k.id === buzzerWinner ? { ...k, skorAkumulasi: k.skorAkumulasi + data.skor } : k
          )
        );
      } else {
        setLockedOutUsers((prev) => [...prev, buzzerWinner]);
        setBuzzerWinner(null);
        setJawabanInput("");
      }
    } catch (err) {
      alert("Gagal menghubungi server Python Backend!");
      setIsTimerActive(true);
    } finally {
      setLoading(false);
    }
  };

  const resetRound = () => {
    setBuzzerWinner(null);
    setJawabanInput("");
    setEvaluation(null);
    setLockedOutUsers([]);
    setPertanyaan("");
    setSecondsLeft(45);
    setIsTimerActive(false);
  };

  const activeTeamTheme = buzzerWinner ? themeFor(buzzerWinner) : null;
  const timerUrgent = secondsLeft < 15;

  // ── Layar Setup (belum mulai) ─────────────────────────────────────────────
  if (!gameStarted) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden"
        style={{ background: "#0a0400", fontFamily: "'Nunito', sans-serif" }}
      >
        {/* <FontImports /> */}
        <div className="fixed inset-0 z-0 pointer-events-none">
          <img
            src="https://images.unsplash.com/photo-1552432552-06c0b0a94dda?w=1920&h=1080&fit=crop&auto=format"
            alt="Roman Colosseum Arena"
            className="w-full h-full object-cover"
            style={{ opacity: 0.14 }}
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse at 50% 0%, #2d0800cc 0%, #0a040099 50%, #000000ee 100%)",
            }}
          />
        </div>

        <div
          className="relative z-10 max-w-md w-full rounded-2xl border-2 p-8 text-center"
          style={{
            borderColor: "rgba(249,199,79,0.25)",
            background: "linear-gradient(180deg, #1c0900 0%, #0f0500 100%)",
            boxShadow: "0 0 60px rgba(249,199,79,0.08), inset 0 1px 0 rgba(249,199,79,0.15)",
          }}
        >
          <FlameBar />
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full my-4 bg-gradient-to-br from-[#F94144] to-[#F3722C] shadow-lg shadow-[#F9414444]">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1
            className="text-2xl font-black tracking-widest text-[#F9C74F]"
            style={{ fontFamily: "' Decorative', serif" }}
          >
            ScoreHub
          </h1>
          <p className="text-[#F8961E]/60 text-xs tracking-wide mt-3 mb-6 leading-relaxed">
            Konfigurasi jumlah kontestan untuk memulai kompetisi cerdas cermat otomatis.
          </p>

          <div className="text-left space-y-2 mb-6">
            <label
              className="text-[10px] font-bold tracking-widest text-[#F9C74F]/50"
              style={{ fontFamily: "'', serif" }}
            >
              JUMLAH KONTESTAN REGU
            </label>
            <input
              type="number"
              min={2}
              max={6}
              value={jumlahPeserta}
              onChange={(e) => setJumlahPeserta(Number(e.target.value))}
              className="w-full px-4 py-3 rounded-xl border text-[#F9C74F] text-lg font-bold outline-none"
              style={{ background: "#100600", borderColor: "rgba(249,199,79,0.3)" }}
            />
          </div>

          <button
            onClick={handleSetupGame}
            className="w-full py-4 rounded-xl font-black text-white tracking-widest transition-all hover:scale-[1.02] active:scale-[0.98]"
            style={{
              fontFamily: "'', serif",
              background: "linear-gradient(135deg, #F94144, #F3722C)",
              boxShadow: "0 0 32px #F9414444",
            }}
          >
            MASUK ARENA LOMBA
          </button>
          <FlameBar />
        </div>
      </div>
    );
  }

  // ── Dashboard Utama ─────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen text-[#F9C74F] flex flex-col md:flex-row relative overflow-x-hidden"
      style={{ fontFamily: "'Nunito', sans-serif", background: "#0a0400" }}
    >
      {/* <FontImports /> */}

      {/* Background */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <img
          src="https://images.unsplash.com/photo-1552432552-06c0b0a94dda?w=1920&h=1080&fit=crop&auto=format"
          alt="Roman Colosseum Arena"
          className="w-full h-full object-cover"
          style={{ opacity: 0.1 }}
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 50% 0%, #2d0800cc 0%, #0a040099 50%, #000000ee 100%)",
          }}
        />
        <div className="absolute inset-0" style={{ boxShadow: "inset 0 0 120px rgba(0,0,0,0.8)" }} />
      </div>

      {/* SIDEBAR */}
      <aside
        className="relative z-10 w-full md:w-80 border-r p-6 flex flex-col justify-between"
        style={{ borderColor: "rgba(249,199,79,0.12)", background: "rgba(5,2,0,0.75)" }}
      >
        <div className="space-y-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#F94144] to-[#F3722C] flex items-center justify-center shadow-lg shadow-[#F9414444]">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <span
                className="font-black text-lg tracking-widest text-[#F9C74F] block leading-none"
                style={{ fontFamily: "' Decorative', serif" }}
              >
                ScoreHub
              </span>
              <span className="text-[8px] tracking-[0.3em] text-[#F8961E]/60 font-semibold">
                ARENA EDITION
              </span>
            </div>
          </div>

          <div className="space-y-3">
            <div
              className="text-[10px] font-bold text-[#F9C74F]/40 uppercase tracking-widest"
              style={{ fontFamily: "'', serif" }}
            >
              System Status
            </div>
            <div
              className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm border"
              style={{ borderColor: "rgba(67,170,139,0.3)", background: "rgba(67,170,139,0.06)", color: "#90BE6D" }}
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#90BE6D] opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#90BE6D]" />
              </span>
              Core Engine API Connected
            </div>
          </div>

          <div
            className="rounded-2xl border p-4"
            style={{ borderColor: "rgba(249,199,79,0.12)", background: "rgba(249,199,79,0.03)" }}
          >
            <div className="flex items-center gap-2 mb-1">
              <Crown className="text-[#F9C74F] w-4 h-4" />
              <span
                className="text-sm font-bold text-[#F9C74F]"
                style={{ fontFamily: "'', serif" }}
              >
                Leaderboard
              </span>
            </div>
            <p className="text-[10px] text-[#F9C74F]/40 mb-4">Papan skor kontestan</p>

            <div className="space-y-2">
              {kontestans
                .slice()
                .sort((a, b) => b.skorAkumulasi - a.skorAkumulasi)
                .map((k, idx) => {
                  const theme = themeFor(k.id);
                  return (
                    <div
                      key={k.id}
                      className="flex items-center justify-between rounded-xl border px-3 py-2"
                      style={{ borderColor: `${theme.color}30`, background: `${theme.color}0d` }}
                    >
                      <div className="flex items-center gap-2">
                        {idx === 0 && k.skorAkumulasi > 0 && (
                          <Crown className="w-3 h-3 text-[#F9C74F]" />
                        )}
                        <span className="text-base">{theme.emblem}</span>
                        <span
                          className="text-sm font-bold"
                          style={{ fontFamily: "'', serif", color: theme.color }}
                        >
                          {k.nama}
                        </span>
                      </div>
                      <span
                        className="font-mono font-black text-sm px-2 py-0.5 rounded-full"
                        style={{ background: `${theme.color}22`, color: theme.color }}
                      >
                        {k.skorAkumulasi}
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>

        <button
          onClick={() => setGameStarted(false)}
          className="flex items-center gap-2 text-[#F9C74F]/40 hover:text-[#F94144] transition-colors text-sm mt-6"
        >
          <RefreshCw className="w-4 h-4" /> Reset Konfigurasi Awal
        </button>
      </aside>

      {/* MAIN */}
      <main className="relative z-10 flex-1 p-6 lg:p-10 space-y-6 max-w-5xl mx-auto w-full">
        {/* Header + timer */}
        <div
          className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 pb-6 border-b"
          style={{ borderColor: "rgba(249,199,79,0.12)" }}
        >
          <div>
            <h1
              className="text-2xl font-black tracking-wide text-[#F9C74F]"
              style={{ fontFamily: "' Decorative', serif" }}
            >
              Arena Contest
            </h1>
            <p className="text-sm text-[#F9C74F]/40 mt-1">
              Masukkan detail kompetisi dan jawaban tim untuk analisis semantik.
            </p>
          </div>

          <div
            className="flex items-center gap-3 rounded-xl border px-4 py-2.5"
            style={{ borderColor: "rgba(249,199,79,0.15)", background: "rgba(249,199,79,0.03)" }}
          >
            <span
              className="text-[10px] font-bold text-[#F9C74F]/40 uppercase tracking-widest"
              style={{ fontFamily: "'', serif" }}
            >
              Babak Penyisihan
            </span>
            <span
              className="flex items-center gap-1.5 font-mono text-sm px-3 py-1 rounded-full border font-bold"
              style={{
                borderColor: isTimerActive ? "#F9C74F" : "rgba(249,199,79,0.2)",
                color: isTimerActive ? "#F9C74F" : "rgba(249,199,79,0.5)",
                background: isTimerActive ? "rgba(249,199,79,0.1)" : "transparent",
              }}
            >
              <Clock className={`w-3.5 h-3.5 ${isTimerActive ? "animate-pulse" : ""}`} />
              {formatTime(secondsLeft)}
            </span>
          </div>
        </div>

        {/* Input Soal */}
        <div
          className="rounded-2xl border p-6"
          style={{
            borderColor: "rgba(249,199,79,0.15)",
            background: "linear-gradient(180deg, #1c0900 0%, #0f0500 100%)",
          }}
        >
          <div className="flex flex-row items-center justify-between mb-4">
            <span
              className="text-xs uppercase tracking-widest text-[#F9C74F]/50 font-bold"
              style={{ fontFamily: "'', serif" }}
            >
              Input Soal Disini
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={toggleVoicePertanyaan}
                disabled={evaluation !== null || buzzerWinner !== null}
                className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                style={{
                  fontFamily: "'', serif",
                  borderColor: isListeningPertanyaan ? "#F94144" : "rgba(249,199,79,0.25)",
                  color: isListeningPertanyaan ? "#F94144" : "#F9C74F",
                  background: isListeningPertanyaan ? "rgba(249,65,68,0.1)" : "transparent",
                }}
              >
                {isListeningPertanyaan ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                {isListeningPertanyaan ? "Mendengarkan..." : "Voice Input"}
              </button>
              <button
                onClick={handlePastePertanyaan}
                disabled={evaluation !== null || buzzerWinner !== null}
                className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                style={{ fontFamily: "'', serif", borderColor: "rgba(249,199,79,0.25)", color: "#F9C74F" }}
              >
                <Clipboard className="w-3.5 h-3.5" /> Paste Soal
              </button>
            </div>
          </div>

          <textarea
            rows={3}
            value={pertanyaan}
            onChange={(e) => setPertanyaan(e.target.value)}
            disabled={evaluation !== null || buzzerWinner !== null}
            placeholder={
              isListeningPertanyaan
                ? "Silakan bicara sekarang, juri..."
                : "Tuliskan atau paste pertanyaan kompetisi hukum/kewarganegaraan di sini..."
            }
            className="w-full p-4 rounded-xl border resize-none text-lg outline-none transition-colors disabled:opacity-60"
            style={{ background: "#100600", borderColor: "rgba(249,199,79,0.2)", color: "#F9C74F" }}
          />
          <div className="flex flex-row gap-2 mt-4">
            {["MPR RI", "Pancasila", "UUD 1945"].map((tag) => (
              <span
                key={tag}
                className="text-[10px] font-bold px-2.5 py-1 rounded-full border tracking-wide"
                style={{ borderColor: "rgba(249,199,79,0.25)", color: "rgba(249,199,79,0.6)" }}
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Buzzer grid */}
        {pertanyaan && !evaluation && (
          <div
            className="rounded-2xl border p-6"
            style={{ borderColor: "rgba(249,199,79,0.12)", background: "rgba(249,199,79,0.02)" }}
          >
            <p
              className="text-xs uppercase tracking-widest text-[#F9C74F]/50 font-bold mb-5"
              style={{ fontFamily: "'', serif" }}
            >
              Contestant Submissions (Buzzer)
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {kontestans.map((k) => {
                const isWinner = buzzerWinner === k.id;
                const isDisabled = (buzzerWinner !== null && !isWinner) || lockedOutUsers.includes(k.id);
                const isLockedOut = lockedOutUsers.includes(k.id);

                return (
                  <Buzzer
                    key={k.id}
                    namaTim={k.nama}
                    isActive={isWinner}
                    isDisabled={isDisabled}
                    isLockedOut={isLockedOut}
                    onClick={() => handleBuzzerClick(k.id)}
                    colorScheme={themeFor(k.id)}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Panel jawaban */}
        {buzzerWinner !== null && !evaluation && activeTeamTheme && (
          <div
            className="rounded-2xl border-2 p-6"
            style={{
              borderColor: `${activeTeamTheme.color}55`,
              background: `linear-gradient(180deg, ${activeTeamTheme.color}14 0%, #0f0500 70%)`,
            }}
          >
            <div className="flex flex-row items-center justify-between mb-4">
              <span
                className="text-xs uppercase tracking-widest font-bold flex items-center gap-2"
                style={{ fontFamily: "'', serif", color: activeTeamTheme.color }}
              >
                <span className="text-lg">{activeTeamTheme.emblem}</span>
                Input Jawaban: {kontestans.find((k) => k.id === buzzerWinner)?.nama}
              </span>
              <span
                className="text-2xl font-black"
                style={{
                  fontFamily: "'', serif",
                  color: timerUrgent ? "#F94144" : activeTeamTheme.color,
                }}
              >
                {formatTime(secondsLeft)}
              </span>
            </div>

            {/* Progress bar waktu */}
            <div className="h-2 rounded-full bg-[#F9C74F]/10 overflow-hidden mb-4">
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{
                  width: `${(secondsLeft / 45) * 100}%`,
                  background: timerUrgent
                    ? "linear-gradient(90deg, #F94144, #F3722C)"
                    : `linear-gradient(90deg, ${activeTeamTheme.color}, ${activeTeamTheme.color}aa)`,
                }}
              />
            </div>

            <div className="relative flex items-center mb-4">
              <input
                autoFocus
                value={jawabanInput}
                onChange={(e) => setJawabanInput(e.target.value)}
                placeholder={
                  isListeningJawaban
                    ? "Silakan bicara, tim tercepat..."
                    : `Ketik transkrip jawaban lisan dari ${
                        kontestans.find((k) => k.id === buzzerWinner)?.nama
                      }...`
                }
                className="w-full pr-14 h-12 px-4 rounded-xl border text-base outline-none"
                style={{ background: "#100600", borderColor: `${activeTeamTheme.color}40`, color: "#F9C74F" }}
              />
              <button
                type="button"
                onClick={toggleVoiceJawaban}
                className="absolute right-1.5 h-9 w-9 rounded-lg flex items-center justify-center transition-all"
                style={{
                  background: isListeningJawaban ? "#F94144" : `${activeTeamTheme.color}33`,
                  color: isListeningJawaban ? "#fff" : activeTeamTheme.color,
                }}
              >
                {isListeningJawaban ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
            </div>

            <button
              onClick={handleProsesPenilaian}
              disabled={loading || !jawabanInput.trim() || isListeningJawaban}
              className="w-full py-4 rounded-xl font-black text-white tracking-widest flex items-center justify-center gap-2 transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
              style={{
                fontFamily: "'', serif",
                background: `linear-gradient(135deg, ${activeTeamTheme.color}, ${activeTeamTheme.color}99)`,
                boxShadow: `0 0 32px ${activeTeamTheme.glow}`,
              }}
            >
              {loading ? (
                <RefreshCw className="animate-spin w-4 h-4" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {loading ? "MENGEVALUASI..." : "MULAI EVALUASI SEMANTIK"}
            </button>
          </div>
        )}

        {/* Hasil evaluasi */}
        {evaluation && (
          <div className="space-y-6">
            <div
              className="relative rounded-2xl border-2 overflow-hidden p-8"
              style={{
                borderColor: scoreColor10(evaluation.skor),
                background: `linear-gradient(180deg, ${scoreColor10(evaluation.skor)}18 0%, #0f0500 65%)`,
                boxShadow: `0 0 60px ${scoreColor10(evaluation.skor)}22`,
              }}
            >
              <div
                className="absolute top-0 left-0 w-32 h-32 rounded-full opacity-20 blur-3xl pointer-events-none"
                style={{ background: scoreColor10(evaluation.skor) }}
              />
              <div
                className="absolute bottom-0 right-0 w-32 h-32 rounded-full opacity-20 blur-3xl pointer-events-none"
                style={{ background: scoreColor10(evaluation.skor) }}
              />

              <div className="relative flex items-start justify-between mb-6">
                <div>
                  <h2
                    className="text-xl font-black text-[#F9C74F]"
                    style={{ fontFamily: "' Decorative', serif" }}
                  >
                    Hasil Evaluasi Juri AI
                  </h2>
                  <p className="text-xs text-[#F9C74F]/40 mt-1">
                    Status: Keputusan bersifat mutlak berdasarkan dokumen negara resmi.
                  </p>
                </div>
                <div className="text-center">
                  <div className="text-3xl mb-1">{gradeEmoji10(evaluation.skor)}</div>
                  <div
                    className="text-4xl font-black tabular-nums leading-none"
                    style={{ color: scoreColor10(evaluation.skor), fontFamily: "' Decorative', serif" }}
                  >
                    {evaluation.skor}
                    <span className="text-lg text-[#F9C74F]/30">/10</span>
                  </div>
                </div>
              </div>

              <div className="relative grid grid-cols-1 md:grid-cols-2 gap-4">
                <div
                  className="rounded-xl border p-5"
                  style={{ borderColor: "rgba(249,199,79,0.12)", background: "rgba(0,0,0,0.35)" }}
                >
                  <div
                    className="text-[10px] font-bold uppercase tracking-widest mb-3"
                    style={{ color: "#F9C74F", fontFamily: "'', serif" }}
                  >
                    Kunci Jawaban Resmi
                  </div>
                  <p className="text-sm leading-relaxed text-[#F9C74F]/80">{evaluation.kunci_jawaban}</p>
                  <span
                    className="inline-flex items-center gap-1.5 mt-4 text-[10px] font-bold px-2.5 py-1 rounded-full border"
                    style={{ borderColor: "rgba(249,199,79,0.25)", color: "rgba(249,199,79,0.6)" }}
                  >
                    <BookOpen className="w-3 h-3" />
                    {evaluation.sumber_dokumen}
                  </span>
                </div>
                <div
                  className="rounded-xl border p-5"
                  style={{ borderColor: "rgba(87,117,144,0.3)", background: "rgba(0,0,0,0.35)" }}
                >
                  <div
                    className="text-[10px] font-bold uppercase tracking-widest mb-3"
                    style={{ color: "#577590", fontFamily: "'', serif" }}
                  >
                    Pertimbangan Semantik
                  </div>
                  <p className="text-sm leading-relaxed italic text-[#F9C74F]/50">
                    &ldquo;{evaluation.alasan}&rdquo;
                  </p>
                </div>
              </div>

              <div className="relative mt-6">
                <button
                  onClick={resetRound}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl font-black text-[#0a0400] text-sm tracking-widest transition-all hover:scale-[1.02] active:scale-[0.98]"
                  style={{ fontFamily: "'', serif", background: "linear-gradient(135deg, #F9C74F, #F8961E)" }}
                >
                  Lanjut Pertanyaan Berikutnya <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div
              className="rounded-2xl border p-6"
              style={{ borderColor: "rgba(249,199,79,0.1)", background: "rgba(249,199,79,0.02)" }}
            >
              <p
                className="text-[10px] uppercase tracking-widest text-[#F9C74F]/40 font-bold mb-3"
                style={{ fontFamily: "'', serif" }}
              >
                Knowledge Retrieval Logs
              </p>
              <div
                className="rounded-lg p-4 text-xs font-mono text-[#F9C74F]/40 max-h-48 overflow-y-auto leading-loose border"
                style={{ background: "rgba(0,0,0,0.4)", borderColor: "rgba(249,199,79,0.08)" }}
              >
                {evaluation.raw_context}
              </div>
            </div>
          </div>
        )}
      </main>

      <style>{`
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(249,199,79,0.2); border-radius: 9999px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(249,199,79,0.4); }
      `}</style>
    </div>
  );
}

// function FontImports() {
//   return (
//     <style>{`
//       @import url('https://fonts.googleapis.com/css2?family=:wght@400;600;700;900&family=+Decorative:wght@700;900&family=Nunito:wght@400;600;700;800&display=swap');
//     `}</style>
//   );
// }