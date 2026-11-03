# Operasyon kılavuzu

SupportFlow'u çalıştıran, demosunu hazırlayan ya da bir sorunu gideren kişi için: yapılandırma, servisler, rutin prosedürler ve arıza durumunda ne yapılacağı. Kurulum adımları [DEVELOPMENT](DEVELOPMENT.md#1-kurulum)'da.

> Bu bir demo kurulumudur. Üretim için eksik olanlar [SECURITY](SECURITY.md#bilinen-eksikler-üretim-için-gerekenler)'de ve README'deki "Bilinen sınırlamalar"da listelenir.

## Servisler

| Servis | Adres | Sağlık |
|---|---|---|
| PostgreSQL 17 + pgvector (`db`, imaj `pgvector/pgvector:pg17`) | `localhost:5433` (container içinde `db:5432`) | Compose `pg_isready` healthcheck |
| Backend (FastAPI) | http://localhost:8000 | `GET /health` (süreç), `GET /ready` (veritabanı) |
| API dokümantasyonu | http://localhost:8000/docs | |
| Frontend (Vite) | http://localhost:5173 | `/api`, `/health`, `/ready` isteklerini backend'e yönlendirir |

Compose ile backend açılırken önce `alembic upgrade head` çalışır, sonra uvicorn başlar.

### Açılışta otomatik kurtarma

Backend her açılışta (tek süreç varsayımıyla, [ADR-005](DECISIONS.md#adr-005-analiz-çalıştırmaları-kalıcı-arka-plan-işleridir)):

1. `queued` ya da `running` durumunda kalmış analiz çalıştırmalarını `interrupted` koduyla `failed` yapar; talepler `failed` olur ve yeniden açılıp denenebilir.
2. Son karar tarihi geçmiş bekleyen önerileri `expired` yapar (asla yürütülmezler).
3. `executing` durumunda kalmış önerileri (onay ile uygulama arasında çökme) idempotency anahtarıyla tamamlar; etki en fazla bir kez oluşur ([ADR-012](DECISIONS.md#adr-012-idempotent-yürütücü-ile-iki-adımlı-onay)).

Veritabanına ulaşılamazsa kurtarma loglanır ve atlanır; uygulama yine açılır, `/ready` 503 döner.

## Yapılandırma

Değerler ortam değişkenlerinden ve repo kökündeki `.env`'den okunur (`backend/app/core/config.py`). Şablon: `.env.example`. Compose'daki `environment` değerleri `.env`'i ezer.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `APP_ENV` | `development` | `development`, `test`, `production`. `production` geliştirme JWT sırrıyla açılmayı reddeder |
| `LOG_LEVEL` | `INFO` | Python log seviyesi |
| `POSTGRES_HOST_PORT` | `5433` | Compose'un Postgres'i yayınladığı host portu |
| `DATABASE_URL` | `postgresql+psycopg://supportflow:supportflow@localhost:5433/supportflow` | Uygulama veritabanı |
| `TEST_DATABASE_URL` | `...@localhost:5433/supportflow_test` | Yalnızca testler; asla geliştirme veritabanını göstermemeli |
| `DATABASE_CONNECT_TIMEOUT` | `3` | Saniye; `/ready`'nin hızlı cevap vermesi için kısa |
| `JWT_SECRET_KEY` | geliştirme sırrı | Üretimde 32+ karakterlik rastgele değer zorunlu |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token ömrü |
| `DEMO_USER_PASSWORD` | `supportflow-demo` | Seed'in demo kullanıcılarına verdiği parola |
| `LLM_MODE` | `fake` | `fake`: ücretsiz, deterministik, çevrimdışı. `live`: Gemini |
| `GEMINI_API_KEY` | yok | `live` için zorunlu. Asla commit'lenmez |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Sabitlenmiş model sürümü ([ADR-009](DECISIONS.md#adr-009-llm-sağlayıcısı-olarak-gemini-api)) |
| `LLM_TIMEOUT_SECONDS` | `30` | Tek model çağrısının zaman aşımı |
| `LLM_MAX_ATTEMPTS` | `3` | Geçici hatalarda deneme sayısı (artan bekleme ile) |
| `AGENT_MAX_TOKENS_PER_RUN` | `12000` | Bir analizin token bütçesi; aşılırsa `token_budget_exceeded` |
| `AGENT_RUN_TIMEOUT_SECONDS` | `120` | Bir analizin süre sınırı; aşılırsa `run_timeout` |
| `PROPOSAL_TTL_HOURS` | `48` | Bekleyen önerinin karar süresi |
| `EMBEDDING_MODE` | `fake` | Politika araması için embedding: `fake` (çevrimdışı, deterministik) ya da `live` (Gemini, `GEMINI_API_KEY` gerekir) |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-2` | Canlı embedding modeli; 768 boyutla kullanılır ([ADR-014](DECISIONS.md#adr-014-politika-bilgi-tabanı-pgvector-madde-bazlı-parçalar-kararlar-kodda-kalır)) |
| `AGENT_TOOL_TRANSPORT` | `mcp` | Ajanın sipariş ve talep geçmişini nasıl okuduğu: `mcp` (süreç içi MCP sunucusu) ya da `direct` (servisler; geri dönüş yolu) ([ADR-015](DECISIONS.md#adr-015-salt-okunur-mcp-adaptörü-stdio--süreç-içi-bağlantı-kimlik-bağlantıdan-gelir)) |
| `MCP_TOOL_TIMEOUT_SECONDS` | `10` | Bir MCP araç çağrısının süre sınırı; aşılırsa analiz `tool_timeout` ile biter |
| `MCP_ACCESS_TOKEN` | yok | stdio MCP sunucusunun adına çalıştığı personel token'ı (`poe mcp-token`); boşsa `poe mcp` başlamaz |
| `VITE_DEMO_MODE` (frontend) | yok | `true` ise üretim derlemesinde de demo giriş butonları görünür (geliştirmede hep görünür) |
| `VITE_API_BASE_URL` (frontend) | yok | Backend'in adresi (canlıda `https://supportflow-api-e4i6.onrender.com`); boşsa istekler aynı kaynağa gider (geliştirmede Vite proxy'si). Derleme sırasında okunur |
| `CORS_ALLOW_ORIGINS` | yok | API'yi tarayıcıdan çağırabilecek kaynaklar, virgülle (canlıda Pages adresi). Boşsa CORS başlığı eklenmez |

## Rutin prosedürler

### Demo öncesi hazırlık

```bash
cd backend
uv run poe seed --reset     # tüm veriyi (denetim kaydı dahil) siler, NovaShop verisini yeniden kurar
```

Sonuç: 3 kullanıcı, 20 müşteri, 50 sipariş, 30 talep; politika bilgi tabanı sahte embedder'la indekslenir (canlı embedding için ayrıca `poe ingest`). Yedi talep sahte modelle önceden analiz edilir, biri onaylanır: iki iade yönetici bekler, bir adres değişikliği herhangi bir personeli bekler. 1 numaralı talep ("Siparişim nerede?") canlı gösterim için `new` bırakılır. Kontrol: `GET /api/v1/tickets/summary` → `pending_proposals: 3`.

Seed idempotenttir: `--reset` olmadan tekrar çalıştırmak eksik kayıtları ekler, var olanlara dokunmaz.

### Gerçek modele geçmek (`LLM_MODE=live`)

1. Google AI Studio'dan bir API anahtarı alın.
2. `.env`'de `LLM_MODE=live` ve `GEMINI_API_KEY=...` ayarlayın.
3. Backend'i yeniden başlatın (ayarlar açılışta okunur).
4. Doğrulama: bir talebi analiz edin; çalıştırmanın `model` alanı `gemini-...` olmalı (sahte modelde `fake-llm`).

Seed her zaman sahte modeli kullanır, `LLM_MODE`'dan etkilenmez. Ücretsiz kota hızlı tükenebilir; canlı eval betiği istekleri bu yüzden aralıklı gönderir.

### Politika bilgi tabanını indekslemek

```bash
cd backend
uv run poe ingest          # EMBEDDING_MODE'a göre (varsayılan: sahte, ücretsiz)
uv run poe ingest --fake   # her zaman sahte embedder
```

Çıktı eklenen, yerini alan ve değişmeyen doküman sayısını ve güncel sürümleri listeler. Tekrar çalıştırmak güvenlidir. Bir politikayı değiştirmek için dokümanın `version` değerini artırın; sürümü artırılmadan değiştirilmiş doküman reddedilir (`Ingestion failed: ... sürüm artırılmamış`) ve veritabanı değişmez. Sonuç her çalıştırmada `ingestion_jobs` tablosuna da yazılır. Canlı ve sahte embedding'ler ayrı tutulur; `EMBEDDING_MODE` değiştirilince `poe ingest` yeniden çalıştırılmalıdır.

### MCP sunucusunu bir istemciye bağlamak

Sunucu salt okunurdur ve istemcinin başlattığı yerel bir süreç olarak stdio üzerinden konuşur ([ADR-015](DECISIONS.md#adr-015-salt-okunur-mcp-adaptörü-stdio--süreç-içi-bağlantı-kimlik-bağlantıdan-gelir)). Önce bir personel token'ı alın, sonra istemciye komutu ve token'ı verin:

```bash
cd backend
uv run poe mcp-token --email selin@novashop.example   # parola: MCP_LOGIN_PASSWORD ya da sorulur
```

MCP Inspector ile (Node.js gerekir; `localhost:6274`'te bir arayüz açar):

```bash
npx @modelcontextprotocol/inspector -e MCP_ACCESS_TOKEN=<token> uv --directory backend run python -m app.mcp
```

Masaüstü asistanı gibi JSON yapılandırması kullanan bir istemci için:

```json
{{
  "mcpServers": {{
    "supportflow": {{
      "command": "uv",
      "args": ["--directory", "C:/yol/SupportFlow/backend", "run", "python", "-m", "app.mcp"],
      "env": {{ "MCP_ACCESS_TOKEN": "<token>" }}
    }}
  }}
}}
```

Token `ACCESS_TOKEN_EXPIRE_MINUTES` (30 dk) sonra geçersizleşir; araçlar `[unauthorized]` döndürünce yeni token alın. Her çağrı backend log'una `MCP tool call <call_id>: tool=… caller=user:<id> ticket=… outcome=…` satırı ve denetim kaydına `mcp.tool_called` girdisi yazar. stdout protokole ayrıldığı için loglar stderr'e gider.

### Migration

```bash
cd backend
uv run poe migrate                         # bekleyenleri uygula
uv run alembic current                     # şu anki sürüm
uv run alembic downgrade -1                # bir geri al (yerel veride dikkat)
```

### Canlı demo

Barındırma kararı ve gerekçesi [ADR-016](DECISIONS.md#adr-016-canlı-demo-cloudflare-pages--render--supabase-ücretsiz-katmanlar)'da.

| Parça | Nerede | Ayarlar |
|---|---|---|
| Frontend | Cloudflare Pages, `supportflow` projesi: https://supportflow-w7q.pages.dev | Kök dizin `frontend`, derleme `npm run build`, çıktı `dist`; ortam: `VITE_API_BASE_URL`, `VITE_DEMO_MODE=true`, `NODE_VERSION=24`. Güvenlik başlıkları `frontend/public/_headers`'ta |
| Backend | Render, `supportflow-api` (free, Frankfurt, Docker): https://supportflow-api-e4i6.onrender.com | Dockerfile `backend/Dockerfile`, bağlam `backend`; ortam: `APP_ENV=production`, `DATABASE_URL`, `JWT_SECRET_KEY`, `LLM_MODE=fake`, `EMBEDDING_MODE=fake`, `CORS_ALLOW_ORIGINS` |
| Veritabanı | Supabase, `supportflow` projesi (Frankfurt) | Şema `supportflow`, rol `supportflow_app`; bağlantı session pooler: `postgresql+psycopg://supportflow_app.<proje-ref>:<parola>@aws-1-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require` |
| Günlük sıfırlama | GitHub Actions `Demo reset` (03:00 UTC, elle de çalıştırılabilir) | Secret: `DEMO_DATABASE_URL` (yukarıdaki bağlantı adresi) |

**Erişim notu:** 2026-11-03'te geliştirme makinesindeki komut satırı araçları (`curl`, PowerShell) hiçbir `*.pages.dev` adresine bağlanamadı (TLS el sıkışmasında bağlantı sıfırlandı), aynı makinedeki tarayıcı ise siteyi açtı. Muhtemel neden, ağdaki SNI filtrelemesi ve tarayıcının ECH ile alan adını gizlemesi. Bir ziyaretçi açamazsa önce başka bir tarayıcı ya da ağ denenmeli; kalıcı çözüm, Pages'e bağlanan kendi alan adıdır.

**Yayın:** `main`'e birleşen her değişiklik Render ve Pages'te kendiliğinden yayınlanır. Render açılışta migration'ları uygular; yeni bir migration geri alınamaz durumdaysa önce yerelde `upgrade`/`downgrade` turunu (`test_migrations.py`) doğrulayın.

**Geri alma:** Render panelinde servis → Events → önceki başarılı deploy → "Rollback". Pages'te Deployments → önceki sürüm → "Rollback". Migration içeren bir sürümü geri alırken veritabanı yeni şemada kalır; gerekiyorsa `DATABASE_URL` ile yerelden `uv run alembic downgrade -1` çalıştırın.

**Veriyi elle sıfırlamak:** GitHub → Actions → Demo reset → "Run workflow", ya da yerelden `DATABASE_URL=<canlı adres> uv run python -m scripts.seed_demo --reset`.

**Soğuk başlatma:** Render ücretsiz servisi 15 dakika istek almazsa uyur. Gösterimden önce `https://supportflow-api-e4i6.onrender.com/ready` adresini açıp `ready` yanıtını bekleyin.

**Uygulama rolünü kurmak** (yeni bir Supabase projesinde bir kez, SQL editöründe):

```sql
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE ROLE supportflow_app LOGIN PASSWORD '<güçlü parola>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
GRANT supportflow_app TO postgres;            -- şemayı bu role verebilmek için
CREATE SCHEMA supportflow AUTHORIZATION supportflow_app;
GRANT USAGE ON SCHEMA extensions TO supportflow_app;
ALTER ROLE supportflow_app SET search_path = supportflow, extensions;
ALTER ROLE supportflow_app SET statement_timeout = '30s';
```

Ardından yerelden `DATABASE_URL=<adres> uv run alembic upgrade head` ve `uv run python -m scripts.seed_demo` çalıştırın. Supabase'in güvenlik danışmanı (Advisors → Security) temiz olmalıdır.

### JWT sırrını değiştirmek

`JWT_SECRET_KEY`'i değiştirip backend'i yeniden başlatın. Verilmiş tüm token'lar geçersizleşir; kullanıcılar yeniden giriş yapar.

## Sorun giderme

### `Ingestion failed` hatası

Mesaj nedeni söyler: sürümü artırılmadan değiştirilmiş doküman, güncelden eski sürüm, iki dosyada aynı `id` ya da biçim hatası (ön bilgi eksik, `## KİMLİK başlık` bölümü yok, tekrarlanan madde). Dosyayı düzeltip yeniden çalıştırın; başarısız çalıştırma hiçbir şeyi değiştirmez.

### `extension "vector" is not available`

Postgres eski `postgres:17-alpine` imajıyla çalışıyor. `compose.yaml` artık `pgvector/pgvector:pg17` kullanır; yerel veritabanını yeni imajla kurun: `docker compose down -v && docker compose up -d db`, ardından `poe migrate`, `poe seed`, `poe ingest` (yerel demo verisi silinir ve yeniden oluşur).

### Analiz `tool_timeout` ya da `tool_error` ile bitiyor

Ajanın MCP üzerinden yaptığı sipariş sorgusu süre sınırını aştı ya da sunucu bir hata döndürdü. Ayrıntı backend log'undaki `MCP tool call … outcome=…` satırındadır (`internal_error` ise hemen öncesinde `crashed` satırı ve hata izi vardır). Veritabanının ayakta olduğunu (`/ready`) kontrol edip talebi yeniden açın ve tekrar deneyin. Sorun MCP katmanındaysa `AGENT_TOOL_TRANSPORT=direct` ile geçici olarak doğrudan servis çağrısına dönülebilir.

### Canlı demoda "Sunucuya ulaşılamıyor"

Önce `https://supportflow-api-e4i6.onrender.com/ready`'yi açın: Render servisi uyuyorsa 30–60 saniye içinde uyanır. Sürekli hata varsa Render → Logs'a bakın. Tarayıcı konsolunda CORS hatası görünüyorsa Render'daki `CORS_ALLOW_ORIGINS` değeri Pages adresiyle (sonunda `/` olmadan) birebir aynı olmalıdır. `/ready` 503 dönüyorsa Supabase projesinin duraklatılmadığını (Supabase panelinde "Restore") ve `DATABASE_URL`'nin session pooler adresi olduğunu kontrol edin.

### `/ready` 503 dönüyor

Veritabanına ulaşılamıyor. `docker compose ps` ile `db` servisinin `healthy` olduğunu kontrol edin; `DATABASE_URL`'nin host/portunu doğrulayın (makineden `localhost:5433`, container'dan `db:5432`). Nedeni backend logunda `Readiness check failed` satırındadır.

### Analiz `llm_rate_limited` ya da `llm_timeout` ile bitiyor

Canlı modelin kota ya da hız sınırı. Talebi yeniden açıp (`PATCH` ile `new`) birkaç dakika sonra tekrar deneyin. Sorun sürerse demo için `LLM_MODE=fake`'e dönün. `gemini-3.8-flash` gibi daha büyük modeller ücretsiz katmanda çok daha hızlı 429 verir.

### Analiz `invalid_output` ile bitiyor

Model şemaya uymayan bir yanıt verdi; ham çıktı güvenlik gereği saklanmaz. Talebi yeniden açıp tekrar deneyin. Sık tekrarlanıyorsa prompt ya da model değişikliği gerekir: `uv run poe eval --live` ile ölçün.

### Talep `triaging`'de takılı kaldı

Arka plan işi süreç içinde çalışır; süreç analiz sırasında öldüyse çalıştırma yarım kalır. Backend'i yeniden başlatın: açılıştaki kurtarma çalıştırmayı `interrupted` ile `failed` yapar, talep yeniden açılıp analiz edilebilir.

### Öneri onaylandı ama `executing`'de kaldı

Onay ile uygulama arasında süreç durdu. Backend'i yeniden başlatın; kurtarma aynı idempotency anahtarıyla uygulamayı tamamlar, ikinci bir etki oluşmaz. Sonuç önerinin `status`'ünde ve denetim kaydında görünür.

### Onaylamak 409 veriyor

Beklenen davranış olabilir: öneri başka biri tarafından karara bağlanmış, süresi dolmuş, içeriği değişmiş ya da ekrandaki sürüm eski. `detail` mesajı nedeni söyler; sayfayı yenileyip güncel duruma bakın. Hiçbir durumda ikinci bir etki oluşmaz.

### Onay `failed` (Engellendi) ile bitti

Onay anındaki yeniden kontrol izin vermedi; en sık neden siparişin öneriden sonra kargoya verilmesi. Neden önerinin `failure_reason` alanında. Sipariş değişmemiştir; müşteriye durumu açıklayın.

### Denetim kaydı silinemiyor

Bilerek böyle: veritabanı trigger'ı `audit_logs` üzerinde UPDATE ve DELETE'i reddeder. Yalnızca `seed --reset` (TRUNCATE) kaydı temizler.

## Loglar

Backend standart çıktıya Python `logging` biçiminde yazar (`docker compose logs -f backend`). Ham model çıktısı ve müşteri metni loglanmaz; analiz adımlarının özetleri yalnızca kimlik ve sayı içerir. Her istek, analiz ve iş için ortak bir `correlation_id` ile yapılandırılmış (JSON) loglama planlanmıştır (Faz 10); şimdilik ilişkilendirme `ticket_id` ve `run_id` ile yapılır.
