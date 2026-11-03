# Geliştirme kılavuzu

Projeyi ilk kez açan bir geliştiricinin yerelde çalıştırıp güvenle değişiklik yapabilmesi için. Mimari kurallar [ARCHITECTURE](ARCHITECTURE.md)'da, terimler [Sözlük](GLOSSARY.md)'te; bu doküman "nasıl yapılır" sorusunu cevaplar.

## 1. Kurulum

Gerekenler: [Docker](https://docs.docker.com/get-docker/), [uv](https://docs.astral.sh/uv/) (Python sürümünü kendisi yönetir; proje 3.12 kullanır), Node.js 24+, git.

```bash
git clone https://github.com/UygarYildiz/SupportFlow.git
cd SupportFlow
cp .env.example .env              # yerel varsayılanlar; sır içermez

docker compose up -d db           # yalnızca Postgres (host portu 5433)

cd backend
uv sync                           # bağımlılıklar + .venv
uv run poe migrate                # şemayı oluştur
uv run poe seed                   # NovaShop demo verisi
uv run poe dev                    # API: http://localhost:8000 (dokümantasyon: /docs)

cd ../frontend                    # ikinci terminal
npm install
npm run dev                       # Panel: http://localhost:5173
```

Doğrulama: http://localhost:8000/ready `{"status":"ready","database":"ok"}` döner; panelde "Selin (destek uzmanı) olarak giriş yap" butonu çalışır.

Her şeyi container'da çalıştırmak isterseniz: `docker compose up --build` (backend açılışta migration'ları uygular; seed için `docker compose exec backend python -m scripts.seed_demo`).

Postgres neden 5433? Geliştirme makinelerinde 5432 çoğunlukla yerel bir Postgres'e aittir. Değiştirmek için `.env` içinde `POSTGRES_HOST_PORT` ve URL'leri güncelleyin. Compose ilk açılışta iki veritabanı yaratır: `supportflow` (geliştirme) ve `supportflow_test` (testler).

## 2. Klasör yapısı

```
SupportFlow/
├── backend/
│   ├── app/
│   │   ├── api/            # router'lar (ince), auth bağımlılıkları, hata eşleme
│   │   ├── schemas/        # Pydantic API sözleşmeleri
│   │   ├── core/           # ayarlar (config.py), JWT, parola
│   │   ├── domain/         # saf Python: enum'lar, durum makineleri, NovaShop kuralları, hatalar
│   │   ├── services/       # kullanım senaryoları; transaction'ı sahiplenir
│   │   ├── integrations/   # mock sipariş sistemi (tek yazma yolu)
│   │   ├── agent/          # LangGraph grafı, prompt'lar, araçlar, LLM adaptörleri
│   │   ├── db/             # SQLAlchemy modelleri ve oturum
│   │   └── demo/           # seed verisi ve demo hareketleri
│   ├── alembic/            # migration'lar
│   ├── evals/              # eval çalıştırıcı (senaryolar kökteki evals/ altında)
│   ├── scripts/            # seed_demo.py, check_docs.py
│   └── tests/              # unit/ (DB'siz) ve integration/ (gerçek Postgres)
├── frontend/src/
│   ├── api/                # client.ts (tüm HTTP), queries.ts (hook'lar), üretilmiş tipler
│   ├── pages/  components/ # ekranlar ve parçaları
│   ├── lib/format.ts       # personelin gördüğü etiketler ve tarih biçimleri
│   └── styles/             # token'lar ve bileşen stilleri
├── evals/scenarios.jsonl   # senaryo eval'leri (veri)
├── docs/                   # bu dokümanlar
└── compose.yaml
```

