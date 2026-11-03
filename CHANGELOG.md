# Değişiklik kaydı

Bu projedeki kullanıcıya görünen değişiklikler bu dosyada tutulur. Biçim [Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/), sürümleme [Anlamsal Sürümleme](https://semver.org/lang/tr/) kurallarını izler. Yeni değişiklikler "Yayınlanmamış" bölümüne eklenir; sürüm çıkarken bu bölüm sürüm numarası ve tarihle adlandırılır.

## [Yayınlanmamış]

### Eklendi

- **Kendi kurulumu (Blok D1, ADR-017):** SupportFlow bir işletmenin kendi bilgisayarında ya da sunucusunda, kendi verisiyle çalışabiliyor. `deploy/selfhost/` altında tek komutla kurulum (`init.sh` / `init.ps1` rastgele sırları üretir, `docker compose up -d --build`); panel nginx ile sunuluyor, veritabanı dışarı açılmıyor. Kılavuz: `docs/SELF_HOSTING.md`.
- **İlk açılış kurulumu:** boş bir kendi kurulum, giriş ekranı yerine kurulum sayfasını açıyor: işletme adı, ilk yönetici ve kurulum kodu. Kurulum bir kez yapılabiliyor. Yeni uç noktalar: `GET /api/v1/setup/status`, `POST /api/v1/setup`.
- **Ekip yönetimi:** yöneticiler "Ekip" sayfasından hesap ekliyor, rol değiştiriyor, pasifleştiriyor ve parola sıfırlıyor; herkes "Hesabım" sayfasından kendi parolasını değiştirebiliyor. Parola en az 12 karakter; kurulum hiçbir zaman yöneticisiz kalmıyor; her değişiklik denetim kaydında. Yeni uç noktalar: `POST /api/v1/users`, `PATCH /api/v1/users/{user_id}`, `POST /api/v1/auth/password`.
- **Kurulum modu:** `DEPLOYMENT_MODE=demo|self_hosted` ve `SETUP_TOKEN`. Kendi kurulumda demo verisi yüklenemiyor ve giriş ekranında demo hesabı görünmüyor; giriş ekranı işletmenin adını gösteriyor.
- **Canlı demo (Faz 11-B):** https://supportflow-w7q.pages.dev. Frontend Cloudflare Pages'te, backend Render'da, veritabanı Supabase'de (ücretsiz katmanlar). Backend yalnızca tanımlı frontend kaynağına CORS izni veriyor (`CORS_ALLOW_ORIGINS`); frontend backend adresini `VITE_API_BASE_URL`'den alıyor; demo verisi her gece sıfırlanıyor.
- **Salt okunur MCP araçları (Faz 8):** `get_order_status`, `get_customer_orders`, `get_ticket_history`; MCP Inspector ya da bir masaüstü asistanı stdio üzerinden personel token'ıyla bağlanabilir (`poe mcp`, `poe mcp-token`). Kimlik bağlantıdan gelir, müşteri talepten; başka müşterinin siparişi görünmez. Her çağrı `call_id` ile log'lanır, personel çağrıları denetim kaydına yazılır.
- **Ajan MCP üzerinden okuyor:** analiz, sipariş ve talep geçmişini aynı MCP sunucusundan alır (`AGENT_TOOL_TRANSPORT=mcp`, geri dönüş `direct`); "Bu öneri nasıl hazırlandı" listesi MCP çağrılarını "· MCP" ile işaretler. Yeni analiz hata kodları: `tool_timeout`, `tool_error`.
- **Kaynak gösteren taslaklar (Faz 7):** analiz, kural sonucunu açıklayan politika maddelerini getirir (`retrieve_policy`); taslak bu maddelere atıf yapar ("Dayanak: İade Politikası v1, IADE-2"), atıflar getirilen maddelerle doğrulanır, kaynak yoksa personele söylenir. Politika metni ve müşteri metni ayraçtan çıkamaz; dokümana gizlenmiş talimatlar hiçbir aksiyon üretmez.
- **Getirme kalitesi ölçümü:** 20 soruluk golden set ve `poe eval-rag` (hit@k, MRR); çevrimdışı sonuç CI'da taban değerle korunuyor. Yürürlük tarihi gelmemiş politika sürümüne dayanan analizler insan incelemesine gidiyor.
- **Panelde kaynaklar:** "Mağaza kuralı" kutusu kural sonucunun dayandığı politika maddesini gösterir (politika adı, sürüm, madde, açılır metin, yürürlük tarihi).
- **Politika bilgi tabanı (Faz 7, ilk dilim):** sürümlü Türkçe NovaShop politika dokümanları (teslimat, iade, hasarlı ürün, adres değişikliği, istisnalar); pgvector ile madde bazlı indeksleme (`poe ingest`), idempotent ve sürüm denetimli; yalnızca güncel sürümde arama. Canlıda Gemini embedding'leri, testlerde ücretsiz sahte embedder.

### Değişti

- Backend imajı `PORT` ortam değişkenine uyuyor (varsayılan 8000). Denetim trigger fonksiyonunun `search_path`'i sabitlendi (yeni migration).
- Veritabanı imajı `pgvector/pgvector:pg17` (yerel volume'un yeniden kurulması gerekir, bkz. Operasyon kılavuzu).

## [0.1.0] - 2026-11-03

İlk sürüm: insan onaylı yapay zekâ destek masasının MVP'si. Demo videosu sonraki bir sürümde README'ye eklenecek.

### Eklendi

- **Talepler ve siparişler:** talep oluşturma, listeleme (durum, öncelik, kategori filtreleri), detay ve izin verilen durum geçişleri; kurgusal NovaShop için mock müşteri ve sipariş sorgulama.
- **Demo kimlik doğrulaması:** seed ile oluşturulan kullanıcılar, kısa ömürlü JWT, iki rol (destek uzmanı, yönetici); `/health` ve `/ready` dışındaki her uç noktada yetki kontrolü.
- **Yapay zekâ analizi:** arka planda çalışan, adımları kaydedilen LangGraph analizi; talebi sınıflandırır, müşterinin siparişlerini ve mağaza kurallarını kontrol eder, Türkçe yanıt taslağı yazar. Gemini (canlı) ya da ücretsiz deterministik sahte model.
- **İnsan onayı:** adres değişikliği ve iade önerileri; rol bazlı onay (iadeler yalnızca yönetici), onay anında yeniden kontrol, iyimser kilitleme, idempotent yürütücü, 48 saatlik karar süresi, açılışta kurtarma.
- **Denetim kaydı:** yalnızca eklenebilir, kişisel verisi maskelenmiş, yalnızca yöneticinin okuyabildiği kayıt.
- **Operasyon paneli:** role göre genel bakış, talep listesi, talep detayı ("Bu öneri nasıl hazırlandı" adımlarıyla), onay kuyruğu; sevkiyat masası görsel dili ve karar mühürleri.
- **Kalite:** gerçek PostgreSQL üzerinde backend testleri, frontend bileşen testleri, S1–S6 ve P0 güvenlik senaryolarını kapsayan eval'ler; GitHub Actions CI.
- **Dokümantasyon:** gereksinimler, mimari, 13 karar kaydı, güvenlik, test planı, tasarım, API referansı, geliştirme ve operasyon kılavuzları, sözlük; dokümanların eskimesini yakalayan otomatik kontrol.

### Değişti

- Karar mührünün yazı boyutu kelime uzunluğuna göre ölçekleniyor; uzun Türkçe mühür kelimeleri (ENGELLENDİ, SÜRESİ DOLDU) kart metninin üstüne binmiyor.
- Proje Türk işverenlere sunulacağı için tüm dokümanlar, arayüz, hata mesajları, demo verisi ve eval senaryoları Türkçeye çevrildi; sahte model Türkçe mesajları anlıyor.

[Yayınlanmamış]: https://github.com/UygarYildiz/SupportFlow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/UygarYildiz/SupportFlow/releases/tag/v0.1.0
