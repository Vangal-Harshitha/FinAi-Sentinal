'use client'
import { useState, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { voiceApi, apiError } from '@/lib/api'
import { Mic, Square, FileText, CheckCircle } from 'lucide-react'

export default function VoicePage() {
  const [recording, setRecording] = useState(false)
  const [result, setResult]       = useState<any>(null)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunks   = useRef<Blob[]>([])

  const transcribeMut = useMutation({
    mutationFn: (audio: Blob) => voiceApi.transcribe(audio),
    onSuccess: (d) => setResult(d),
  })

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      chunks.current = []
      mr.ondataavailable = e => chunks.current.push(e.data)
      mr.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        transcribeMut.mutate(blob)
        stream.getTracks().forEach(t => t.stop())
      }
      mr.start()
      mediaRef.current = mr
      setRecording(true)
    } catch (e) { alert('Microphone access denied') }
  }

  const stopRecording = () => { mediaRef.current?.stop(); setRecording(false) }

  return (
    <AppShell>
      <p className="text-xs mb-5" style={{ color: 'var(--text-muted)' }}>
        Say "I spent 500 rupees at Swiggy" to add a transaction
      </p>

      <div className="card p-10 flex flex-col items-center gap-6 mb-5">
        {/* Mic button */}
        <div className="relative">
          {recording && (
            <div className="absolute inset-0 rounded-full animate-ping"
              style={{ background: 'var(--expense-dim)', scale: '1.5' }} />
          )}
          <div className={`w-28 h-28 rounded-full flex items-center justify-center transition-all`}
            style={{
              background: recording ? 'var(--expense-dim)' : 'var(--accent-dim)',
              border: `2px solid ${recording ? 'var(--expense)' : 'var(--accent)'}`,
              boxShadow: recording ? '0 0 40px rgba(239,68,68,0.2)' : '0 0 40px rgba(99,102,241,0.15)',
            }}>
            <Mic size={32} style={{ color: recording ? 'var(--expense)' : 'var(--text-accent)' }} />
          </div>
        </div>

        <div className="text-center">
          <p className="font-semibold" style={{ color: 'var(--text-primary)' }}>
            {recording ? 'Recording…' : transcribeMut.isPending ? 'Transcribing…' : 'Ready to record'}
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            {recording ? 'Click stop when done' : 'Click the button to start'}
          </p>
        </div>

        {!recording ? (
          <button onClick={startRecording} disabled={transcribeMut.isPending} className="btn-primary" style={{ padding: '10px 28px' }}>
            <Mic size={14} /> Start Recording
          </button>
        ) : (
          <button onClick={stopRecording}
            className="btn-primary" style={{ padding: '10px 28px', background: 'var(--expense)' }}>
            <Square size={14} /> Stop Recording
          </button>
        )}
      </div>

      {transcribeMut.error && (
        <div className="mb-4 p-3 rounded-xl text-sm" style={{ background: 'var(--expense-dim)', color: 'var(--expense)' }}>
          {apiError(transcribeMut.error)}
        </div>
      )}

      {result && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={15} style={{ color: 'var(--text-accent)' }} />
            <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>Transcript</h3>
          </div>
          <p className="text-sm p-3 rounded-xl mb-4 italic"
            style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
            "{result.text}"
          </p>
          {result.transaction && (
            <>
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle size={15} style={{ color: 'var(--income)' }} />
                <h3 className="font-semibold text-sm" style={{ color: 'var(--income)' }}>Parsed Transaction</h3>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(result.transaction).map(([k, v]: any) => v && (
                  <div key={k} className="p-3 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
                    <p className="text-[10px] uppercase tracking-wider mb-0.5 capitalize" style={{ color: 'var(--text-muted)' }}>{k}</p>
                    <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{String(v)}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </AppShell>
  )
}
