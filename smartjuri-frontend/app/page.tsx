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
import Buzzer from "./components/buzzer";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

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

interface HistoryItem extends EvaluationResult {
  id: string;
  namaTim: string;
  pertanyaan: string;
  jawaban: string;
  timestamp: Date;
}

// Dipakai untuk buzzer (bg/border/glow saat aktif) dan aksen kecil (dot leaderboard, badge "Tekan!").
const COLOR_SCHEMES: { [key: number]: any } = {
  1: {
    bg: "bg-amber-600",
    border: "border-amber-400",
    glow: "shadow-[0_0_40px_rgba(245,158,11,0.35)]",
    text: "text-amber-600 dark:text-amber-400",
    dot: "bg-amber-500",
    badgeBg: "bg-amber-500",
    badgeText: "text-amber-950",
  },
  2: {
    bg: "bg-cyan-600",
    border: "border-cyan-400",
    glow: "shadow-[0_0_40px_rgba(6,182,212,0.35)]",
    text: "text-cyan-600 dark:text-cyan-400",
    dot: "bg-cyan-500",
    badgeBg: "bg-cyan-500",
    badgeText: "text-cyan-950",
  },
  3: {
    bg: "bg-emerald-600",
    border: "border-emerald-400",
    glow: "shadow-[0_0_40px_rgba(16,185,129,0.35)]",
    text: "text-emerald-600 dark:text-emerald-400",
    dot: "bg-emerald-500",
    badgeBg: "bg-emerald-500",
    badgeText: "text-emerald-950",
  },
  4: {
    bg: "bg-fuchsia-600",
    border: "border-fuchsia-400",
    glow: "shadow-[0_0_40px_rgba(217,70,239,0.35)]",
    text: "text-fuchsia-600 dark:text-fuchsia-400",
    dot: "bg-fuchsia-500",
    badgeBg: "bg-fuchsia-500",
    badgeText: "text-fuchsia-950",
  },
  5: {
    bg: "bg-rose-600",
    border: "border-rose-400",
    glow: "shadow-[0_0_40px_rgba(244,63,94,0.35)]",
    text: "text-rose-600 dark:text-rose-400",
    dot: "bg-rose-500",
    badgeBg: "bg-rose-500",
    badgeText: "text-rose-950",
  },
  6: {
    bg: "bg-indigo-600",
    border: "border-indigo-400",
    glow: "shadow-[0_0_40px_rgba(99,102,241,0.35)]",
    text: "text-indigo-600 dark:text-indigo-400",
    dot: "bg-indigo-500",
    badgeBg: "bg-indigo-500",
    badgeText: "text-indigo-950",
  },
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
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);

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

      // Add to history
      setHistoryItems((prev) => [
        {
          ...data,
          id: Date.now().toString(),
          namaTim: activeTeam?.nama || "Kontestan",
          pertanyaan: pertanyaan,
          jawaban: jawabanInput,
          timestamp: new Date(),
        },
        ...prev,
      ]);

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

  const clearHistory = () => {
    setHistoryItems([]);
  };

  if (!gameStarted) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
        <Card className="max-w-md w-full shadow-lg">
          <CardHeader className="text-center space-y-3">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Shield className="w-7 h-7" />
            </div>
            <CardTitle className="text-2xl">ScoreHub</CardTitle>
            <CardDescription>
              Konfigurasi jumlah kontestan untuk memulai kompetisi cerdas cermat otomatis.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-left">
            <label className="text-sm font-medium text-foreground">Jumlah Kontestan Regu</label>
            <Input
              type="number"
              min={2}
              max={6}
              value={jumlahPeserta}
              onChange={(e) => setJumlahPeserta(Number(e.target.value))}
            />
          </CardContent>
          <CardFooter>
            <Button onClick={handleSetupGame} className="w-full" size="lg">
              Masuk Arena Lomba
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col md:flex-row">
      {/* SIDEBAR PANEL */}
      <aside className="w-full md:w-80 border-r bg-muted/30 p-6 flex flex-col justify-between">
        <div className="space-y-8">
          <div className="flex items-center gap-3">
            <div className="bg-primary text-primary-foreground p-2 rounded-lg">
              <Shield className="w-5 h-5" />
            </div>
            <span className="font-semibold text-xl tracking-tight">ScoreHub</span>
          </div>

          <div className="space-y-3">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              System Status
            </div>
            <Card className="border-emerald-500/30 bg-emerald-500/5 py-0">
              <CardContent className="flex items-center gap-2 px-3 py-2.5 text-sm text-emerald-600 dark:text-emerald-400">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                Core Engine API Connected
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Crown className="text-amber-500 w-4 h-4" />
                <CardTitle className="text-base">Leaderboard</CardTitle>
              </div>
              <CardDescription>Papan skor kontestan</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {kontestans
                .slice()
                .sort((a, b) => b.skorAkumulasi - a.skorAkumulasi)
                .map((k) => {
                  const scheme = COLOR_SCHEMES[k.id] || COLOR_SCHEMES[1];
                  return (
                    <div
                      key={k.id}
                      className="flex items-center justify-between rounded-lg border bg-background px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${scheme.dot}`} />
                        <span className="text-sm font-medium">{k.nama}</span>
                      </div>
                      <Badge variant="secondary" className="font-mono">
                        {k.skorAkumulasi}
                      </Badge>
                    </div>
                  );
                })}
            </CardContent>
          </Card>
        </div>

        <Button
          variant="ghost"
          onClick={() => setGameStarted(false)}
          className="justify-start text-muted-foreground hover:text-destructive mt-6"
        >
          <RefreshCw className="w-4 h-4 mr-2" /> Reset Konfigurasi Awal
        </Button>
      </aside>

      {/* DASHBOARD KONTEN UTAMA */}
      <main className="flex-1 p-6 lg:p-10 space-y-6 max-w-5xl mx-auto w-full">
        {/* Header Dashboard & Timer Panel */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 pb-6 border-b">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Selamat Datang di Arena Cerdas Cermat</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Evaluasi dan analisis jawaban kontestan.
            </p>
          </div>

          <Card className="py-0">
            <CardContent className="flex items-center gap-4 px-4 py-2.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Babak Penyisihan
              </span>
              <Badge
                variant={isTimerActive ? "default" : "secondary"}
                className="gap-1.5 font-mono text-sm px-3 py-1"
              >
                <Clock className={`w-3.5 h-3.5 ${isTimerActive ? "animate-pulse" : ""}`} />
                {formatTime(secondsLeft)}
              </Badge>
            </CardContent>
          </Card>
        </div>

        {/* INPUT SOAL PERTANYAAN */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground font-semibold">
                Input Soal Disini
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={isListeningPertanyaan ? "destructive" : "outline"}
                size="sm"
                onClick={toggleVoicePertanyaan}
                disabled={evaluation !== null || buzzerWinner !== null}
              >
                {isListeningPertanyaan ? (
                  <MicOff className="w-3.5 h-3.5 mr-1.5" />
                ) : (
                  <Mic className="w-3.5 h-3.5 mr-1.5" />
                )}
                {isListeningPertanyaan ? "Mendengarkan..." : "Voice Input"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handlePastePertanyaan}
                disabled={evaluation !== null || buzzerWinner !== null}
              >
                <Clipboard className="w-3.5 h-3.5 mr-1.5" /> Paste Soal
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              rows={3}
              value={pertanyaan}
              onChange={(e) => setPertanyaan(e.target.value)}
              disabled={evaluation !== null || buzzerWinner !== null}
              placeholder={
                isListeningPertanyaan
                  ? "Silakan bicara sekarang, juri..."
                  : "Tuliskan atau paste pertanyaan kompetisi hukum/kewarganegaraan di sini..."
              }
              className="text-lg"
            />
            <div className="flex flex-row gap-2">
              <Badge variant="outline">MPR RI</Badge>
              <Badge variant="outline">Pancasila</Badge>
              <Badge variant="outline">UUD 1945</Badge>
            </div>
          </CardContent>
        </Card>

        {/* INTERFACE GRID TOMBOL BUZZER */}
        {pertanyaan && !evaluation && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground font-semibold">
                Tekan Tombol Buzzer!
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                {kontestans.map((k) => {
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
            </CardContent>
          </Card>
        )}

        {/* PANEL MASUKAN JAWABAN TIM TERCEPAT */}
        {buzzerWinner !== null && !evaluation && (
          <Card className="border-primary/30">
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-sm uppercase tracking-wide text-primary font-semibold">
                Input Jawaban: {kontestans.find((k) => k.id === buzzerWinner)?.nama}
              </CardTitle>
              <span
                className={`text-lg font-mono font-semibold ${
                  secondsLeft < 15 ? "text-destructive animate-pulse" : "text-primary"
                }`}
              >
                {formatTime(secondsLeft)}
              </span>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative flex items-center">
                <Input
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
                  className="pr-12 h-12 text-base"
                />
                <Button
                  type="button"
                  size="icon"
                  variant={isListeningJawaban ? "destructive" : "secondary"}
                  onClick={toggleVoiceJawaban}
                  className="absolute right-1.5 h-9 w-9"
                >
                  {isListeningJawaban ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </Button>
              </div>
              <Button
                onClick={handleProsesPenilaian}
                disabled={loading || !jawabanInput.trim() || isListeningJawaban}
                className="w-full"
                size="lg"
              >
                {loading ? (
                  <RefreshCw className="animate-spin w-4 h-4 mr-2" />
                ) : (
                  <Sparkles className="w-4 h-4 mr-2" />
                )}
                {loading ? "Mengevaluasi..." : "Mulai Menilai!"}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* OUTPUT HASIL KEPUTUSAN JURI AI */}
        {evaluation && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle>Hasil Evaluasi Juri AI</CardTitle>
                    <CardDescription className="mt-1">
                      Status: Keputusan bersifat mutlak berdasarkan dokumen negara resmi.
                    </CardDescription>
                  </div>
                  <div
                    className={`text-4xl font-bold tabular-nums ${
                      evaluation.skor > 6 ? "text-emerald-600 dark:text-emerald-400" : "text-destructive"
                    }`}
                  >
                    {evaluation.skor}
                    <span className="text-lg text-muted-foreground">/10</span>
                  </div>
                </div>
              </CardHeader>
              <Separator />
              <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-0">
                <Card className="bg-muted/40">
                  <CardContent className="pt-6">
                    <div className="text-xs text-primary font-semibold uppercase tracking-wide mb-3">
                      Kunci Jawaban Resmi
                    </div>
                    <p className="text-sm leading-relaxed">{evaluation.kunci_jawaban}</p>
                    <Badge variant="outline" className="mt-4 gap-1.5">
                      <BookOpen className="w-3 h-3" />
                      {evaluation.sumber_dokumen}
                    </Badge>
                  </CardContent>
                </Card>
                <Card className="bg-muted/40">
                  <CardContent className="pt-6">
                    <div className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold uppercase tracking-wide mb-3">
                      Pertimbangan Semantik
                    </div>
                    <p className="text-sm leading-relaxed italic text-muted-foreground">
                      &quot;{evaluation.alasan}&quot;
                    </p>
                  </CardContent>
                </Card>
              </CardContent>
              <CardFooter>
                <Button onClick={resetRound}>
                  Lanjut Pertanyaan Berikutnya <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">
                  Knowledge Retrieval Logs
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-muted/40 border rounded-lg p-4 text-xs font-mono text-muted-foreground max-h-48 overflow-y-auto leading-loose">
                  {evaluation.raw_context}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* HISTORY JAWABAN PESERTA SEBELUMNYA */}
        {historyItems.length > 0 && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle>Riwayat Jawaban Peserta</CardTitle>
                <CardDescription className="mt-1">
                  Log evaluasi dari {historyItems.length} jawaban sebelumnya
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={clearHistory}
                className="text-destructive hover:text-destructive"
              >
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Hapus History
              </Button>
            </CardHeader>
            <Separator />
            <CardContent className="pt-6">
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {historyItems.map((item) => {
                  const scheme = COLOR_SCHEMES[item.namaTim.charCodeAt(item.namaTim.length - 1) % 6 + 1] || COLOR_SCHEMES[1];
                  return (
                    <div
                      key={item.id}
                      className="border rounded-lg p-4 bg-muted/40 hover:bg-muted/60 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div className="flex items-center gap-3">
                          <span className={`h-3 w-3 rounded-full ${scheme.dot}`} />
                          <div>
                            <div className="font-medium text-sm">{item.namaTim}</div>
                            <div className="text-xs text-muted-foreground">
                              {item.timestamp.toLocaleTimeString("id-ID")}
                            </div>
                          </div>
                        </div>
                        <div
                          className={`text-lg font-bold tabular-nums ${
                            item.skor > 6
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "text-destructive"
                          }`}
                        >
                          {item.skor}/10
                        </div>
                      </div>
                      <div className="space-y-2 text-sm">
                        <div>
                          <div className="text-xs font-semibold text-muted-foreground uppercase mb-1">
                            Pertanyaan
                          </div>
                          <p className="text-foreground line-clamp-2">{item.pertanyaan}</p>
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-muted-foreground uppercase mb-1">
                            Jawaban Peserta
                          </div>
                          <p className="text-foreground line-clamp-2">{item.jawaban}</p>
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-muted-foreground uppercase mb-1">
                            Kunci Jawaban
                          </div>
                          <p className="text-foreground line-clamp-2">{item.kunci_jawaban}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}