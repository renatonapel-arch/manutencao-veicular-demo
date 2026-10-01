import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

export interface AnexoVisual {
  arquivo_url: string
  mime_type?: string | null
  filename_original?: string | null
}

/**
 * Visualizador de anexo NA PRÓPRIA TELA (follow-up do #0150).
 *
 * O módulo roda num iframe do Clavis. Antes, foto/NF eram `<a target="_blank">`:
 * abria aba nova e, em quem já tinha o service worker do módulo, a navegação
 * para /uploads/... caía no fallback de SPA (devolvia o index.html, ou seja, o
 * módulo inteiro, no lugar do arquivo). Aqui o arquivo aparece num overlay —
 * nenhuma navegação, nenhuma aba nova.
 *
 * PDF não é renderizado inline: dentro de iframe com sandbox (como o Clavis
 * embute o módulo) o visualizador de PDF do navegador não aparece — testado,
 * o quadro fica em branco. Para PDF fica o botão Baixar (o sandbox do Clavis
 * libera download).
 */
export default function AnexoViewer({ anexo, onClose }: { anexo: AnexoVisual | null; onClose: () => void }) {
  const [zoom, setZoom] = useState(false)
  const [falhou, setFalhou] = useState(false)

  useEffect(() => { setZoom(false); setFalhou(false) }, [anexo])

  useEffect(() => {
    if (!anexo) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [anexo, onClose])

  if (!anexo) return null

  const nome = anexo.filename_original || 'anexo'
  const pdf = anexo.mime_type === 'application/pdf'

  // Portal no body: fora do layout da página (o `space-y-3` da tela mobile
  // empurrava o overlay 12px pra baixo e deixava uma faixa descoberta no topo).
  return createPortal(
    <div
      className="fixed inset-0 z-50 flex flex-col bg-noite/90 overscroll-contain"
      role="dialog" aria-modal="true" aria-label={`Anexo ${nome}`}
      onClick={onClose}
    >
      <div className="flex items-center justify-between gap-3 px-4 py-2 text-white text-sm" onClick={(e) => e.stopPropagation()}>
        <span className="truncate">{nome}</span>
        <div className="flex items-center gap-4 shrink-0">
          {!pdf && !falhou && <a href={anexo.arquivo_url} download={nome} className="underline">Baixar</a>}
          <button type="button" onClick={onClose} aria-label="Fechar" className="text-xl leading-none px-1">✕</button>
        </div>
      </div>

      <div className={`flex-1 min-h-0 p-2 ${zoom ? 'overflow-auto' : 'flex items-center justify-center'}`}>
        {falhou ? (
          <div className="bg-white rounded-lg p-5 max-w-sm text-center text-sm" onClick={(e) => e.stopPropagation()}>
            Este arquivo não está mais disponível no servidor. Anexe de novo, se precisar.
          </div>
        ) : pdf ? (
          <div className="bg-white rounded-lg p-5 max-w-sm text-center text-sm space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="text-3xl">📄</div>
            <div>PDF não abre dentro desta tela.</div>
            <a href={anexo.arquivo_url} download={nome} className="inline-block bg-naval text-white px-4 py-2 rounded font-medium">Baixar PDF</a>
          </div>
        ) : (
          <img
            src={anexo.arquivo_url} alt={nome}
            onClick={(e) => { e.stopPropagation(); setZoom(z => !z) }}
            onError={() => setFalhou(true)}
            className={zoom ? 'max-w-none cursor-zoom-out' : 'max-w-full max-h-full object-contain cursor-zoom-in'}
          />
        )}
      </div>
    </div>,
    document.body,
  )
}
