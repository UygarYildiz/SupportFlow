# Mimari Karar Kayıtları (ADR)

Her kayıt şunları içerir: karar, gerekçe, alternatifler ve kararın ne zaman yeniden değerlendirileceği.

## ADR-001: Modüler monolit

**Karar:** Tek bir FastAPI uygulaması; `domain`, `services`, `agent`, `integrations` ve `api` modülleri ayrı ve aralarındaki bağımlılık kuralları zorunlu (bkz. [ARCHITECTURE.md](ARCHITECTURE.md)).
**Gerekçe:** Tek geliştirici için operasyonel karmaşıklığı düşük tutar; ileride ayrılabilecek net sınırları korur.
**Alternatifler:** Mikroservisler (reddedildi: bugün hiçbir faydası olmayan dağıtım ve tutarlılık yükü).
**Yeniden değerlendir:** Bileşenlerin bağımsız ölçeklenmesi gerekirse ya da farklı ekipler sahiplenirse.

## ADR-002: LLM yazma işlemi yapamaz

**Karar:** Ajan yalnızca `ActionProposal` (aksiyon önerisi) kaydı oluşturur. Değişiklikleri, onaylayanın rolünü, kuralı ve güncel durumu doğruladıktan sonra deterministik bir `ActionExecutor` uygular.
**Gerekçe:** Yetkisiz, tekrarlanan ya da halüsinasyona dayanan değişiklikleri önler. Ajanın bir şey istemesi asla yetki anlamına gelmez.
**Alternatifler:** Modelin yazma araçlarını doğrudan çağırması (reddedildi).

## ADR-003: Önce REST ve servis arayüzleri, MCP sonra

**Karar:** Domain servisleri Python arayüzleri ve REST uç noktaları üzerinden geliştirilir ve test edilir. MCP (Faz 8) daha sonra aynı servislerin üzerine salt okunur bir adaptör olarak eklenir.
**Gerekçe:** Araç protokolünün iş mantığına sızmasını engeller; çekirdek MCP olmadan da çalışır.

## ADR-004: psycopg 3 ile senkron SQLAlchemy

**Karar:** MVP, psycopg 3 sürücüsüyle senkron SQLAlchemy 2 ve Alembic migration'ları kullanır.
**Gerekçe:** Hata ayıklaması ve test etmesi daha kolay; trafik düşük. psycopg 3 aynı zamanda, ileride gerekirse LangGraph'ın Postgres checkpointer'ının kullandığı sürücü.
**Alternatifler:** asyncpg ile tamamen asenkron bir yığın.
**Yeniden değerlendir:** Ölçülebilir eşzamanlılık sorunları ortaya çıkarsa.

## ADR-005: Analiz çalıştırmaları kalıcı arka plan işleridir

