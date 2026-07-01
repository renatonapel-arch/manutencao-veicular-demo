#!/bin/bash
# smoke_test.sh — 1 OS ponta a ponta via curl
#
# Executa o ciclo COMPLETO de uma OS num ambiente real (demo VPS ou local):
#   1. Login (admin)                                 → JWT
#   2. Frota (verifica se tem veículos)              → veiculo_id
#   3. POST /os                                       → cria em rascunho
#   4. transição → aberta                             → em_triagem
#   5. em_triagem → aguardando_orcamento              → aguardando_orcamento
#   6. POST /os/{id}/itens                            → adiciona 1 item R$ 100
#   7. submeter_orcamento (auto-aprova < R$500)       → em_execucao
#   8. POST /os/{id}/encerrar                          → encerrada
#   9. GET /os/{id}                                    → verifica estado final
#
# Uso:
#   BASE=https://manutencao.demos.napel.com.br bash smoke_test.sh
#   BASE=http://localhost:8000 bash smoke_test.sh
#
# Envs:
#   BASE       (default: https://manutencao.demos.napel.com.br)
#   EMAIL      (default: hudson@napel.local)
#   PASSWORD   (default: password123)

set -e

BASE="${BASE:-https://manutencao.demos.napel.com.br}"
EMAIL="${EMAIL:-hudson@napel.local}"
PASSWORD="${PASSWORD:-password123}"

echo "=== SMOKE TEST — Manutenção Veicular ==="
echo "Base: $BASE"
echo "User: $EMAIL"
echo ""

# ---- 1. Login ----
echo "[1/9] Login..."
LOGIN_RESP=$(curl -s -X POST "$BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"senha\":\"$PASSWORD\"}")
TOKEN=$(echo "$LOGIN_RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))")
if [ -z "$TOKEN" ]; then
    echo "❌ Falhou: $LOGIN_RESP"
    exit 1
fi
echo "  ✅ Token obtido"
AUTH="Authorization: Bearer $TOKEN"

# ---- 2. Verifica frota ----
echo "[2/9] Buscando veículos..."
VEIC_RESP=$(curl -s -H "$AUTH" "$BASE/api/veiculos")
VEIC_ID=$(echo "$VEIC_RESP" | python -c "import json,sys; v=json.load(sys.stdin); print(v[0]['id'] if v else '')")
if [ -z "$VEIC_ID" ]; then
    echo "❌ Sem veículos. Rode /admin/sync-frota antes"
    exit 1
fi
echo "  ✅ Veículo ID $VEIC_ID"

# ---- 3. Criar OS (rascunho) ----
echo "[3/9] Criando OS (rascunho)..."
OS_RESP=$(curl -s -X POST "$BASE/api/ordem-servico" \
    -H "$AUTH" -H "Content-Type: application/json" \
    -d "{
      \"request_id\": \"$(python -c 'import uuid;print(uuid.uuid4())')\",
      \"veiculo_id\": $VEIC_ID,
      \"tipo_os\": \"corretiva_manual\",
      \"km_veiculo\": 100,
      \"descricao_problema\": \"Smoke test ponta a ponta\",
      \"itens\": []
    }")
OS_ID=$(echo "$OS_RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('id',''))")
if [ -z "$OS_ID" ]; then
    echo "❌ Falhou criar OS: $OS_RESP"
    exit 1
fi
echo "  ✅ OS #$OS_ID (rascunho)"

# ---- 4. rascunho → aberta ----
# (Se sua API implementou POST /os/{id}/abrir, use — senão o PATCH continua)
echo "[4/9] rascunho → aberta (transição direta pra em_triagem)..."
# rascunho não transiciona direto pra em_triagem — precisa ir por aberta
# Rota específica não existe? tenta manualmente via /triagem falha; use PATCH
# Alternativa: aberta é atingível via POST /os que já cria em rascunho.
# Aqui vamos passar por aberta usando /triagem que exige status aberta.
# Solução: usar PATCH pra mover pra aberta primeiro (workaround por enquanto)
curl -s -X PATCH "$BASE/api/ordem-servico/$OS_ID" \
    -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"status":"aberta"}' > /dev/null || true
echo "  ✅ aberta"

# ---- 5. aberta → em_triagem → aguardando_orcamento ----
echo "[5/9] Triagem + envia p/ orçamento..."
curl -s -X POST "$BASE/api/ordem-servico/$OS_ID/triagem" -H "$AUTH" > /dev/null
curl -s -X POST "$BASE/api/ordem-servico/$OS_ID/enviar-orcamento" -H "$AUTH" > /dev/null
echo "  ✅ aguardando_orcamento"

# ---- 6. Adicionar item R$ 100 ----
echo "[6/9] Adicionando item de R\$ 100..."
curl -s -X POST "$BASE/api/ordem-servico/$OS_ID/itens" \
    -H "$AUTH" -H "Content-Type: application/json" \
    -d '{
      "tipo_item": "peca",
      "descricao": "Peça teste",
      "quantidade": 1,
      "valor_unitario": 100,
      "garantia_dias": 30
    }' > /dev/null
echo "  ✅ Item adicionado"

# ---- 7. Submeter orçamento (auto-aprova < R$500) ----
echo "[7/9] Submetendo orçamento (auto < R\$500)..."
SUB_RESP=$(curl -s -X POST "$BASE/api/ordem-servico/$OS_ID/submeter-orcamento" -H "$AUTH")
STATUS_AFTER=$(echo "$SUB_RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('status',''))")
if [ "$STATUS_AFTER" != "em_execucao" ]; then
    echo "❌ Esperava em_execucao (auto-aprovada), obteve: $STATUS_AFTER"
    echo "$SUB_RESP"
    exit 1
fi
echo "  ✅ Auto-aprovada → em_execucao"

# ---- 8. Encerrar ----
echo "[8/9] Encerrando OS..."
curl -s -X POST "$BASE/api/ordem-servico/$OS_ID/encerrar" -H "$AUTH" > /dev/null
echo "  ✅ Encerrada"

# ---- 9. Verificar estado final ----
echo "[9/9] Verificando estado final..."
FINAL_RESP=$(curl -s -H "$AUTH" "$BASE/api/ordem-servico/$OS_ID")
FINAL_STATUS=$(echo "$FINAL_RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('status',''))")
FINAL_MOTIVO=$(echo "$FINAL_RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('motivo_aprovacao','—'))")
FINAL_VALOR=$(echo "$FINAL_RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('valor_total',''))")

echo ""
echo "=== RESULTADO ==="
echo "OS #$OS_ID"
echo "  status: $FINAL_STATUS"
echo "  motivo_aprovacao: $FINAL_MOTIVO"
echo "  valor_total: $FINAL_VALOR"

if [ "$FINAL_STATUS" = "encerrada" ] && [ "$FINAL_MOTIVO" = "auto" ]; then
    echo ""
    echo "✅ SMOKE TEST PASSOU"
    exit 0
else
    echo ""
    echo "❌ Estado inesperado"
    exit 1
fi
