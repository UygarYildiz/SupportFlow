# Operasyon kılavuzu

SupportFlow'u çalıştıran, demosunu hazırlayan ya da bir sorunu gideren kişi için: yapılandırma, servisler, rutin prosedürler ve arıza durumunda ne yapılacağı. Kurulum adımları [DEVELOPMENT](DEVELOPMENT.md#1-kurulum)'da.

> Bu bir demo kurulumudur. Üretim için eksik olanlar [SECURITY](SECURITY.md#bilinen-eksikler-üretim-için-gerekenler)'de ve README'deki "Bilinen sınırlamalar"da listelenir.

## Servisler

| Servis | Adres | Sağlık |
|---|---|---|
| PostgreSQL 17 (`db`) | `localhost:5433` (container içinde `db:5432`) | Compose `pg_isready` healthcheck |
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
| `VITE_DEMO_MODE` (frontend) | yok | `true` ise üretim derlemesinde de demo giriş butonları görünür (geliştirmede hep görünür) |

## Rutin prosedürler

### Demo öncesi hazırlık

```bash
cd backend
uv run poe seed --reset     # tüm veriyi (denetim kaydı dahil) siler, NovaShop verisini yeniden kurar
```

Sonuç: 3 kullanıcı, 20 müşteri, 50 sipariş, 30 talep. Yedi talep sahte modelle önceden analiz edilir, biri onaylanır: iki iade yönetici bekler, bir adres değişikliği herhangi bir personeli bekler. 1 numaralı talep ("Siparişim nerede?") canlı gösterim için `new` bırakılır. Kontrol: `GET /api/v1/tickets/summary` → `pending_proposals: 3`.

Seed idempotenttir: `--reset` olmadan tekrar çalıştırmak eksik kayıtları ekler, var olanlara dokunmaz.

### Gerçek modele geçmek (`LLM_MODE=live`)

1. Google AI Studio'dan bir API anahtarı alın.
2. `.env`'de `LLM_MODE=live` ve `GEMINI_API_KEY=...` ayarlayın.
3. Backend'i yeniden başlatın (ayarlar açılışta okunur).
4. Doğrulama: bir talebi analiz edin; çalıştırmanın `model` alanı `gemini-...` olmalı (sahte modelde `fake-llm`).

Seed her zaman sahte modeli kullanır, `LLM_MODE`'dan etkilenmez. Ücretsiz kota hızlı tükenebilir; canlı eval betiği istekleri bu yüzden aralıklı gönderir.

### Migration

```bash
cd backend
uv run poe migrate                         # bekleyenleri uygula
uv run alembic current                     # şu anki sürüm
uv run alembic downgrade -1                # bir geri al (yerel veride dikkat)
```

### JWT sırrını değiştirmek

`JWT_SECRET_KEY`'i değiştirip backend'i yeniden başlatın. Verilmiş tüm token'lar geçersizleşir; kullanıcılar yeniden giriş yapar.

## Sorun giderme

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