**Karar:** `POST /tickets/{id}/analyze`, `queued` durumunda bir `agent_runs` satırı ekler ve çalıştırma kimliğiyle birlikte `202` döner. İşi, süreç içi (in-process) bir worker yürütür. Kısmi benzersiz indeks, bir talep için aynı anda yalnızca bir aktif çalıştırmaya izin verir. Uygulama açılırken `running` durumunda kalmış çalıştırmalar `interrupted` gerekçesiyle `failed` olarak işaretlenir.
**Gerekçe:** LLM gecikmesini HTTP isteğinin dışında tutar ve ek altyapı gerektirmez.
**Alternatifler:** Senkron istek (reddedildi: zaman aşımları, kötü kullanıcı deneyimi); Redis ile Celery/RQ (V2'ye ertelendi).
**Yeniden değerlendir:** Yük ayrı worker süreçleri gerektirirse ya da çalıştırmaların yeniden başlatmalardan sağ çıkması gerekirse.

## ADR-006: Onay ve yürütme ajan grafiğinin dışında gerçekleşir

**Karar:** Graf `pending` (bekleyen) bir öneri kaydeder ve biter. Karar uç noktası domain katmanındaki `ActionExecutor`'ı çağırır. Bekleyen onaylar bir graf checkpoint'inde değil, iş veritabanında saklanır.
**Gerekçe:** Onaydan sonra hiçbir graf düğümü yeniden çalışmaz; böylece yan etkilerin tekrarlanması tasarım gereği imkânsızdır. Bekleyen onaylar yeniden başlatmalardan etkilenmez ve yürütücü ajandan bağımsız test edilebilir.
**Alternatifler:** Postgres checkpointer ile LangGraph `interrupt()` ve onaydan sonra kaldığı yerden devam (V2'ye ertelendi).
**Yeniden değerlendir:** Ajanın bir insan kararından sonra çok adımlı işe devam etmesi gerekirse.

## ADR-007: Faz 2'den itibaren demo kimlik doğrulaması

**Karar:** Seed ile oluşturulan kullanıcılar, kısa ömürlü JWT'ler ve `/health` ile `/ready` dışındaki her uç noktada `get_current_user` / `require_role` FastAPI bağımlılıkları. Roller: `agent_user` (destek uzmanı) ve `admin` (yönetici). Aksiyon tipine göre onaylayıcı roller `domain/` içinde tanımlıdır.
**Gerekçe:** Onay ve veri erişim kuralları en baştan test edilebilir; kimlik doğrulamayı sonradan eklemek servisleri yeniden yazmak demek olurdu.
**Alternatifler:** Harici kimlik sağlayıcı (üretim için gerekli, demo kapsamı dışında).

## ADR-008: Talep ve öneri durumları ayrıdır

**Karar:** `approved` / `rejected` yalnızca öneri durumlarıdır. Talebin kendi yaşam döngüsü vardır ve bir talebin birden çok önerisi olabilir.
**Gerekçe:** İki yaşam döngüsünü tek bir durum alanında karıştırmak tutarsız durumlara yol açar.

## ADR-009: LLM sağlayıcısı olarak Gemini API

**Karar:** Gemini API, Google'ın resmî `google-genai` Python SDK'sı üzerinden ve bir `LLMClient` arayüzünün arkasında kullanılır (`generate_structured`, zaman aşımı, yeniden deneme, token kullanımı). Yapılandırılmış çıktı, Pydantic modellerinden türetilen bir JSON şemasıyla alınır ve her yanıt yine de Pydantic ile doğrulanır. Model adı yapılandırmadır (`GEMINI_MODEL`). Faz 3'ten itibaren `-latest` takma adı yerine belirli bir sürüm sabitlenir; böylece model testlerin ve eval'lerin altından değişmez. Varsayılan: `gemini-3.5-flash-lite`. 2026-11-02'de `gemini-3.8-flash`'in ücretsiz kotası birkaç düzine çağrıdan sonra doldu (HTTP 429) ve eski modeller yeni kullanıcılara 404 döndü; lite model geliştirmeyi ücretsiz kota içinde tutar. Model değiştirmek yalnızca bir yapılandırma değişikliğidir. `LLM_MODE=fake`, testler, CI ve herkese açık demo için deterministik bir `FakeLLMClient` kullanır.
**Gerekçe:** Yerleşik yapılandırılmış çıktı desteği, geliştirmeye uygun bir ücretsiz katman ve tek sağlayıcının adaptörü sade tutması.
**Sonuçlar:** Ücretsiz katman koşulları sağlayıcının gönderilen veriyi kullanmasına izin verebilir; bu yalnızca tüm veri sentetik olduğu için kabul edilebilir. Gerçek müşteri verisi asla gönderilmez. API anahtarı yalnızca sunucu tarafındaki ortam değişkenlerinde bulunur.
**Alternatifler:** `LLMClient` uygulanarak başka sağlayıcılar da eklenebilir; hiçbir domain ya da route kodu SDK'ya bağımlı değildir.

## ADR-010: Kalıcılık kuralları

**Karar:**
- Müşteriler ve siparişler (mock) dış sistemin metin kimliklerini korur (`CUS-0001`, `ORD-1001`). Bu sistemin sahip olduğu talepler ve kullanıcılar tamsayı identity anahtarları kullanır.
- Durum enum'ları yerel PostgreSQL enum'ı olarak değil, `CHECK` kısıtlı `VARCHAR` olarak saklanır.
- Bir talebin siparişi, talebin müşterisine ait olmalıdır. Bunu servis kontrol eder; ayrıca `(order_id, customer_id) → orders(id, customer_id)` bileşik yabancı anahtarı veritabanı düzeyinde de zorunlu kılar.
- İş birimini (unit of work) servisler yönetir ve commit eder; route handler'lar oturuma doğrudan dokunmaz.
- Zaman damgaları saat dilimi bilgili UTC'dir.

**Gerekçe:** Okunabilir dış kimlikler, müşterilerin ve LLM'in atıf yapacağı şeydir ("ORD-1001"). `CHECK` kısıtları, değer eklendiğinde `ALTER TYPE` migration'ı gerektirmeden bütünlüğü korur. Sahiplik bir güvenlik kuralıdır; bu yüzden uygulama koduna ek olarak veritabanı düzeyinde de güvence altındadır.
**Alternatifler:** Her yerde UUID (demolarda ve prompt'larda daha az okunur); yerel enum'lar (geliştirmesi daha zor).

## ADR-011: Kararları kodun verdiği, modeli iki kez çağıran analiz grafiği

**Karar:** Analiz, dokuz düğümlü bir LangGraph durum grafiğidir (`app/agent/graph.py`). Yalnızca ikisi modeli çağırır: `classify` (niyet, atıf yapılan sipariş, istenen adres) ve `draft` (özet ve yanıt). Karar veren her şey düz koddur:
- hangi siparişin kapsamda olduğu (modelin sipariş atfı yalnızca müşteri o kimliği gerçekten yazdıysa kullanılır);
- hangi kategoriye hangi kuralın uygulandığı ve sonucu (`PolicyService`);
- bir aksiyonun önerilip önerilemeyeceği (`plan_action`: kural izin vermeli; mesaj sisteme yönelik talimatlar içeriyorsa asla);
- atıf yapılan kanıtlardan hangilerinin geçerli olduğu (`assemble_result`).

Araçlar, talebin veritabanındaki müşterisine bağlanmış açık bir izin listesidir (`get_order`, `get_customer_orders`, `get_customer_tickets`, `get_policy`). Araçları model seçmez; düğümler çağırır. Her düğüm `agent_run_steps` tablosuna kaydedilir (süre, kısa özet, araç çağrıları). Sınırlar: graf adım sınırı, çalıştırma başına token bütçesi, çalıştırma süre sınırı. Checkpointer kullanılmaz (ADR-006).

**Gerekçe:** Bir model çağrısı yanılabilir, kandırılabilir ya da erişilemez olabilir. Modeli sınıflandırma ve metin yazımıyla sınırlamak, sonuç doğuran her kararı modelsiz test edilebilir, arayüzde açıklanabilir ve sağlayıcıdan bağımsız kılar. İki odaklı çağrı, tek büyük bir prompt'tan ya da serbest araç kullanımından daha ucuz ve daha kolay doğrulanır.
**Alternatifler:** Her şeyi yapan tek bir prompt (Faz 3; kontrol etmesi ve açıklaması daha zor); kendi araçlarını seçen ReAct tarzı bir ajan (daha esnek ama yetkilendirmeyi ve determinizmi garanti etmek zorlaşır; V2'deki salt okunur araştırma görevleri için yeniden düşünülebilir).

## ADR-012: Idempotent yürütücü ile iki adımlı onay

**Karar:** Bir aksiyon öneren analiz, çalıştırmayı tamamlayan transaction içinde `pending` bir `ActionProposal` kaydeder. Ardından `POST /proposals/{id}/decision` commit edilen iki adımda çalışır:
1. **Karar:** öneri kilitlenir; onaylayanın rolü, `expected_version`, durum, son kullanma zamanı ve içerik parmak izi kontrol edilir; karar kaydedilir (`approved`) ve `executing` durumuna geçilir.
2. **Yürütme:** (mock) sipariş sistemi aksiyonu `proposal-{id}` idempotency anahtarıyla uygular. Önce siparişi kilitler ve kuralı yeniden kontrol eder (TOCTOU), sonra değişikliği ve tek bir `action_executions` satırını yazar. Öneri `executed` ya da `failed` olarak biter.

Süreç iki adım arasında çökerse, açılıştaki kurtarma 2. adımı yeniden çalıştırır; idempotency anahtarı bunu güvenli kılar. Bekleyen öneriler 48 saat sonra süresi dolar ve asla yürütülmez; yeni bir analiz eski bekleyen önerilerin yerini alır (talep başına tek açık öneri, kısmi benzersiz indeksle zorunlu). Her geçiş bir talep olayı ve bir denetim kaydı yazar (veritabanı trigger'ı ile yalnızca eklemeli, kişisel veriler maskelenmiş).

**Gerekçe:** Kararı aksiyondan önce kaydetmek, yürütme başarısız olsa bile kalıcı bir iz bırakır ve "bir insan evet dedi" ile "sistem bunu yaptı"yı birbirinden ayırır. Sürüm kontrolleri ve idempotency anahtarları çift tıklamaları, eşzamanlı inceleyenleri ve yeniden denemeleri zararsız kılar. Yürütme anında yeniden kontrol, öneriden sonra değişen koşullara karşı korur.
**Alternatifler:** Karar ve yürütme için tek transaction (daha basit, ama yürütmesi başarısız olan onayların kaydı kalmaz ve gerçek dış sistemlere taşınamaz); grafı LangGraph `interrupt()` ile kaldığı yerden sürdürmek (ADR-006).
**Yeniden değerlendir:** Gerçek bir dış sistem entegre edildiğinde: `unknown` sonucu eklenmeli ve rollback'in "hiçbir şey olmadı" anlamına geldiği varsayılmak yerine o sistemin idempotency API'si üzerinden mutabakat yapılmalı.

## ADR-013: Frontend yığını ve API sözleşmesi

**Karar:** React Router ve TanStack Query ile React + TypeScript + Vite. Stiller Tailwind yerine tasarım token'ları üzerine düz CSS'tir (`frontend/src/styles/tokens.css`, bkz. [DESIGN.md](DESIGN.md)). API tipleri backend'in OpenAPI şemasından üretilir (`npm run gen:api`, `src/api/schema.d.ts` olarak commit edilir); tüm HTTP trafiği `src/api/client.ts` ve `src/api/queries.ts` içindeki hook'lar üzerinden geçer. Fontlar Fontsource ile projeyle birlikte sunulur (üçüncü taraf font CDN'i yok).
**Gerekçe:** Arayüzün bilinçli bir görsel dili var (etiketler, karbon kâğıdı taslaklar, mühürler); bunu utility class'larla değil, isimlendirilmiş token'lar ve bileşen stilleriyle ifade etmek ve incelemek daha kolay. Üretilen tipler API değiştiğinde frontend'i dürüst tutar; TanStack Query çalıştırmaları yoklamayı, kararlardan sonra yeniden veri çekmeyi ve 409 sonrası bayat veriyi yönetir.
**Alternatifler:** Tailwind (başta planlanmıştı; hız için iyi, özgün bir görsel sistem için zayıf); elle yazılmış API tipleri (sessizce uyumsuzlaşır).
**Notlar:** `openapi-typescript` TypeScript 5 gerektiriyor, uygulama ise TypeScript 7 kullanıyor; bu yüzden proje bağımlılığı olarak değil, üretim anında `npx` ile çalıştırılır.

## ADR-014: Politika bilgi tabanı: pgvector, madde bazlı parçalar, kararlar kodda kalır

**Karar:** NovaShop politikaları `backend/knowledge/policies/` altında sürümlü Türkçe markdown dokümanları olarak tutulur (ön bilgi: `id`, `title`, `version`, `effective_from`). Her `## KİMLİK başlık` bölümü bir maddedir (ör. `IADE-2`) ve hem arama hem kaynak gösterme birimidir. İndeksleme (`uv run poe ingest`) maddeleri embedding'e çevirip PostgreSQL'de pgvector ile saklar (`policy_documents`, `policy_chunks`, `ingestion_jobs`; HNSW, kosinüs mesafesi, 768 boyut).
- **Sürümleme:** Doküman `(id, version)` ve içerik hash'iyle tanınır. Aynı içerik yeniden indekslenince hiçbir şey değişmez; `version` yükseltilen doküman eskisinin yerini alır (eski sürüm iz için saklanır, aranmaz; kısmi benzersiz indeks politika başına tek güncel sürüm garanti eder); sürümü yükseltilmeden değiştirilmiş doküman reddedilir, böylece bir alıntı her zaman o sürümle indekslenen metni gösterir.
- **Embedding:** Canlıda `gemini-embedding-2` (doküman ve sorgu için ayrı görev tipleri, 768 boyut); testlerde, CI'da ve demoda deterministik, çevrimdışı bir sahte embedder (Türkçe kelime kökleri üzerinde feature hashing). Her vektör üreten modelin adıyla saklanır ve yalnızca aynı modelin vektörleriyle karşılaştırılır; model değişince yeniden indeksleme yeni satırlar ekler.
- **Katmanlar:** Ayrıştırma saf domain kodudur (`app/domain/policy_documents.py`). İndeksleme ve arama servis katmanındadır (`app/services/policy_knowledge.py`) ve embedder'ı dışarıdan alır; sağlayıcı SDK'sını yalnızca `app/agent/llm/gemini.py` import eder.
- **Kararlar:** Dokümanlar kural *kararı vermez*. İade süresi, adres değişikliği gibi kararlar `app/domain/policies.py`'de kalır (ADR-011); dokümanlar yalnızca o kararın hangi maddeye dayandığını kaynağıyla gösterir. Dokümanlardaki süreler koddakilerle bir testle eşlenir.

**Gerekçe:** Kaynak gösteren açıklama personelin kararı doğrulamasını kolaylaştırır ve "model kuralı uydurdu" riskini azaltır; ama bir dokümandaki cümlenin (ya da dokümana gizlenmiş bir talimatın) yetki vermesi kabul edilemez. Madde bazlı parçalar doğal kaynak gösterme birimidir ve küçük bir bilgi tabanında sabit boyutlu parçalamadan daha anlamlı sonuç verir. pgvector, ayrı bir vektör veritabanı işletmeden aynı transaction ve yedekleme düzeninde kalmayı sağlar.
**Alternatifler:** Ayrı bir vektör veritabanı (Qdrant, Pinecone; bu ölçekte gereksiz operasyon yükü); sabit boyutlu parçalama (madde sınırlarını böler, kaynak gösterimini bulanıklaştırır); dokümanların karar vermesi (reddedildi: yetki ve determinizm kaybolur); yalnızca anahtar kelime araması (Türkçe çekim ekleri ve eş anlamlılarla zayıf; gerekirse hibrit arama eklenebilir).
**Yeniden değerlendir:** Bilgi tabanı yüzlerce dokümana çıkarsa (hibrit arama, yeniden sıralama), politikalar kullanıcı tarafından yüklenirse (erişim kontrolü, içerik denetimi) ya da çok dilli destek gerekirse.

## ADR-015: Salt okunur MCP adaptörü: stdio + süreç içi bağlantı, kimlik bağlantıdan gelir

**Karar:** SupportFlow, sipariş ve talep geçmişi sorgularını üç salt okunur MCP aracı olarak sunar (`get_order_status`, `get_customer_orders`, `get_ticket_history`; resmî Python SDK, `mcp` 2.x). Sunucu `app/mcp/` içinde, `SupportLookupService` üzerinde ince bir adaptördür: iş kuralı eklemez, yazma yolu yoktur (import sınırı testle korunur), her aracın `readOnlyHint` işareti ve şemayla doğrulanan yapılandırılmış çıktısı vardır.
- **Taşıma:** Dış istemciler için **stdio** (`uv run poe mcp`): sunucu, istemcinin başlattığı yerel bir süreçtir ve ağa port açmaz. Ajan için **süreç içi** bağlantı: aynı JSON-RPC mesajları ve şemalar, ağ yok, çalıştırmanın veritabanı oturumu. HTTP (Streamable HTTP) taşıma bu fazda **yoktur**.
- **Kimlik:** Kimlik araç parametresinden türetilmez, bağlantıdan gelir. stdio'da `MCP_ACCESS_TOKEN` içindeki personel JWT'si her çağrıda doğrulanır ve kullanıcı veritabanından yeniden okunur (süresi dolmuş token ya da pasif kullanıcı anında reddedilir). Ajan bağlantısının kimliği çalıştırmadır ve yalnızca analiz ettiği talebi okuyabilir. `ticket_id` neyin okunacağını söyler; müşteri her zaman talep satırından gelir, başka müşterinin siparişi olmayan bir siparişle aynı yanıtı alır.
- **Hata sözlüğü:** `[unauthorized]`, `[forbidden]`, `[not_found]`, `[internal_error]` ön ekli araç hataları; şemaya uymayan argümanları SDK reddeder. Beklenmeyen bir hatanın ayrıntısı istemciye gitmez, sunucu log'una yazılır. Ajan `not_found`'ı "sipariş yok" olarak, diğerlerini analizi durduran `tool_error` / `tool_timeout` olarak ele alır; böylece reddedilmiş bir sorgu "siparişi yok" diye yanlış bir taslağa dönüşmez.
- **Kapsam:** Kural kontrolü (`get_policy`) ve politika araması (`search_policies`) doğrudan çağrı olarak kalır: bunlar müşteri verisi değil, deterministik kural kodu ve ortak bilgi tabanıdır. `AGENT_TOOL_TRANSPORT=direct` tüm araçları doğrudan çağıran geri dönüş yoludur.

**Gerekçe:** MCP'nin değeri, aynı yetkili operasyonların standart bir arayüzle hem ajana hem dış araçlara açılmasıdır; ama MCP kendi başına yetki sağlamaz. Kimliği bağlantıya bağlamak, modelin ya da istemcinin bir parametreyle yetkisini genişletmesini engeller. Ajanın da MCP üzerinden okuması adaptörü her analizde gerçekten çalıştırır (yan yol değil, ana yol). stdio, yerel geliştirme ve demo için ağ yüzeyi ve OAuth altyapısı gerektirmeyen en dar seçenektir.
**Alternatifler:** Streamable HTTP + OAuth 2.1 (MCP yetkilendirme spesifikasyonu; uzaktan istemciler için gerekli ama bir yetkilendirme sunucusu, token audience doğrulaması ve origin kontrolü ister: canlı yayın fazına bırakıldı); araçların `customer_id` alması (reddedildi: yetki parametreden türetilirdi); ajanın servisleri doğrudan çağırmaya devam etmesi ve MCP'nin yalnızca dışa açılması (adaptör ana yolda sınanmazdı; geri dönüş olarak korundu); yazma araçları (reddedildi: tüm yazmalar onaylı yürütücüden geçer, ADR-002).
**Yeniden değerlendir:** Uzaktan bir MCP istemcisi gerektiğinde (HTTP + OAuth, kısa ömürlü ve audience'lı token), personel başına araç izinleri gerektiğinde ya da ajanın sunucuyu ayrı bir süreçte çalıştırması gerektiğinde.

## ADR-016: Canlı demo: Cloudflare Pages + Render + Supabase (ücretsiz katmanlar)

**Karar:** Herkese açık demo üç ücretsiz katmanda çalışır: React paneli **Cloudflare Pages**'te (statik, `*.pages.dev`), FastAPI backend'i **Render**'ın ücretsiz Docker web servisinde (Frankfurt, tek kopya, `*.onrender.com`), PostgreSQL + pgvector **Supabase**'in ücretsiz projesinde (Frankfurt, `eu-central-1`).
- **Veritabanı yalıtımı:** Uygulama Supabase'in `postgres` kullanıcısıyla değil, yalnızca kendi `supportflow` şemasının sahibi olan, süper yetkisiz `supportflow_app` rolüyle bağlanır (`search_path = supportflow, extensions`, `statement_timeout = 30s`). Supabase'in REST API'sinin (Data API) gördüğü `anon` ve `authenticated` rollerinin bu şemaya erişimi yoktur, `public` şemasında tablo yoktur; tablolar Data API'den okunamaz. Bağlantı Supavisor **session pooler** (IPv4, port 5432) üzerinden kurulur; ücretsiz planda doğrudan bağlantı yalnızca IPv6'dır.
- **Yayın:** Render her `main` push'unda imajı derler; açılışta `alembic upgrade head` çalışır. Pages her push'ta `frontend/`'i `VITE_API_BASE_URL` ile derler. Backend yalnızca `CORS_ALLOW_ORIGINS`'teki kaynağa CORS izni verir (çerez yok, bearer token).
- **Model ve veri:** Demo `LLM_MODE=fake` ve `EMBEDDING_MODE=fake` ile çalışır (maliyet ve kota riski yok). Demo hesapları ve parolası bilerek herkese açıktır; veri sentetiktir ve bir GitHub Actions iş akışıyla her gece sıfırlanır (bu, ücretsiz Supabase projesinin hareketsizlikten duraklatılmasını da önler).

**Gerekçe:** Üçü de kredi kartı istemeden çalışır ve mevcut Dockerfile ile Compose düzenini değiştirmeden kullanılır. Render, süreç içi worker'ın (ADR-005) ihtiyacı olan tek, yanıt sonrası da çalışmayı sürdüren bir süreç sağlar. Supabase pgvector'ı hazır sunar (ADR-014).
**Alternatifler:** Google Cloud Run (kart ister; varsayılan modda yanıt sonrası CPU'yu kıstığı için arka plan analizlerini bozar); Hugging Face Spaces (daha fazla bellek, ama API barındırma için alışılmış değil); Render Postgres (ücretsiz veritabanı 30 gün sonra silinir); Fly.io ve Railway (yeni hesaplar için kalıcı ücretsiz katman yok); frontend'i Render static site olarak yayınlamak (mümkün, ama Pages uyumaz ve CDN'i daha geniştir).
**Bedeli:** Render ücretsiz servisi 15 dakika istek almazsa uyur; ilk istek 30–60 saniye sürebilir. Uyku sırasında yarım kalan analiz açılışta `interrupted` olarak işaretlenir (ADR-005). Supabase ücretsiz projesi 500 MB ile sınırlıdır.
**Yeniden değerlendir:** Demo gerçek kullanıcı ya da gerçek model (`LLM_MODE=live`) alırsa, soğuk başlatma gösterimi bozarsa ya da ayrı bir worker gerekirse.
