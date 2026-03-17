'use client'

import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { receiptsApi, apiError } from '@/lib/api'
import { Upload, CheckCircle, ScanLine } from 'lucide-react'

export default function ReceiptsPage() {

  const qc = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)

  const [result, setResult] = useState<any>(null)

  const { data } = useQuery({
    queryKey: ['receipts'],
    queryFn: () => receiptsApi.history()
  })

  const uploadMut = useMutation({
    mutationFn: (file: File) => receiptsApi.upload(file),
    onSuccess: (d) => {
      setResult(d)
      qc.invalidateQueries({ queryKey: ['receipts'] })
    }
  })

  return (
    <AppShell>

      <p className="text-xs mb-5" style={{ color: 'var(--text-muted)' }}>
        Upload receipts to auto-extract transaction data via OCR
      </p>

      {/* Upload Zone */}
      <div
        className="card p-10 text-center mb-5 cursor-pointer"
        style={{
          border: `2px dashed ${uploadMut.isPending ? 'var(--accent)' : 'var(--border-strong)'}`,
          transition: 'border-color 0.2s'
        }}
        onClick={() => fileInput.current?.click()}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--accent)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor =
            uploadMut.isPending ? 'var(--accent)' : 'var(--border-strong)'
        }}
      >

        <input
          ref={fileInput}
          type="file"
          accept="image/*,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) uploadMut.mutate(file)
          }}
        />

        <div
          className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
          style={{ background: 'var(--accent-dim)' }}
        >
          {uploadMut.isPending ? (
            <div
              className="w-6 h-6 rounded-full border-2 animate-spin"
              style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}
            />
          ) : (
            <Upload size={22} style={{ color: 'var(--text-accent)' }} />
          )}
        </div>

        <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
          {uploadMut.isPending ? 'Processing receipt…' : 'Click to upload receipt'}
        </p>

        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
          JPG, PNG or PDF · Max 10MB
        </p>

      </div>


      {/* Error */}
      {uploadMut.error && (
        <div
          className="mb-4 p-3 rounded-xl text-sm"
          style={{ background: 'var(--expense-dim)', color: 'var(--expense)' }}
        >
          {apiError(uploadMut.error)}
        </div>
      )}


      {/* OCR Result */}
      {result && (
        <div
          className="card p-5 mb-5"
          style={{
            borderColor: 'rgba(34,197,94,0.25)',
            background: 'linear-gradient(135deg, var(--bg-card), #0d1f12)'
          }}
        >

          <div className="flex items-center gap-2 mb-3">
            <CheckCircle size={16} style={{ color: 'var(--income)' }} />
            <h3 className="font-semibold text-sm" style={{ color: 'var(--income)' }}>
              Receipt Parsed Successfully
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-3">

            {result.parsed_receipt &&
              Object.entries(result.parsed_receipt).map(([key, value]: any) => {

                if (!value?.value) return null

                return (
                  <div
                    key={key}
                    className="p-3 rounded-xl"
                    style={{ background: 'var(--income-dim)' }}
                  >

                    <p
                      className="text-[10px] uppercase tracking-wider mb-1"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {key.replace('_', ' ')}
                    </p>

                    <p
                      className="text-sm font-medium"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {key === 'total'
                        ? `₹${parseFloat(value.value).toLocaleString('en-IN')}`
                        : value.value}

                      <span
                        className="text-xs ml-1"
                        style={{ color: 'var(--income)' }}
                      >
                        ({(value.confidence * 100).toFixed(0)}%)
                      </span>
                    </p>

                  </div>
                )
              })}

          </div>
        </div>
      )}


      {/* History */}
      <h3 className="font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>
        Upload History
      </h3>

      {(data?.items ?? []).length === 0 ? (
        <div className="card p-8 text-center">
          <ScanLine size={28} className="mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            No receipts uploaded yet
          </p>
        </div>
      ) : (

        <div className="space-y-2">

          {(data?.items ?? []).map((r: any) => (

            <div
              key={r.receipt_id}
              className="card p-4 flex items-center justify-between"
            >

              <div>
                <p
                  className="font-medium text-sm"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {r.merchant ?? 'Unknown merchant'}
                </p>

                <p
                  className="text-xs mt-0.5"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {r.date ?? '—'} · {r.parse_status}
                </p>
              </div>

              {r.total_amount && (
                <p
                  className="font-bold text-sm"
                  style={{ color: 'var(--text-primary)' }}
                >
                  ₹{parseFloat(r.total_amount).toLocaleString('en-IN')}
                </p>
              )}

            </div>

          ))}

        </div>

      )}

    </AppShell>
  )
}