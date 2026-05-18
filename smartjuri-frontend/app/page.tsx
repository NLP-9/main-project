"use client";

import React, { useState } from 'react';
import { Shield, Users, Award, AlertCircle, Volume2, HelpCircle, RefreshCw } from 'lucide-react';

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
  
  const [loading, setLoading] = useState<boolean>(false);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);

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
      setBuzzerWinner(id);
    }
  };

  const handleProsesPenilaian = async () => {
    if (!buzzerWinner || !jawabanInput.trim()) return;
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
    } finally {
      setLoading(false);
    }
  };

  const resetRound = () => {
    setBuzzerWinner(null);
    setJawabanInput("");
    setEvaluation(null);
    setLockedOutUsers([]);
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
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 py-3 rounded-xl font-bold transition-all shadow-lg"
          >
            Masuk Arena Lomba
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      {/* SIDEBAR PANEL BARU SPERTI REFERENSI GAMBAR */}
      <aside className="w-full md:w-80 bg-slate-900 border-r border-slate-800 p-6 flex flex-col justify-between">
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
          <div className="mt-8 space-y-3">
            <div className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Papan Skor Kontestan</div>
            {kontestans.map(k => (
              <div key={k.id} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3 flex justify-between items-center">
                <span className="font-medium text-slate-300">{k.nama}</span>
                <span className="bg-slate-900 px-3 py-1 rounded-lg font-bold text-blue-400 border border-slate-700">{k.skorAkumulasi} Pts</span>
              </div>
            ))}
          </div>
        </div>
        <button onClick={() => setGameStarted(false)} className="text-sm text-slate-500 hover:text-red-400 flex items-center gap-2 mt-6">
          <RefreshCw className="w-4 h-4" /> Reset Konfigurasi Awal
        </button>
      </aside>

      {/* DASHBOARD KONTEN UTAMA COMPETITION */}
      <main className="flex-1 p-6 lg:p-8 space-y-6 max-w-5xl mx-auto w-full">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Arena Cerdas Cermat</h1>
            <p className="text-sm text-slate-400">Masukkan pertanyaan kompetisi dan aktifkan modul interaksi buzzer sistem.</p>
          </div>
          {evaluation && (
            <button onClick={resetRound} className="bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2">
              <RefreshCw className="w-4 h-4" /> Babak Baru
            </button>
          )}
        </div>

        {/* INPUT SOAL PERTANYAAN */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-3 shadow-xl">
          <h2 className="text-sm font-semibold tracking-wide text-slate-400 flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-blue-400" /> Masukkan Pertanyaan Aktif
          </h2>
          <textarea 
            rows={2}
            value={pertanyaan}
            onChange={(e) => setPertanyaan(e.target.value)}
            disabled={evaluation !== null}
            placeholder="Tuliskan pertanyaan kompetisi hukum/kewarganegaraan di sini..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-200 focus:outline-none focus:border-blue-500 transition disabled:opacity-50"
          />
        </div>

        {/* MODUL BUZZER REBUTAN REAL-TIME */}
        {pertanyaan && !evaluation && (
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
            <h2 className="text-sm font-semibold tracking-wide text-slate-400 flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-amber-400" /> Modul Kendali Rebutan Jawaban (Buzzer)
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {kontestans.map(k => {
                const isWinner = buzzerWinner === k.id;
                const isDisabled = (buzzerWinner !== null && !isWinner) || lockedOutUsers.includes(k.id);
                
                return (
                  <button
                    key={k.id}
                    disabled={isDisabled}
                    onClick={() => handleBuzzerClick(k.id)}
                    className={`p-6 rounded-xl font-bold border flex flex-col items-center justify-center gap-2 transition duration-200 ${
                      isWinner 
                        ? 'bg-amber-600 border-amber-400 text-white shadow-lg shadow-amber-600/30 ring-4 ring-amber-500/20 scale-105'
                        : lockedOutUsers.includes(k.id)
                        ? 'bg-red-950/20 border-red-900/30 text-red-700 opacity-40 line-through'
                        : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700 active:scale-95 disabled:opacity-30'
                    }`}
                  >
                    <span className="text-sm tracking-wider uppercase">{k.nama}</span>
                    <span className="text-xs font-normal text-slate-400">
                      {isWinner ? '🎉 Tercepat!' : lockedOutUsers.includes(k.id) ? 'Jawaban Salah' : 'Klik Buzzer'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* KOLOM INPUT JAWABAN JIKA PESERTA SUDAH PENCET BUZZER */}
        {buzzerWinner !== null && !evaluation && (
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4 animate-in fade-in slide-in-from-bottom-2">
            <div className="flex items-center gap-2 text-sm text-amber-400 font-semibold">
              <AlertCircle className="w-4 h-4" />
              Hak Menjawab Terkunci Otomatis untuk: {kontestans.find(k => k.id === buzzerWinner)?.nama}
            </div>
            <input 
              type="text"
              value={jawabanInput}
              onChange={(e) => setJawabanInput(e.target.value)}
              placeholder={`Masukkan respon lisan dari ${kontestans.find(k => k.id === buzzerWinner)?.nama}...`}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-amber-500"
            />
            <button
              onClick={handleProsesPenilaian}
              disabled={loading || !jawabanInput.trim()}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition shadow-lg disabled:opacity-50"
            >
              {loading ? "Juri AI Sedang Menilai Semantik..." : "⚙️ SERAHKAN JAWABAN KE JURI AI"}
            </button>
          </div>
        )}

        {/* REPORT OUTPUT EVALUASI RAG JURI AI */}
        {evaluation && (
          <div className="space-y-6 animate-in fade-in duration-300">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
              <div className="flex justify-between items-start border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-lg font-bold flex items-center gap-2">
                    <Award className="w-5 h-5 text-blue-500" /> Hasil Keputusan Akhir Juri AI
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">Analisis kemiripan makna teks secara absolut.</p>
                </div>
                <div className={`text-2xl font-black px-4 py-1.5 rounded-xl border ${
                  evaluation.skor > 0 ? 'bg-emerald-950/50 text-emerald-400 border-emerald-800/60' : 'bg-red-950/50 text-red-400 border-red-800/60'
                }`}>
                  {evaluation.skor} <span className="text-xs font-normal text-slate-500">/ 10</span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80">
                  <div className="text-xs text-blue-400 font-bold uppercase tracking-wider mb-1">🔑 Kunci Jawaban Resmi:</div>
                  <p className="text-sm text-slate-300 leading-relaxed">{evaluation.kunci_jawaban}</p>
                  <div className="text-xs text-slate-500 mt-2 font-mono">Sumber: {evaluation.sumber_dokumen}</div>
                </div>
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80">
                  <div className="text-xs text-indigo-400 font-bold uppercase tracking-wider mb-1">📝 Analisis Pertimbangan Juri:</div>
                  <p className="text-sm text-slate-300 leading-relaxed">{evaluation.alasan}</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
              <div className="text-sm font-semibold text-slate-400 mb-2 px-1">📚 Dokumen Pengetahuan RAG Utama (Ground Truth)</div>
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs text-slate-500 font-mono max-h-40 overflow-y-auto whitespace-pre-wrap">
                {evaluation.raw_context}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}