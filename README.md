# Demo VPS — Manutenção Veicular Clavis

Módulo Clavis de gestão de manutenção da frota. Substitui o pipe "Custos - Manutenção Veiculos" do Pipefy por OS-Manutenção centralizada, CPK real por veículo, catálogo de oficinas padronizado e timeline unificada (OS + Troca de Óleo + Checklist V2).

## Stack (idêntica à prod Clavis)

| Camada | Tech |
|---|---|
| Frontend | React 18 + Vite 5 + Refine.dev 4 + Tailwind 3 + tokens DS Napel |
| Backend | FastAPI 0.110 + Python 3.11 |
| DB | PostgreSQL 16 + SQLAlchemy 2 + Alembic |
| Cache/Blacklist | Redis 7 (AOF habilitado) |
| Scheduler | APScheduler |
| Auth | JWT HS256 + Redis blacklist + RBAC (6 roles) |
| Deploy | GitHub → Coolify VPS Hostinger |
| FQDN | `manutencao.demos.napel.com.br` |

## Rodar localmente

```powershell
# 1) Sobe Postgres + Redis + API (porta 8765)
docker compose up -d --build

# 2) Frontend dev (em outro terminal, porta 5173)
cd frontend
npm install
npm run dev

# 3) Abrir
# http://localhost:5173  (frontend dev)
# http://localhost:8765/api/health  (API health)
# http://localhost:8765/docs        (Swagger)
```

PIN/senha demo: `password123` para todos os 6 usuários seed.

## Usuários seed

| Email | Role | Filial |
|---|---|---|
| `hudson@napel.local` | admin | todas |
| `responsavel@maringa.local` | filial_responsavel | 100 |
| `responsavel@pg.local` | filial_responsavel | 700 |
| `responsavel@leme.local` | filial_responsavel | 900 |
| `motorista@mobile.local` | motorista | 100 |
| `admin@oficinas.local` | admin_oficinas | — |

## Seed de dados

Bootstrap automático no primeiro boot:
- 14 veículos (7 motos CG 125/160 FAN + Strada + Montana + 4 Saveiro + Empilhadeira) — placas reais do Pipefy
- 7 oficinas top do Pipefy (DIDA MOTOS, LARANJA MECANICA, Boldor, AGUIA, AK BORRACHARIA, PK, G&C) — texto livre bloqueado
- 200 OS históricas baseadas no Pipefy (mix Motor/Pneu/Pastilha/Relação)
- 12 planos preventivos por modelo
- 150 trocas de óleo (cache do app dedicado)

## O que está mockado (TODOs ADR)

| Integração | Estado MVP | Ativar em |
|---|---|---|
| Controle Patrimonial API (veículos) | Mock arquivo JSON | `ADR-contratos-APIs-externas` |
| App Troca de Óleo API | Mock arquivo JSON | `ADR-contratos-APIs-externas` |
| SIGE V2 (baixa estoque + economia) | Schema pronto, vazio | `ADR-integracao-SIGE-V2` |
| Mercado Livre (lookup preço) | Não ativado | `ADR-integracao-SIGE-V2` |
| Evolution WhatsApp | `EVOLUTION_ENABLED=false` → toast preview | `ADR-evolution-whatsapp` |
| Webhook Checklist V2 | Endpoint registrado → 501 | `ADR-checklist-eletronico-V2` |

## Cherry-pick para produção

Conteúdo de:
- `demos/manutencao-veicular-demo/backend/app/` → `backend/app/modules/manutencao_veicular/`
- `demos/manutencao-veicular-demo/frontend/src/modules/ManutencaoVeicular/` → `frontend/src/modules/ManutencaoVeicular/`

Sem refactor — mesma stack e estrutura de pastas do Clavis main.
