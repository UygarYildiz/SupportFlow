# Sözlük

Kodda, arayüzde ve dokümanlarda aynı şeyi aynı kelimeyle anlatmak için. **Kod** sütunu veritabanında ve API'de görünen değerdir (değişmez, İngilizce); **Arayüz** sütunu personelin ekranda gördüğü metindir (`frontend/src/lib/format.ts`); dokümanlar da bu Türkçe karşılıkları kullanır.

## Temel kavramlar

| Kod | Türkçe terim | Anlamı |
|---|---|---|
| `ticket` | Talep | Müşterinin bir destek isteği: konu, mesaj, isteğe bağlı sipariş |
| `customer` | Müşteri | NovaShop müşterisi. Giriş yapmaz; talepleri API ile gelir |
| `order` | Sipariş | Mock sipariş sistemindeki bir sipariş (`ORD-1001`) |
| `agent_run`, run | Analiz çalıştırması | Bir talebin yapay zekâ ile bir kez analiz edilmesi; arka planda çalışır ([ADR-005](DECISIONS.md#adr-005-analiz-çalıştırmaları-kalıcı-arka-plan-işleridir)) |
| `agent_run_step` | Analiz adımı | Grafın bir düğümünün kaydı: süre, küçük özet, araç çağrıları |
| `ActionProposal`, proposal | Öneri (aksiyon önerisi) | Analizin önerdiği, insan onayı bekleyen sipariş değişikliği |
| `decision` | Karar | Önerinin onaylanması (`approve`) ya da reddedilmesi (`reject`) |
| `action_execution` | Yürütme kaydı | Onaylanan önerinin sipariş sistemine uygulanma sonucu; öneri başına en fazla bir tane |
| `refund_request` | İade talebi kaydı | Onaylanan iadenin oluşturduğu mock finans kaydı; para hareketi yoktur |
| `audit_log` | Denetim kaydı | Kim neyi ne zaman önerdi, onayladı, uyguladı; yalnızca eklenebilir, yalnızca yönetici okur |
| `ticket_event` | Talep olayı | Talebin zaman çizelgesindeki bir satır ("Geçmiş" bölümü) |
| `policy`, policy check | Mağaza kuralı, kural kontrolü | NovaShop kuralının (iade süresi, adres değişikliği…) bir siparişe uygulanması ([REQUIREMENTS §4](REQUIREMENTS.md#4-demo-alanı-novashop)) |
| draft reply | Taslak yanıt | Yapay zekânın müşteri için yazdığı, personelin inceleyip kopyaladığı yanıt; asla kendiliğinden gönderilmez |
| evidence | Kanıt (dayanak) | Taslağın dayandığı, backend tarafından doğrulanmış sipariş kimlikleri |
| policy document | Politika dokümanı | `backend/knowledge/policies/` altındaki sürümlü NovaShop politikası (ör. İade Politikası v1) |
| citation | Atıf (dayanak) | Taslağın dayandığı, getirilen maddelerle doğrulanmış politika maddesi (`cited_clause_ids`) |
| clause | Madde | Politika dokümanının kimlikli bir bölümü (`IADE-2`); arama ve kaynak gösterme birimi |
| `needs_human_review` | İnsan incelemesi gerekli | Talebin olağan dışı olduğu ya da bir kuralla çeliştiği işareti |
| `DEPLOYMENT_MODE=self_hosted` | Kendi kurulumu | Bir işletmenin SupportFlow'u kendi makinesinde, kendi verisiyle çalıştırması; bir kurulum = bir işletme ([ADR-017](DECISIONS.md#adr-017-gerçek-kullanım-için-tek-işletmelik-kendi-kurulumu-demo-sentetik-kalır)) |
| `DEPLOYMENT_MODE=demo` | Demo modu | Sentetik NovaShop verisi ve herkese açık demo hesaplarıyla çalışma (geliştirme, canlı demo) |
| `installation` | Kurulum kaydı | Kendi kurulumun işletme adı ve kurulumu yapan yönetici; en fazla bir satır |
| setup | İlk açılış kurulumu | Boş bir kendi kurulumda işletme adının ve ilk yöneticinin oluşturulması; bir kez yapılır |
| `SETUP_TOKEN` | Kurulum kodu | Kurulum sayfasının istediği tek seferlik kod; kurulumu başkasının sahiplenmesini önler |
| team | Ekip | Kurulumdaki çalışan hesapları; yönetici "Ekip" sayfasından yönetir |

## Roller

| Kod | Arayüz | Yetkisi |
|---|---|---|
| `agent_user` | Destek uzmanı | Talepleri ve siparişleri görür, analiz başlatır, adres değişikliklerini onaylar |
| `admin` | Yönetici | Destek uzmanının yaptığı her şey; ayrıca iadeleri onaylar, denetim kaydını görür ve ekibi yönetir |
| AI agent | Yapay zekâ ajanı | Kullanıcı değil; yalnızca salt okunur araçlar kullanır ve öneri oluşturur |

Ayrıntı: [REQUIREMENTS §3 Erişim modeli](REQUIREMENTS.md#3-erişim-modeli).

## Talep durumları (`TicketStatus`)

| Kod | Arayüz | Anlamı |
|---|---|---|
| `new` | Yeni | Henüz analiz edilmedi |
| `triaging` | Analiz ediliyor | Bir analiz çalıştırması kuyrukta ya da çalışıyor |
| `awaiting_review` | İncelemeye hazır | Analiz bitti; taslak ve varsa öneri personeli bekliyor |
| `needs_info` | Müşteriden bilgi bekleniyor | Sipariş numarası ya da yeni adres gibi bir bilgi eksik |
| `resolved` | Çözüldü | Personel talebi kapattı (son durum) |
| `failed` | Analiz başarısız | Analiz hata ile bitti; yeniden açılıp tekrar denenebilir |

Geçiş kuralları: [ARCHITECTURE §4](ARCHITECTURE.md#4-durum-makineleri).

## Öncelik (`TicketPriority`) ve kategori (`TicketCategory`)

| Kod | Arayüz |
|---|---|
| `low` / `medium` / `high` / `urgent` | Düşük / Orta / Yüksek / Acil |
| `delivery_delay` | Teslimat sorusu |
| `refund_request` | İade talebi |
| `address_change` | Adres değişikliği |
| `damaged_item` | Hasarlı ürün |
| `general` | Genel soru |
| `unknown` | Belirsiz talep (gerçek bir müşteri isteği yok ya da sisteme talimat vermeye çalışıyor) |

## Öneri durumları (`ProposalStatus`) ve aksiyon tipleri (`ActionType`)

| Kod | Arayüz | Mühür | Anlamı |
|---|---|---|---|
| `pending` | Karar bekliyor | | Onay ya da ret bekliyor; 48 saat sonra süresi dolar |
| `approved` | Onaylandı | | Karar kaydedildi, yürütme başlamak üzere (ara durum) |
| `executing` | Uygulanıyor | | Sipariş sistemine uygulanıyor (ara durum) |
| `executed` | Uygulandı | ONAYLANDI | Değişiklik siparişe bir kez uygulandı |
| `rejected` | Reddedildi | REDDEDİLDİ | Personel reddetti; hiçbir şey değişmedi |
| `failed` | Engellendi | ENGELLENDİ | Onay anındaki yeniden kontrol izin vermedi (ör. sipariş bu arada kargoya verildi) |
| `expired` | Süresi doldu | SÜRESİ DOLDU | Zamanında karar verilmedi; asla yürütülmez |

| Kod | Arayüz | Onaylayan |
|---|---|---|
| `change_shipping_address` | Teslimat adresini değiştir | Destek uzmanı ya da yönetici |
| `create_refund_request` | İade talebi oluştur | Yalnızca yönetici |

## Sipariş durumları (`OrderStatus`)

| Kod | Arayüz | Taslaklarda |
|---|---|---|
| `pending` | Beklemede | beklemede |
| `processing` | Hazırlanıyor | hazırlanıyor |
| `shipped` | Kargoda | kargoda |
| `delivered` | Teslim edildi | teslim edildi |
| `cancelled` | İptal edildi | iptal edildi |

## Analiz çalıştırması durumları ve hata kodları

Durumlar (`AgentRunStatus`): `queued` (kuyrukta) → `running` (çalışıyor) → `succeeded` (başarılı) ya da `failed` (başarısız).

| `error_code` | Anlamı |
|---|---|
| `invalid_output` | Model şemaya uymayan bir yanıt döndürdü |
| `llm_rate_limited` | Sağlayıcının istek ya da kota sınırına takıldı |
| `llm_timeout` | Model zamanında yanıt vermedi (yeniden denemelerden sonra) |
| `llm_unavailable` | Sağlayıcıya ulaşılamadı |
| `llm_request_failed`, `llm_error` | Sağlayıcı isteği reddetti ya da başka bir model hatası |
| `token_budget_exceeded` | Çalıştırma token bütçesini (`AGENT_MAX_TOKENS_PER_RUN`) aştı |
| `run_timeout` | Çalıştırma süre sınırını (`AGENT_RUN_TIMEOUT_SECONDS`) aştı |
| `step_limit_exceeded` | Graf adım sınırını aştı |
| `interrupted` | Sunucu çalıştırma sırasında yeniden başladı |
| `tool_timeout` | Bir MCP araç çağrısı süre sınırını (`MCP_TOOL_TIMEOUT_SECONDS`) aştı |
| `tool_error` | MCP aracı hata döndürdü (ör. `forbidden`, `internal_error`) ya da şemaya uymayan yanıt verdi |
| `ticket_missing`, `internal_error` | Beklenmeyen iç hata |

## Analiz grafiği düğümleri

| Düğüm | Arayüzdeki adım ("Bu öneri nasıl hazırlandı") |
|---|---|
| `load_ticket` | Talebi okudu |
| `resolve_orders` | Müşterinin siparişlerini kontrol etti |
| `classify` | Talebin türünü belirledi (model çağrısı) |
| `request_info` | Eksik bilgiyi not etti |
| `fetch_context` | Önceki taleplere baktı |
| `check_policy` | Mağaza kuralını uyguladı |
| `plan_action` | Aksiyon önerilip önerilmeyeceğine karar verdi |
| `retrieve_policy` | Politika maddelerini aradı |
| `draft` | Yanıtı yazdı (model çağrısı) |
| `validate` | Sonucu doğruladı |

## Teknik terimler

| Terim | Bu projede anlamı |
|---|---|
| Idempotency anahtarı | Aynı işlemin tekrarlanmasını tek etkiye indiren anahtar: `proposal-{id}` + benzersiz kısıt ([ADR-012](DECISIONS.md#adr-012-idempotent-yürütücü-ile-iki-adımlı-onay)) |
| İyimser kilitleme | Karar isteği, ekranda görülen öneri sürümünü (`expected_version`) gönderir; sürüm değiştiyse 409 |
| TOCTOU | "Kontrol zamanı ile kullanım zamanı" farkı: onay anında sipariş durumu yeniden kontrol edilir |
| Prompt injection | Talep metnine gizlenmiş, modele talimat vermeye çalışan ifadeler; veri olarak ele alınır |
| Sahte model (`LLM_MODE=fake`) | Testlerde, CI'da ve demoda kullanılan, kurallarla yanıt veren ücretsiz ve deterministik model |
| Canlı model (`LLM_MODE=live`) | Gemini API |
| Eval | Bir senaryoyu gerçek analiz akışından geçirip kritik ve kalite kontrollerini ölçen değerlendirme ([TEST_PLAN](TEST_PLAN.md#senaryo-evalleri)) |
| Seed | Kurgusal NovaShop demo verisini oluşturan betik (`uv run poe seed`) |
| RAG | Getirme destekli üretim: modele, aranarak bulunan politika maddeleri kaynaklarıyla verilir ([ADR-014](DECISIONS.md#adr-014-politika-bilgi-tabanı-pgvector-madde-bazlı-parçalar-kararlar-kodda-kalır)) |
| Embedding | Metnin anlamını temsil eden sayı vektörü; benzer metinlerin vektörleri birbirine yakındır |
| İndeksleme (`ingest`) | Politika dokümanlarını maddelere ayırıp embedding'leriyle veritabanına yazma (`uv run poe ingest`) |
| pgvector | PostgreSQL'in vektör saklama ve benzerlik araması eklentisi |
| MCP | Model Context Protocol: yapay zekâ istemcilerinin araçları standart bir JSON-RPC arayüzüyle çağırması. SupportFlow'da üç salt okunur araç sunar ([ADR-015](DECISIONS.md#adr-015-salt-okunur-mcp-adaptörü-stdio--süreç-içi-bağlantı-kimlik-bağlantıdan-gelir)) |
| MCP aracı (`get_order_status`, `get_customer_orders`, `get_ticket_history`) | Bir talep adına salt okunur sorgu; arayüzdeki "Bu öneri nasıl hazırlandı" listesinde "· MCP" ile işaretlenir |
| stdio taşıma | MCP istemcisinin sunucuyu yerel bir süreç olarak başlatıp stdin/stdout üzerinden konuşması (`uv run poe mcp`) |
| `call_id` | Her MCP araç çağrısına verilen kimlik; log satırında ve denetim kaydında aynıdır |
| hit@k, MRR | Getirme kalitesi ölçüleri: doğru maddenin ilk k sonuç içinde olma oranı; doğru maddenin sırasının tersinin ortalaması ([TEST_PLAN](TEST_PLAN.md#politika-getirme-kalitesi)) |
