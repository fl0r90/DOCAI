'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../lib/api';
import Cookies from 'js-cookie';
import { Lock, User, KeyRound, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isForcingChange, setIsForcingChange] = useState(false);
  
  const [isResetRequest, setIsResetRequest] = useState(false);
  const [statusMsg, setStatusMsg] = useState({ type: '', text: '' });
  
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMsg({ type: '', text: '' });
    try {
      const res = await api.post('/auth/login', { username, password });
      Cookies.set('token', res.data.access_token);
      Cookies.set('role', res.data.role);
      
      if (res.data.needs_password_change) {
        setIsForcingChange(true);
      } else {
        if (res.data.role === 'ADMIN') router.push('/dashboard');
        else router.push('/');
      }
    } catch (err) {
      setStatusMsg({ type: 'error', text: 'Autentificare eșuată. Verificați credențialele.' });
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setStatusMsg({ type: 'error', text: 'Parolele nu se potrivesc.' });
      return;
    }
    try {
      await api.post('/auth/change-password', { new_password: newPassword });
      const role = Cookies.get('role');
      if (role === 'ADMIN') router.push('/dashboard');
      else router.push('/');
    } catch (err) {
      setStatusMsg({ type: 'error', text: 'Eroare la schimbarea parolei.' });
    }
  };

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/auth/request-reset', { username });
      setStatusMsg({ type: 'success', text: 'Cerere trimisă adminului. Așteaptă aprobarea.' });
      setIsResetRequest(false);
    } catch (err) {
      setStatusMsg({ type: 'error', text: 'Utilizatorul nu a fost găsit.' });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        
        {/* LOGO AREA */}
        <div className="flex justify-center mb-8">
          {isForcingChange ? <KeyRound className="w-12 h-12 text-orange-500 animate-pulse" /> : <Lock className="w-12 h-12 text-blue-500" />}
        </div>

        <h2 className="text-2xl font-black text-white text-center mb-8 tracking-tight">
          {isForcingChange ? 'SCHIMBĂ PAROLA' : isResetRequest ? 'RESETARE CONT' : <>AUTENTIFICARE <span className="text-blue-500">SYSTEM</span></>}
        </h2>
        
        {statusMsg.text && (
          <div className={`p-3 rounded-lg mb-6 text-sm flex items-center gap-2 ${statusMsg.type === 'error' ? 'bg-red-500/10 border border-red-500/50 text-red-500' : 'bg-emerald-500/10 border border-emerald-500/50 text-emerald-500'}`}>
            {statusMsg.type === 'error' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            {statusMsg.text}
          </div>
        )}
        
        {/* FORȚARE SCHIMBARE PAROLĂ */}
        {isForcingChange ? (
          <form onSubmit={handlePasswordChange} className="space-y-6">
            <p className="text-xs text-slate-400 text-center">Ești la prima logare sau parola a fost resetată. Te rugăm să setezi o parolă nouă.</p>
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 block">Parolă Nouă</label>
              <input 
                type="password" 
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-orange-500 transition-colors"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 block">Confirmă Parola</label>
              <input 
                type="password" 
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-orange-500 transition-colors"
                placeholder="••••••••"
              />
            </div>
            <button type="submit" className="w-full bg-orange-600 hover:bg-orange-500 text-white font-bold py-3 rounded-lg transition-colors">
              Salvează și Continuă
            </button>
          </form>
        ) : isResetRequest ? (
          /* CERERE RESETARE */
          <form onSubmit={handleRequestReset} className="space-y-6">
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 block">Utilizator</label>
              <input 
                type="text" 
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-blue-500"
                placeholder="admin"
              />
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => setIsResetRequest(false)} className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-3 rounded-lg transition-colors">Anulează</button>
              <button type="submit" className="flex-[2] bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg transition-colors">Trimite Cerere</button>
            </div>
          </form>
        ) : (
          /* LOGIN NORMAL */
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 block">Utilizator</label>
              <div className="relative">
                <User className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                <input 
                  type="text" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg py-3 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 transition-colors"
                  placeholder="admin"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 block">Parolă</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg py-3 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 transition-colors"
                  placeholder="••••••••"
                />
              </div>
            </div>
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg transition-colors mt-4">
              Intră în cont
            </button>
            <button type="button" onClick={() => setIsResetRequest(true)} className="w-full text-xs text-slate-500 hover:text-blue-400 transition-colors text-center font-bold uppercase tracking-widest">
              Ai uitat parola? Cere resetare
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

