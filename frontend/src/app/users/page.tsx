'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import api from '../../lib/api';
import { Users, UserPlus, Trash2, Shield, ChevronLeft, Loader2, AlertCircle, Star, StarOff } from 'lucide-react';

export default function UserManagement() {
  const router = useRouter();
  const [users, setUsers] = useState<any[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(true);

  // New User State
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('WORKER');
  const [userError, setUserError] = useState('');

  const token = Cookies.get('token');
  const role = Cookies.get('role');

  const fetchUsers = async () => {
    try {
      const res = await api.get('/auth/users');
      setUsers(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchMe = async () => {
    try {
      const res = await api.get('/auth/me');
      setCurrentUser(res.data);
    } catch (err) { console.error(err); }
  }

  useEffect(() => {
    setMounted(true);
    if (!token || role !== 'ADMIN') {
      router.push('/login');
      return;
    }
    fetchUsers();
    fetchMe();
  }, [router]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserError('');
    if (!newUsername || !newPassword) {
      setUserError('Completați toate câmpurile.');
      return;
    }
    try {
      await api.post('/auth/users', { username: newUsername, password: newPassword, role: newRole });
      setNewUsername('');
      setNewPassword('');
      fetchUsers();
    } catch (err: any) {
      setUserError(err.response?.data?.detail || 'Eroare la crearea utilizatorului.');
    }
  };

  const handleDeleteUser = async (id: number) => {
    if (!confirm('Sigur doriți să ștergeți acest utilizator?')) return;
    try {
      await api.delete(`/auth/users/${id}`);
      fetchUsers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Eroare la ștergerea utilizatorului.');
    }
  };

  const handleTogglePriority = async (id: number, currentPriority: number) => {
    const newPriority = currentPriority > 0 ? 0 : 10;
    try {
      await api.post(`/auth/users/${id}/priority`, { priority: newPriority });
      fetchUsers();
    } catch (err) {
      alert("Eroare la actualizarea priorității.");
    }
  };

  if (!mounted || !token || role !== 'ADMIN') {
    return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-blue-500"><Loader2 className="animate-spin" /></div>;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8 font-sans animate-in fade-in duration-500">
      <nav className="flex justify-between items-center mb-12 border-b border-slate-800 pb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push('/dashboard')} className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white">
            <ChevronLeft />
          </button>
          <div className="flex items-center gap-3">
            <Users className="text-blue-500 w-8 h-8" />
            <h1 className="text-2xl font-black tracking-tighter uppercase">Gestiune <span className="text-blue-500">Utilizatori</span></h1>
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-slate-300">Admin: <span className="text-blue-400">@{currentUser?.username}</span></p>
          <Shield className="w-6 h-6 text-blue-500/50 ml-auto mt-1" />
        </div>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        {/* User Table */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
          <div className="p-6 border-b border-slate-800 bg-slate-900/50">
            <h2 className="text-sm font-black tracking-widest text-slate-400 uppercase">Utilizatori Înregistrați ({users.length})</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-950/50 text-[10px] font-black uppercase text-slate-500 tracking-widest">
                <tr>
                  <th className="px-6 py-4 text-center">ID</th>
                  <th className="px-6 py-4">Utilizator</th>
                  <th className="px-6 py-4 text-center">Prioritate</th>
                  <th className="px-6 py-4">Rol Acces</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Acțiuni</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {users.map(u => (
                  <tr key={u.id} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors group">
                    <td className="px-6 py-4 text-center font-mono text-slate-600">{u.id}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-200">@{u.username}</span>
                        {u.needs_password_change === 1 && <span className="text-[8px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/20 font-black tracking-tighter">NEW</span>}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <button 
                        onClick={() => handleTogglePriority(u.id, u.priority)}
                        className={`p-2 rounded-xl transition-all border ${u.priority > 0 ? 'bg-amber-500/10 text-amber-500 border-amber-500/30' : 'bg-slate-800/50 text-slate-600 border-slate-800'}`}
                        title={u.priority > 0 ? "Utilizator Prioritar" : "Setează Prioritate"}
                      >
                        {u.priority > 0 ? <Star className="w-4 h-4 fill-amber-500" /> : <StarOff className="w-4 h-4" />}
                      </button>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-md text-[10px] font-black tracking-widest ${u.role === 'ADMIN' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : u.role === 'MASTER' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${u.is_active ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-red-500'}`}></div>
                        <span className="text-[10px] font-bold text-slate-500 uppercase">{u.is_active ? 'Activ' : 'Inactiv'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {u.username !== 'admin' && (
                        <button 
                          onClick={() => handleDeleteUser(u.id)}
                          className="p-2 bg-red-500/10 text-red-500 rounded-xl hover:bg-red-500 hover:text-white transition-all border border-red-500/20 opacity-0 group-hover:opacity-100 shadow-lg shadow-red-500/10"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Add User Form */}
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-3xl shadow-2xl h-fit sticky top-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-3 bg-blue-500/10 text-blue-500 rounded-2xl"><UserPlus className="w-6 h-6" /></div>
            <h2 className="text-lg font-black tracking-tight uppercase">Cont Nou</h2>
          </div>
          
          {userError && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-500 p-4 rounded-xl mb-6 text-xs flex items-center gap-3">
              <AlertCircle className="w-4 h-4" /> {userError}
            </div>
          )}

          <form onSubmit={handleCreateUser} className="space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nume Utilizator</label>
              <input 
                type="text" 
                value={newUsername} 
                onChange={e => setNewUsername(e.target.value)} 
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition-all" 
                placeholder="ex: operator_01" 
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Parolă Provizorie</label>
              <input 
                type="password" 
                value={newPassword} 
                onChange={e => setNewPassword(e.target.value)} 
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition-all" 
                placeholder="••••••••" 
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nivel Acces</label>
              <select 
                value={newRole} 
                onChange={e => setNewRole(e.target.value)} 
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 cursor-pointer transition-all"
              >
                <option value="WORKER">WORKER (Operativ)</option>
                <option value="MASTER">MASTER (Sef Dosar)</option>
                <option value="ADMIN">ADMIN (Supervizor)</option>
              </select>
            </div>
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-black py-4 rounded-xl text-xs uppercase tracking-widest transition-all shadow-xl shadow-blue-600/20 active:scale-95">
              Creează Investigator
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
