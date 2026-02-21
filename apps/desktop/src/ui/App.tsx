import React, { useMemo, useState } from 'react'
import { createCase, listCases, listDocuments, listJournal, login, uploadDocument, type Case, type Document, type JournalEntry } from './api'

type View = 'login' | 'cases' | 'case'

export function App() {
  const [view, setView] = useState<View>('login')
  const [token, setToken] = useState<string>('')
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin1234')

  const [cases, setCases] = useState<Case[]>([])
  const [activeCase, setActiveCase] = useState<Case | null>(null)
  const [docs, setDocs] = useState<Document[]>([])
  const [journal, setJournal] = useState<JournalEntry[]>([])

  const [newCaseTitle, setNewCaseTitle] = useState('')
  const [newCaseJur, setNewCaseJur] = useState('')

  const header = useMemo(() => {
    return (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 12, borderBottom: '1px solid #ddd' }}>
        <div style={{ fontWeight: 700 }}>Local Case AI MVP</div>
        <div style={{ fontFamily: 'monospace', fontSize: 12 }}>{token ? `user: ${username}` : 'not logged in'}</div>
      </div>
    )
  }, [token, username])

  async function doLogin() {
    const res = await login(username, password)
    setToken(res.token)
    setView('cases')
    await refreshCases(res.token)
  }

  async function refreshCases(t: string = token) {
    const cs = await listCases(t)
    setCases(cs)
  }

  async function openCase(c: Case) {
    setActiveCase(c)
    setView('case')
    const [d, j] = await Promise.all([listDocuments(token, c.id), listJournal(token, c.id)])
    setDocs(d)
    setJournal(j)
  }

  async function doCreateCase() {
    if (!newCaseTitle.trim()) return
    const c = await createCase(token, newCaseTitle.trim(), newCaseJur.trim(), [])
    setNewCaseTitle('')
    setNewCaseJur('')
    await refreshCases()
    await openCase(c)
  }

  async function doUpload(file: File) {
    if (!activeCase) return
    await uploadDocument(token, activeCase.id, file)
    const [d, j] = await Promise.all([listDocuments(token, activeCase.id), listJournal(token, activeCase.id)])
    setDocs(d)
    setJournal(j)
  }

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Arial', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {header}
      <div style={{ padding: 16, flex: 1, overflow: 'auto' }}>
        {view === 'login' && (
          <div style={{ maxWidth: 420 }}>
            <h2>Login</h2>
            <div style={{ display: 'grid', gap: 8 }}>
              <label>
                Username
                <input value={username} onChange={e => setUsername(e.target.value)} style={{ width: '100%', padding: 8 }} />
              </label>
              <label>
                Password
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} style={{ width: '100%', padding: 8 }} />
              </label>
              <button onClick={doLogin} style={{ padding: 10, fontWeight: 700 }}>Login</button>
              <div style={{ fontSize: 12, color: '#555' }}>
                Default: admin / admin1234
              </div>
            </div>
          </div>
        )}

        {view === 'cases' && (
          <div style={{ maxWidth: 900 }}>
            <h2>Cases</h2>
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <input placeholder="Case title" value={newCaseTitle} onChange={e => setNewCaseTitle(e.target.value)} style={{ flex: 1, padding: 8 }} />
              <input placeholder="Jurisdiction (optional)" value={newCaseJur} onChange={e => setNewCaseJur(e.target.value)} style={{ width: 220, padding: 8 }} />
              <button onClick={doCreateCase} style={{ padding: 10, fontWeight: 700 }}>Create</button>
              <button onClick={() => refreshCases()} style={{ padding: 10 }}>Refresh</button>
            </div>

            <div style={{ border: '1px solid #ddd', borderRadius: 8 }}>
              {cases.length === 0 && <div style={{ padding: 12, color: '#555' }}>No cases yet.</div>}
              {cases.map(c => (
                <div key={c.id} style={{ padding: 12, borderTop: '1px solid #eee', display: 'flex', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{c.title}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>{c.jurisdiction || '—'} · {c.id}</div>
                  </div>
                  <button onClick={() => openCase(c)} style={{ padding: 10 }}>Open</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {view === 'case' && activeCase && (
          <div style={{ maxWidth: 1100 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0 }}>{activeCase.title}</h2>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => { setView('cases'); setActiveCase(null) }} style={{ padding: 10 }}>Back</button>
                <button onClick={() => openCase(activeCase)} style={{ padding: 10 }}>Refresh</button>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
              <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
                <h3>Documents</h3>
                <input type="file" onChange={e => {
                  const f = e.target.files?.[0]
                  if (f) doUpload(f)
                }} />
                <div style={{ marginTop: 12, borderTop: '1px solid #eee' }}>
                  {docs.length === 0 && <div style={{ padding: 10, color: '#555' }}>No documents uploaded.</div>}
                  {docs.map(d => (
                    <div key={d.id} style={{ padding: 10, borderBottom: '1px solid #f0f0f0' }}>
                      <div style={{ fontWeight: 600 }}>{d.filename}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>{d.mime} · {d.id}</div>
                      <div style={{ fontSize: 12, color: '#666', fontFamily: 'monospace' }}>{d.sha256.slice(0, 24)}…</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
                <h3>Journal (append-only)</h3>
                <div style={{ marginTop: 8, borderTop: '1px solid #eee' }}>
                  {journal.length === 0 && <div style={{ padding: 10, color: '#555' }}>No journal entries yet.</div>}
                  {journal.map(j => (
                    <div key={j.id} style={{ padding: 10, borderBottom: '1px solid #f0f0f0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <div style={{ fontWeight: 700 }}>{j.action_type}</div>
                        <div style={{ fontSize: 12, color: '#666' }}>{new Date(j.ts * 1000).toLocaleString()}</div>
                      </div>
                      <div style={{ fontSize: 12, color: '#666' }}>actor: {j.actor}</div>
                      <pre style={{ margin: '6px 0 0', fontSize: 12, background: '#fafafa', padding: 8, overflow: 'auto' }}>
{JSON.stringify(j.payload, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  )
}
