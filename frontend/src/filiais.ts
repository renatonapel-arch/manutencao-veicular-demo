/**
 * Filiais do módulo — fonte ÚNICA. `id` é o id interno (o mesmo de
 * backend/app/integrations/patrimonial_client.py::_map_filial: o sync converte
 * o código da Frota nesse id) e `codigo` é o código oficial da filial (wiki
 * `filiais`). Antes cada tela tinha a sua tabela e 2 aparecia como "700" (#0257).
 */
export const FILIAIS = [
  { id: 1, codigo: '100', nome: 'Maringá' },
  { id: 2, codigo: '200', nome: 'Ponta Grossa' },
  { id: 3, codigo: '300', nome: 'LEM' },
  { id: 4, codigo: '700', nome: '' },
  { id: 5, codigo: 'DIR', nome: 'Diretoria' },  // 800: carros de gestor, não vinculados às lojas
  { id: 6, codigo: '900', nome: '' },
]

export const codigoFilial = (id: number) => FILIAIS.find(f => f.id === id)?.codigo ?? String(id)

/** "Maringá (100)"; filial sem cidade conhecida sai só "Filial 700". */
export const nomeFilial = (id: number) => {
  const f = FILIAIS.find(x => x.id === id)
  return f ? (f.nome ? `${f.nome} (${f.codigo})` : `Filial ${f.codigo}`) : `Filial ${id}`
}