Katmanlar arası bağımlılık kuralları (ör. `domain/` hiçbir şeyi import etmez, `agent/` yürütücüyü import edemez) [ARCHITECTURE §2](ARCHITECTURE.md#2-backend-modülleri-ve-bağımlılık-kuralları)'de; bazıları testlerle zorunludur.

## 3. Günlük komutlar

Backend komutları `backend/` içinde çalışır.

| Ne | Komut |
|---|---|
| CI'ın çalıştırdığı her şey (lint, format, tip, test, doküman kontrolü) | `uv run poe check` |
| Testler | `uv run poe test` |
| Tek test | `uv run pytest tests/integration/test_tickets.py::test_list_filters_and_paginates` |
| Docker olmadan (yalnızca birim testleri) | `uv run pytest -m "not db"` |
| Formatla | `uv run poe format` |
| Senaryo eval'leri | `uv run poe eval` (sahte model) · `uv run poe eval --live` (Gemini, kota kullanır) |
| Doküman kontrolü | `uv run poe docs` |
| Demo verisini sıfırla | `uv run poe seed --reset` (`--no-activity`: analiz edilmiş talepler olmadan) |
| Frontend kontrolleri (`frontend/`) | `npm run lint` · `npm run typecheck` · `npm test` · `npm run build` |
| API tiplerini yeniden üret (backend çalışırken) | `npm run gen:api` |

## 4. Testler

- **Birim testleri** (`tests/unit/`): veritabanı yok. Domain kuralları, graf düğümleri (`InMemoryTools` ile), LLM katmanı, sahte model.
- **Entegrasyon testleri** (`tests/integration/`): gerçek Postgres (`TEST_DATABASE_URL`). Her test tek bir transaction içinde çalışır ve sonunda geri alınır; test oturumu başında migration'lar baştan uygulanır. Bu testler otomatik olarak `db` ile işaretlenir.
- **Hiçbir test ücretli API çağırmaz.** Analiz testleri varsayılan olarak `FakeLLMClient` kullanır; belirli bir model çıktısı gerektiğinde `tests.fakes.ScriptedLLMClient(intent_output(...), draft_output(...))`.
- Test verisi `tests/factories.py` ile (`make_customer`, `make_order`, `make_ticket`…), kimlik doğrulama `admin`/`agent` fixture'ları ve `auth_headers(user)` ile.
- **Frontend**: Vitest + Testing Library; `src/test/utils.tsx` içindeki `mockApi` fetch'i taklit eder.

Hangi gereksinimin hangi testle kanıtlandığı [TEST_PLAN](TEST_PLAN.md)'da.

## 5. Sık yapılan işler

Her tarifin sonunda [Ne değişince ne güncellenir](README.md#ne-değişince-ne-güncellenir) tablosuna bakın.

### Yeni bir API uç noktası

1. Şemayı `app/schemas/` altına ekleyin.
2. İş mantığını servise (`app/services/`) yazın; servis domain hatası fırlatır (`NotFoundError`, `ConflictError`, `BusinessRuleViolationError`, `ForbiddenError`), `HTTPException` fırlatmaz. Hatalar `app/api/errors.py` tarafından 404/409/422/403'e çevrilir.
3. Router'ı `app/api/v1/` altına ekleyin. Her uç nokta `StaffUser`, `AdminUser` ya da `CurrentUser` bağımlılıklarından birini almalı.
4. Entegrasyon testi yazın (yetkisiz rol, bulunamadı, mutlu yol).
5. [API](API.md)'ye uç nokta başlığını ve örneği ekleyin; `uv run poe docs` eksik başlığı yakalar.
6. Frontend kullanacaksa backend çalışırken `npm run gen:api` ve hook'u `src/api/queries.ts`'e ekleyin.

### Yeni bir veritabanı alanı ya da tablo

1. Modeli `app/db/models/` altında değiştirin (yeni modül ise `alembic/env.py`'ye import edin).
2. `uv run alembic revision --autogenerate -m "add refund note"` ve oluşan dosyayı gözden geçirin.
3. Enum alanları yerel PostgreSQL enum'ı değil, `app.db.types.str_enum` (VARCHAR + CHECK) kullanır ([ADR-010](DECISIONS.md#adr-010-kalıcılık-kuralları)).
4. `uv run poe migrate`; `tests/integration/test_migrations.py` upgrade/downgrade'in döndüğünü doğrular.

### NovaShop kuralını değiştirmek

Kurallar `app/domain/policies.py` içinde saf fonksiyonlardır ve şimdiki zamanı parametre olarak alır (`datetime.now()` çağrılmaz). Değişikliği `tests/unit/test_policies.py` ile test edin ve [REQUIREMENTS §4](REQUIREMENTS.md#4-demo-alanı-novashop)'ü güncelleyin. Kural gerekçeleri müşteriye giden taslaklarda da görünür; Türkçe ve müşteriye uygun yazın.

### Prompt'u değiştirmek

1. `app/agent/prompts.py` içindeki metni değiştirin ve `PROMPT_VERSION`'ı artırın (her çalıştırma bu sürümü kaydeder).
2. `uv run poe eval` (sahte model) geçmeli. Mümkünse `uv run poe eval --live` ile gerçek modeli ölçün ve sonucu [TEST_PLAN](TEST_PLAN.md#senaryo-evalleri) canlı sonuç tablosuna yeni satır olarak yazın.

### Yeni bir ajan aracı

Araçlar salt okunur ve talebin müşterisiyle sınırlıdır. Ekleme: `ALLOWED_TOOLS` + `DatabaseTools` (`app/agent/tools.py`) + `tests.fakes.InMemoryTools`. Müşteri adına yapılan her sipariş sorgusu `OrderService.get_customer_order(customer_id, order_id)` üzerinden geçer.

### Yeni bir eval senaryosu

`evals/scenarios.jsonl`'a bir satır ekleyin (biçim: `backend/evals/runner.py` içindeki `Scenario` modeli). Talep metni Türkçe, sipariş kimlikleri dosya genelinde benzersiz olmalı. `uv run poe eval` ile çalıştırın; [TEST_PLAN](TEST_PLAN.md)'daki senaryo sayısını güncelleyin.

### Arayüz metni eklemek

Metinler Türkçe ve cümle düzeninde yazılır (yalnızca mühür büyük harf). Durum ve kategori etiketleri `src/lib/format.ts`'te tek yerde durur; yeni bir terimse [Sözlük](GLOSSARY.md)'e ekleyin. Görsel kurallar [DESIGN](DESIGN.md)'da.

## 6. Kodlama kuralları (özet)

- **Dil:** Tanımlayıcılar, yorumlar ve commit mesajları İngilizce; kullanıcıya ve okuyucuya görünen metinler Türkçe.
- **Kararlar kodda, model yalnızca anlatır:** Kapsamdaki sipariş, kural sonucu, önerilecek aksiyon ve kanıt doğrulaması saf koddur ([ADR-011](DECISIONS.md#adr-011-kararları-kodun-verdiği-modeli-iki-kez-çağıran-analiz-grafiği)).
- **Tek yazma yolu:** Siparişler yalnızca `app/integrations/mock_orders.py` üzerinden, yalnızca bir onaydan sonra değişir ([ADR-002](DECISIONS.md#adr-002-llm-yazma-işlemi-yapamaz)).
- **Her öneri geçişi** `ProposalService._move` üzerinden yapılır ve aynı transaction'da bir talep olayı ve bir denetim kaydı yazar.
- Python: Ruff (lint + format, satır 100), Pyright (standard). TypeScript: oxlint, `tsc`.
- Commit ve PR kuralları: [CONTRIBUTING](../CONTRIBUTING.md).

## 7. Geliştirme sırasında sorun giderme

| Belirti | Neden ve çözüm |
|---|---|
| `connection refused ... 5433` | Postgres çalışmıyor: `docker compose up -d db`. Port başka bir süreçteyse `.env`'deki `POSTGRES_HOST_PORT`'u değiştirin |
| `database "supportflow_test" does not exist` | Volume, init betiğinden önce oluşturulmuş: `docker compose down -v && docker compose up -d db` (yerel demo verisi silinir) |
| Git Bash'te `docker: command not found` | Docker komutlarını PowerShell'den çalıştırın |
| Panel "Sunucuya ulaşılamıyor" diyor | Backend çalışmıyor ya da 8000 portu dolu; Vite `/api` isteklerini oraya yönlendirir |
| Frontend tipleri backend ile uyuşmuyor | Backend çalışırken `npm run gen:api` |
| Ruff `RUF001` Türkçe karakter uyarısı | Noktasız `ı` izinli; başka bir karakterse gerçekten yanlış yazılmış olabilir |
| Analiz `llm_rate_limited` ile bitiyor | Canlı modelin ücretsiz kotası; bkz. [OPERATIONS](OPERATIONS.md#analiz-llm_rate_limited-ya-da-llm_timeout-ile-bitiyor) |
