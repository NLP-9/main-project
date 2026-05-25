"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Shield, Award, AlertCircle, HelpCircle, RefreshCw, ChessQueen, Clock, Clipboard, Mic, MicOff } from 'lucide-react';
import Buzzer from './components/buzzer';

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

const COLOR_SCHEMES: { [key: number]: any } = {
  1: {
    bg: "bg-amber-600",
    border: "border-amber-400",
    glow: "shadow-[0_0_50px_rgba(245,158,11,0.4)]",
    text: "text-amber-400",
    badgeBg: "bg-amber-500/10",
    badgeText: "text-amber-400"
  },
  2: {
    bg: "bg-cyan-600",
    border: "border-cyan-400",
    glow: "shadow-[0_0_50px_rgba(6,182,212,0.4)]",
    text: "text-cyan-400",
    badgeBg: "bg-cyan-500/10",
    badgeText: "text-cyan-400"
  },
  3: {
    bg: "bg-emerald-600",
    border: "border-emerald-400",
    glow: "shadow-[0_0_50px_rgba(16,185,129,0.4)]",
    text: "text-emerald-400",
    badgeBg: "bg-emerald-500/10",
    badgeText: "text-emerald-400"
  },
  4: {
    bg: "bg-fuchsia-600",
    border: "border-fuchsia-400",
    glow: "shadow-[0_0_50px_rgba(217,70,239,0.4)]",
    text: "text-fuchsia-400",
    badgeBg: "bg-fuchsia-500/10",
    badgeText: "text-fuchsia-400"
  },
  5: {
    bg: "bg-rose-600",
    border: "border-rose-400",
    glow: "shadow-[0_0_50px_rgba(244,63,94,0.4)]",
    text: "text-rose-400",
    badgeBg: "bg-rose-500/10",
    badgeText: "text-rose-400"
  },
  6: {
    bg: "bg-indigo-600",
    border: "border-indigo-400",
    glow: "shadow-[0_0_50px_rgba(99,102,241,0.4)]",
    text: "text-indigo-400",
    badgeBg: "bg-indigo-500/10",
    badgeText: "text-indigo-400"
  }
};

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

    // Inisialisasi Web Speech API Browser
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
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
      setLockedOutUsers(prev => [...prev, buzzerWinner]);
      setBuzzerWinner(null);
      setJawabanInput("");
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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

    // Voice to Text Pertanyaan
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
      recognitionRef.current.onerror = () => {
        setIsListeningPertanyaan(false);
      };
      recognitionRef.current.onend = () => {
        setIsListeningPertanyaan(false);
      };
      recognitionRef.current.start();
    }
  };

  // Voice to Text Kontestan
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
      recognitionRef.current.onerror = () => {
        setIsListeningJawaban(false);
      };
      recognitionRef.current.onend = () => {
        setIsListeningJawaban(false);
      };
      recognitionRef.current.start();
    }
  };

  const handleProsesPenilaian = async () => {
    if (!buzzerWinner || !jawabanInput.trim()) return;
    setIsTimerActive(false);
    setLoading(true);
    setEvaluation(null);
    
    const activeTeam = kontestans.find(k => k.id === buzzerWinner);
    
    try {
      const res = await fetch("http://localhost:8000/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pertanyaan: pertanyaan,
          nama_kontestan: activeTeam?.nama || "Kontestan",
          jawaban_kontestan: jawabanInput
        })
      });
      
      const data: EvaluationResult = await res.json();
      setEvaluation(data);
      
      if (data.skor > 0) {
        setKontestans(prev => prev.map(k => 
          k.id === buzzerWinner ? { ...k, skorAkumulasi: k.skorAkumulasi + data.skor } : k
        ));
      } else {
        setLockedOutUsers(prev => [...prev, buzzerWinner]);
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

  if (!gameStarted) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl max-w-md w-full shadow-2xl text-center">
          <Shield className="w-16 h-16 text-blue-500 mx-auto mb-4" />
          <h1 className="text-3xl font-bold tracking-tight mb-2">SmartJuri-AI Arena</h1>
          <p className="text-slate-400 text-sm mb-6">Konfigurasi jumlah kontestan untuk memulai kompetisi cerdas cermat otomatis.</p>
          <div className="mb-6 text-left">
            <label className="text-sm font-semibold text-slate-300 block mb-2">Jumlah Kontestan Regu:</label>
            <input 
              type="number" min="2" max="6"
              value={jumlahPeserta}
              onChange={(e) => setJumlahPeserta(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <button 
            onClick={handleSetupGame}
            className="w-full bg-linear-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 py-3 rounded-xl font-bold transition-all shadow-lg cursor-pointer"
          >
            Masuk Arena Lomba
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      {/* SIDEBAR PANEL */}
      <aside className="w-full md:w-80 bg-slate-900 border-r border-slate-800 p-6 flex flex-col justify-between shadow-2xl">
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div className="bg-blue-600 p-2 rounded-xl text-white shadow-md shadow-blue-500/20">
              <Shield className="w-6 h-6" />
            </div>
            <span className="font-bold text-xl tracking-wide text-white">SmartJuri-AI</span>
          </div>
          <div className="space-y-4">
            <div className="text-xs font-semibold text-slate-500 tracking-wider uppercase">System Status</div>
            <div className="bg-emerald-950/40 border border-emerald-900/50 rounded-xl p-3 flex items-center gap-3 text-emerald-400 text-sm">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Core Engine API Connected
            </div>
          </div>
          <div className="mt-8 space-y-3 border-solid border-slate-100/10 border rounded-2xl p-5 bg-slate-950/50">
            <div className='flex flex-col gap-1 mb-4'>
              <div className='flex flex-row gap-2 items-center'>
                <ChessQueen className='text-amber-400 w-5 h-5'/>
                <div className="text-xl font-bold tracking-tight text-white">Leaderboard</div>
              </div>
              <div className="text-xs text-slate-500">Papan skor kontestan</div>
            </div>
            <div className="space-y-2">
              {kontestans.map(k => (
                <div key={k.id} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-3 flex justify-between items-center">
                  <span className="font-medium text-slate-300 text-sm">{k.nama}</span>
                  <span className="bg-slate-900 px-3 py-1 rounded-lg font-bold text-blue-400 border border-slate-700 text-sm">{k.skorAkumulasi}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <button onClick={() => setGameStarted(false)} className="text-sm text-slate-500 hover:text-red-400 flex items-center gap-2 mt-6 cursor-pointer">
          <RefreshCw className="w-4 h-4" /> Reset Konfigurasi Awal
        </button>
      </aside>

      {/* DASHBOARD KONTEN UTAMA */}
      <main className="flex-1 p-6 lg:p-10 space-y-6 max-w-5xl mx-auto w-full">
        {/* Header Dashboard & Timer Panel */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 border-b border-slate-900 pb-6">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">Evaluation Dashboard</h1>
            <p className="text-sm text-slate-400 mt-1">Enter contest details and team answers for semantic analysis.</p>
          </div>
          
          <div className="flex items-center gap-3 self-end sm:self-auto">
            <div className="bg-slate-900 border border-slate-800 px-5 py-2.5 rounded-full flex items-center gap-4 shadow-xl">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Babak Penyisihan</span>
              <div className={`flex items-center gap-2 px-4 py-1 rounded-full border transition-colors ${isTimerActive ? 'bg-blue-950/40 border-blue-500/50 text-blue-400' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
                <Clock className={`w-4 h-4 ${isTimerActive ? 'animate-pulse' : ''}`} />
                <span className="font-mono font-bold text-xl">{formatTime(secondsLeft)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* INPUT SOAL PERTANYAAN */}
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-3xl space-y-4 shadow-xl">
          <div className="flex justify-between items-center">
            <h2 className="text-xs font-bold tracking-widest text-slate-400 flex items-center gap-2 uppercase">
              Contest Question Context
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={toggleVoicePertanyaan}
                disabled={evaluation !== null || buzzerWinner !== null}
                className={`border px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition cursor-pointer ${
                  isListeningPertanyaan 
                    ? "bg-red-600/20 border-red-500 text-red-400 animate-pulse" 
                    : "bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700 disabled:opacity-30"
                }`}
              >
                {isListeningPertanyaan ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                {isListeningPertanyaan ? "Mendengarkan..." : "Voice Input"}
              </button>
              <button
                onClick={handlePastePertanyaan}
                disabled={evaluation !== null || buzzerWinner !== null}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 border border-slate-700 px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
              >
                <Clipboard className="w-3.5 h-3.5" /> Paste Soal
              </button>
            </div>
          </div>
          <textarea 
            rows={2}
            value={pertanyaan}
            onChange={(e) => setPertanyaan(e.target.value)}
            disabled={evaluation !== null || buzzerWinner !== null}
            placeholder={isListeningPertanyaan ? "Silakan bicara sekarang, juri..." : "Tuliskan atau paste pertanyaan kompetisi hukum/kewarganegaraan di sini..."}
            className="w-full bg-slate-950 border border-slate-800 text-xl font-medium rounded-2xl p-5 text-slate-200 focus:outline-none focus:border-blue-500 transition disabled:opacity-50"
          />
          <div className='flex flex-row gap-2 pt-1'>
            <span className='bg-slate-800 text-slate-400 border border-slate-700 px-4 py-1.5 rounded-full text-xs font-semibold'>MPR RI</span>
            <span className='bg-slate-800 text-slate-400 border border-slate-700 px-4 py-1.5 rounded-full text-xs font-semibold'>Pancasila</span>
            <span className='bg-slate-800 text-slate-400 border border-slate-700 px-4 py-1.5 rounded-full text-xs font-semibold'>UUD 1945</span>
          </div>
        </div>

        {/* INTERFACE GRID TOMBOL BUZZER */}
        {pertanyaan && !evaluation && (
          <div className="bg-slate-900/30 border border-slate-800/60 p-6 rounded-3xl space-y-5 shadow-xl">
            <h2 className="text-sm font-bold tracking-widest text-slate-400 flex items-center gap-2 uppercase">
              Contestant Submissions (Buzzer)
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {kontestans.map(k => {
                const isWinner = buzzerWinner === k.id;
                const isDisabled = (buzzerWinner !== null && !isWinner) || lockedOutUsers.includes(k.id);
                const isLockedOut = lockedOutUsers.includes(k.id);
                const currentScheme = COLOR_SCHEMES[k.id] || COLOR_SCHEMES[1];
                
                return (
                  <Buzzer
                    key={k.id}
                    namaTim={k.nama}
                    isActive={isWinner}
                    isDisabled={isDisabled}
                    isLockedOut={isLockedOut}
                    onClick={() => handleBuzzerClick(k.id)}
                    colorScheme={currentScheme}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* PANEL MASUKAN JAWABAN TIM TERCEPAT */}
        {buzzerWinner !== null && !evaluation && (
          <div className="bg-slate-900 border border-blue-500/30 p-6 rounded-3xl space-y-4 shadow-2xl shadow-blue-500/5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-blue-400 font-bold uppercase tracking-widest">
                Input Jawaban: {kontestans.find(k => k.id === buzzerWinner)?.nama}
              </div>
              <span className={`text-xl font-mono font-bold ${secondsLeft < 15 ? 'text-red-500 animate-pulse' : 'text-blue-400'}`}>
                {formatTime(secondsLeft)}
              </span>
            </div>
            <div className="relative flex items-center">
              <input 
                type="text"
                autoFocus
                value={jawabanInput}
                onChange={(e) => setJawabanInput(e.target.value)}
                placeholder={isListeningJawaban ? "Silakan bicara, tim tercepat..." : `Ketik transkrip jawaban lisan dari ${kontestans.find(k => k.id === buzzerWinner)?.nama}...`}
                className="w-full bg-slate-950 border border-slate-800 rounded-2xl pl-6 pr-14 py-4 text-white text-lg focus:outline-none focus:border-blue-500 transition"
              />
              <button
                onClick={toggleVoiceJawaban}
                className={`absolute right-4 p-2.5 rounded-xl transition cursor-pointer ${
                  isListeningJawaban 
                    ? "bg-red-600 text-white animate-pulse shadow-lg shadow-red-500/30" 
                    : "bg-slate-800 text-slate-400 hover:text-white"
                }`}
              >
                {isListeningJawaban ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
            </div>
            <button
              onClick={handleProsesPenilaian}
              disabled={loading || !jawabanInput.trim() || isListeningJawaban}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-extrabold py-4 rounded-2xl transition shadow-xl disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
            >
              {loading ? <RefreshCw className="animate-spin w-5 h-5" /> : "🚀 MULAI EVALUASI SEMANTIK"}
            </button>
          </div>
        )}

        {/* OUTPUT HASIL KEPUTUSAN JURI AI */}
        {evaluation && (
          <div className="space-y-6 animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 space-y-6 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 p-8">
                <div className={`text-5xl font-black ${evaluation.skor > 6 ? 'text-emerald-500' : 'text-red-500'}`}>
                  {evaluation.skor}<span className="text-xl text-slate-600">/10</span>
                </div>
              </div>

              <div className="border-b border-slate-800 pb-6">
                <h3 className="text-xl font-bold flex items-center gap-3 text-white">
                  Hasil Evaluasi Juri AI
                </h3>
                <p className="text-sm text-slate-500 mt-1">Status: Keputusan bersifat mutlak berdasarkan dokumen negara resmi.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-slate-950/80 p-6 rounded-2xl border border-slate-800/50">
                  <div className="text-[10px] text-blue-400 font-black uppercase tracking-[0.2em] mb-3">Kunci Jawaban Resmi</div>
                  <p className="text-sm text-slate-300 leading-relaxed font-medium">{evaluation.kunci_jawaban}</p>
                  <div className="inline-block mt-4 px-3 py-1 bg-slate-900 rounded-lg text-[10px] text-slate-500 border border-slate-800">
                    📚 {evaluation.sumber_dokumen}
                  </div>
                </div>
                <div className="bg-slate-950/80 p-6 rounded-2xl border border-slate-800/50">
                  <div className="text-[10px] text-indigo-400 font-black uppercase tracking-[0.2em] mb-3">Pertimbangan Semantik</div>
                  <p className="text-sm text-slate-300 leading-relaxed italic">&quot;{evaluation.alasan}&quot;</p>
                </div>
              </div>

              <div className="pt-4 flex justify-start mx-auto">
                 <button onClick={resetRound} className="w-fit bg-blue-600 hover:bg-blue-700 px-8 py-3 rounded-2xl text-sm font-bold text-white transition flex items-center gap-2 shadow-lg shadow-blue-600/20 cursor-pointer">
                   Lanjut Pertanyaan Berikutnya <RefreshCw className="w-4 h-4" />
                 </button>
              </div>
            </div>

            <div className="bg-slate-900/30 border border-slate-800/50 rounded-3xl p-6">
              <div className="text-xs font-black text-slate-500 mb-4 uppercase tracking-[0.3em] px-2">Knowledge Retrieval Logs</div>
              <div className="bg-slate-950/50 border border-slate-800 rounded-2xl p-6 text-xs text-slate-400 font-mono max-h-48 overflow-y-auto leading-loose">
                {evaluation.raw_context}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}