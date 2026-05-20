export default function MobilePage() {
  return (
    <section>
      <div className="mb-3">
        <div className="text-lg font-semibold text-naval">PWA do motorista — viewport 375px</div>
        <div className="text-xs text-ink-500">Touch targets ≥44px · câmera nativa · modo offline (IndexedDB)</div>
      </div>

      <div className="flex gap-6 justify-center items-start flex-wrap">
        {/* Device 1: Home */}
        <div>
          <div className="text-center text-[11px] text-ink-500 mb-2 font-medium">1 · Home (sem OS abertas)</div>
          <div className="device-frame">
            <div className="device-screen">
              <div className="device-notch mt-1.5"/>
              <div className="bg-naval text-white px-4 py-3 flex justify-between items-center">
                <div>
                  <div className="text-[10px] text-ceu-claro">Olá, motorista</div>
                  <div className="font-medium">Luiz Gustavo</div>
                </div>
                <div className="w-9 h-9 bg-noite rounded-full flex items-center justify-center text-sm">LG</div>
              </div>
              <div className="bg-gelo px-4 py-2 text-[11px] text-naval border-b border-border">
                🚗 <span className="font-mono">BEO7H12</span> · Strada · KM <span className="font-mono">99.483</span>
              </div>
              <div className="flex-1 px-4 py-4 flex flex-col items-center justify-center text-center bg-page-bg">
                <svg viewBox="0 0 200 160" className="w-32 h-24 mb-3">
                  <circle cx="100" cy="70" r="44" fill="#EBF7FA" stroke="#B5D4E8" strokeWidth="2"/>
                  <path d="M 80 70 L 95 85 L 125 55" stroke="#10B981" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <div className="font-medium text-naval">Sem OS abertas pra você</div>
                <div className="text-[11px] text-ink-500 mt-1 px-4">Se acontecer algo no veículo, abra uma OS aqui.</div>
              </div>
              <div className="p-3 bg-white border-t border-border space-y-2">
                <button className="w-full bg-naval text-white rounded-lg py-3 font-medium text-base">+ Nova OS corretiva</button>
                <button className="w-full border border-border-strong text-naval rounded-lg py-2 font-medium text-sm">📷 Registrar KM</button>
              </div>
            </div>
          </div>
        </div>

        {/* Device 2: Stepper */}
        <div>
          <div className="text-center text-[11px] text-ink-500 mb-2 font-medium">2 · Criar OS — passo 3 (itens)</div>
          <div className="device-frame">
            <div className="device-screen">
              <div className="device-notch mt-1.5"/>
              <div className="bg-white px-4 py-3 flex items-center gap-3 border-b border-border">
                <button className="text-naval text-lg">←</button>
                <div className="flex-1">
                  <div className="text-[10px] text-ink-500">Nova OS</div>
                  <div className="font-medium font-mono">BEO7H12 · Strada</div>
                </div>
              </div>
              <div className="px-4 pt-3 pb-2 bg-white border-b border-border">
                <div className="flex items-center gap-1">
                  <div className="w-6 h-6 rounded-full bg-success text-white flex items-center justify-center text-xs">✓</div>
                  <div className="h-0.5 flex-1 bg-success"/>
                  <div className="w-6 h-6 rounded-full bg-success text-white flex items-center justify-center text-xs">✓</div>
                  <div className="h-0.5 flex-1 bg-naval"/>
                  <div className="w-6 h-6 rounded-full bg-naval text-white flex items-center justify-center text-xs font-mono">3</div>
                  <div className="h-0.5 flex-1 bg-ink-200"/>
                  <div className="w-6 h-6 rounded-full bg-ink-200 text-ink-500 flex items-center justify-center text-xs font-mono">4</div>
                  <div className="h-0.5 flex-1 bg-ink-200"/>
                  <div className="w-6 h-6 rounded-full bg-ink-200 text-ink-500 flex items-center justify-center text-xs font-mono">5</div>
                </div>
                <div className="flex justify-between text-[9px] text-ink-500 mt-1">
                  <span>Tipo</span><span>Oficina</span><span className="text-naval font-medium">Itens</span><span>Anexos</span><span>Revisar</span>
                </div>
              </div>
              <div className="flex-1 px-4 py-3 overflow-y-auto bg-page-bg">
                <div className="space-y-2">
                  <div className="bg-white border border-border-strong rounded-lg p-3">
                    <span className="badge bg-info-bg text-info-fg">Peça</span>
                    <div className="font-medium text-[13px] mt-1">Junta cabeçote</div>
                    <div className="text-[10px] text-success-fg">💡 Napel · economia R$ 22</div>
                    <div className="flex justify-between mt-1 text-[12px] font-mono"><span className="text-ink-500">1×</span><span>R$ 80,00</span></div>
                  </div>
                  <button className="w-full border-2 border-dashed border-ink-300 text-naval rounded-lg py-3 font-medium text-sm">+ Adicionar item</button>
                </div>
                <div className="mt-4 bg-white border border-border rounded-lg p-3 flex justify-between items-center">
                  <span className="text-[11px] text-ink-500">Total</span>
                  <span className="font-semibold font-mono text-naval text-lg">R$ 80,00</span>
                </div>
              </div>
              <div className="p-3 bg-white border-t border-border flex gap-2">
                <button className="flex-1 border border-border-strong text-naval rounded-lg py-3 font-medium">Voltar</button>
                <button className="flex-1 bg-naval text-white rounded-lg py-3 font-medium">Próximo →</button>
              </div>
            </div>
          </div>
        </div>

        {/* Device 3: Anexo NF */}
        <div>
          <div className="text-center text-[11px] text-ink-500 mb-2 font-medium">3 · Anexar NF (passo 4)</div>
          <div className="device-frame">
            <div className="device-screen">
              <div className="device-notch mt-1.5"/>
              <div className="bg-white px-4 py-3 flex items-center gap-3 border-b border-border">
                <button className="text-naval text-lg">←</button>
                <div className="flex-1">
                  <div className="text-[10px] text-ink-500">Passo 4</div>
                  <div className="font-medium">Anexos</div>
                </div>
              </div>
              <div className="flex-1 px-4 py-4 bg-page-bg">
                <div className="mb-3">
                  <div className="text-[11px] font-medium mb-2">📷 Fotos <span className="text-success-fg">(2)</span></div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="aspect-square bg-noite rounded-lg flex items-center justify-center text-3xl">🛢️</div>
                    <div className="aspect-square bg-noite rounded-lg flex items-center justify-center text-3xl">🔧</div>
                    <button className="aspect-square border-2 border-dashed border-ink-300 rounded-lg flex flex-col items-center justify-center text-ink-500 text-[10px]">
                      <span className="text-2xl">📷</span>Câmera
                    </button>
                  </div>
                </div>
                <div className="mb-3">
                  <div className="text-[11px] font-medium mb-2 text-danger-fg">📄 NF obrigatória (0)</div>
                  <button className="w-full border-2 border-dashed border-danger rounded-lg py-6 flex flex-col items-center text-danger-fg">
                    <span className="text-3xl">📄</span>
                    <span className="font-medium text-sm mt-1">Tirar foto da NF</span>
                  </button>
                </div>
                <div className="bg-warn-bg border border-warn rounded-lg p-2.5 text-[11px] text-warn-fg">
                  ⚠️ OS fica em <b>Aguardando anexos</b> até enviar NF. Pode salvar e voltar depois.
                </div>
              </div>
              <div className="p-3 bg-white border-t border-border flex gap-2">
                <button className="flex-1 border border-border-strong text-naval rounded-lg py-3 font-medium">Salvar</button>
                <button className="flex-1 bg-ink-200 text-ink-500 rounded-lg py-3 font-medium cursor-not-allowed">Concluir</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 bg-white border border-border rounded p-3 text-[12px] max-w-3xl mx-auto">
        <div className="font-medium text-naval mb-1">Decisões UX no PWA</div>
        <ul className="space-y-1 list-disc pl-5 text-ink-700">
          <li>Câmera nativa via <span className="font-mono">&lt;input capture="environment"&gt;</span></li>
          <li>Compressão automática 480px webp antes do upload (3G amigável)</li>
          <li>Rascunho em IndexedDB · sincronização automática quando volta conexão</li>
          <li>Touch targets ≥44px · botão "Próximo" 48px</li>
          <li>Cobrança WhatsApp se OS continuar "Aguardando anexos" há +24h</li>
        </ul>
      </div>
    </section>
  )
}
