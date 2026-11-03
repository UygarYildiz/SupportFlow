# API referansı

SupportFlow backend'inin REST API'si: kimlik doğrulama, uç noktalar, hata kodları ve tipik akışlar. Alan bazında tam şema (tüm alanlar, tipler, kısıtlar) çalışan backend'de OpenAPI olarak bulunur: http://localhost:8000/docs (Swagger) ve `/openapi.json`. Bu doküman ne zaman hangi uç noktanın kullanılacağını ve davranışını anlatır.

> Uç nokta başlıkları (`### \`METHOD /yol\``) `uv run poe docs` tarafından uygulamanın OpenAPI şemasıyla karşılaştırılır. Uç nokta ekleyen ya da silen her değişiklik bu dosyayı da güncellemelidir.

## Genel kurallar

- **Taban yol:** `/api/v1`. Sağlık kontrolleri (`/health`, `/ready`) kökte ve herkese açıktır.
- **Kimlik doğrulama:** `/health`, `/ready`, `/api/v1/auth/login` ve ilk açılış kurulumu (`/api/v1/setup`, `/api/v1/setup/status`) dışındaki her uç nokta `Authorization: Bearer <token>` ister. Token kısa ömürlüdür (`ACCESS_TOKEN_EXPIRE_MINUTES`, varsayılan 30 dk). Kullanıcının rolü her istekte veritabanından yeniden okunur; pasifleştirilen kullanıcı anında erişimini kaybeder.
- **Roller:** "Personel" = `agent_user` ya da `admin`. Bazı uç noktalar yalnızca `admin` içindir. Rol yetmezse 403 döner. Rol kuralları sunucudadır; arayüzdeki `can_decide` alanı yalnızca bilgilendirmedir.
- **Biçim:** İstek ve yanıtlar JSON. Zaman damgaları saat dilimli UTC (ISO 8601). Para tutarları ondalık metin (`"749.50"`) ve ayrı bir `currency` alanı (`"TRY"`).
- **Kimlikler:** Talepler, kullanıcılar, çalıştırmalar ve öneriler tamsayı; müşteriler ve siparişler dış sistemin metin kimlikleri (`CUS-0001`, `ORD-1001`) ([ADR-010](DECISIONS.md#adr-010-kalıcılık-kuralları)).
- **Sayfalama:** Liste uç noktaları `limit` (1–100, varsayılan 20) ve `offset` alır ve şu biçimde döner:

```json
{ "items": [ ... ], "total": 30, "limit": 20, "offset": 0 }
```

- **Enum değerleri** (`status`, `category`, `type`…) İngilizce koddur; Türkçe karşılıkları [Sözlük](GLOSSARY.md)'te.

## Hatalar

Her hata şu biçimde döner; `detail` personele gösterilebilecek Türkçe bir mesajdır:

```json
{ "detail": "#7 numaralı öneri zaten 'executed' durumunda" }
```

| Kod | Ne zaman | Örnek `detail` |
|---|---|---|
| 401 | Token yok, geçersiz ya da süresi dolmuş; kullanıcı pasif | `Oturum açılmamış` |
| 401 | Girişte yanlış e-posta/parola (bilinmeyen kullanıcı ve pasif hesap da aynı yanıtı alır) | `E-posta ya da parola hatalı` |
| 403 | Kurulum kodu hatalı (yalnız `POST /api/v1/setup`) | `Kurulum kodu hatalı` |
| 403 | Rol bu işlemi yapamaz | `Bu işlem için yetkiniz yok`, `'agent_user' rolü 'create_refund_request' önerileri hakkında karar veremez` |
| 404 | Kayıt yok | `Sipariş bulunamadı: ORD-9999` |
| 409 | İstek güncel durumla çelişiyor: geçersiz durum geçişi, devam eden analiz, eski sürümle karar, zaten verilmiş karar, süresi dolmuş ya da içeriği değiştirilmiş öneri | `#3 numaralı talebin devam eden bir analizi var` |
| 422 | İstek biçimi geçerli ama bir iş kuralını ihlal ediyor | `'ORD-B1' bu müşterinin hiçbir siparişiyle eşleşmiyor` |
| 422 | Alan doğrulama hatası (FastAPI/Pydantic) | `detail` bir dizidir: `[{"loc": [...], "msg": "...", "type": "..."}]` (mesajlar İngilizce) |
| 503 | `/ready`: veritabanına ulaşılamıyor | `{"status": "not_ready", "database": "unavailable"}` |

**409 alan istemci ne yapmalı?** Elindeki kopya eskidir. Kaydı yeniden çekip güncel durumu göstermeli; aynı isteği körlemesine tekrarlamamalı. Panel bunu yapar ([DESIGN](DESIGN.md#davranış-kuralları)).

## Tipik akış

```bash
API=http://localhost:8000/api/v1

# 1. Giriş
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"selin@novashop.example","password":"supportflow-demo"}' | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

# 2. Analizi başlat (202 + çalıştırma), sonucu yokla
RUN=$(curl -s -X POST $API/tickets/1/analyze -H "$AUTH" | jq .id)
curl -s $API/runs/$RUN -H "$AUTH" | jq '.status, .result.analysis.draft_reply'

# 3. Talebin bekleyen önerisi varsa, gösterilen sürümle karar ver
curl -s "$API/proposals?ticket_id=3&status=pending" -H "$AUTH" | jq '.items[0] | {id, version}'
curl -s -X POST $API/proposals/2/decision -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"decision":"approve","expected_version":1,"note":"Müşteri telefonda teyit etti."}'
```

## Sağlık kontrolleri

### `GET /health`

Canlılık: süreç ayakta mı? Bağımlılıklara dokunmaz. Yanıt: `{"status": "ok"}`.

### `GET /ready`

Hazırlık: veritabanı yanıt veriyor mu? Başarılıysa 200 `{"status": "ready", "database": "ok"}`, değilse 503 `{"status": "not_ready", "database": "unavailable"}`. Sürücü ayrıntısı istemciye dönmez, loglanır.

## İlk açılış kurulumu

Yalnızca kendi kurulumda (`DEPLOYMENT_MODE=self_hosted`) anlamlıdır ([ADR-017](DECISIONS.md#adr-017-gerçek-kullanım-için-tek-işletmelik-kendi-kurulumu-demo-sentetik-kalır), [SELF_HOSTING](SELF_HOSTING.md)). İkisi de herkese açıktır: kurulumdan önce giriş yapılacak bir hesap yoktur.

### `GET /api/v1/setup/status`

Kurulumun modu ve ilk yöneticiye hâlâ ihtiyaç olup olmadığı. Panel, giriş ekranı yerine kurulum sayfasını göstermeye ve demo hesaplarını gizlemeye bununla karar verir.

```json
{ "mode": "self_hosted", "setup_required": true, "setup_token_required": true, "organization_name": null }
```

`demo` modunda `setup_required` her zaman `false`'tur. Kullanıcısı olan bir veritabanında da kurulum açılmaz.

### `POST /api/v1/setup`

İşletme kaydını ve ilk yöneticiyi tek transaction'da oluşturur, yöneticiye token döner (201, `POST /auth/login` ile aynı yanıt). İstek:

```json
{ "organization_name": "Kuzey Kırtasiye", "full_name": "Deniz Kaya", "email": "deniz@kuzey.example",
  "password": "en az on iki karakter", "setup_token": "<SETUP_TOKEN>" }
```

Yalnızca bir kez başarılı olur. Kurulum tamamlanmışsa (ya da `demo` modundaysa) 409 `Kurulum zaten tamamlanmış. Giriş yapın.`; bu durumda kod hiç kontrol edilmez. `SETUP_TOKEN` yapılandırılmışsa ve kod uyuşmuyorsa 403. Zayıf parola, geçersiz e-posta ya da boş işletme adı 422 alır ve hiçbir kayıt oluşmaz. Yarışan iki istekten yalnız biri kazanır.

## Kimlik doğrulama ve kullanıcılar

### `POST /api/v1/auth/login`

Herkese açık. İstek: `{"email": "...", "password": "..."}`. Yanıt:

```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 1800 }
```

Bilinmeyen kullanıcı, yanlış parola ve pasif hesap aynı 401 yanıtını alır (hesap keşfine karşı, [SECURITY T12](SECURITY.md#tehditler-ve-önlemler)).

### `GET /api/v1/auth/me`

Oturumdaki kullanıcı: `{"id", "email", "full_name", "role", "is_active"}`.

### `POST /api/v1/auth/password`

Oturumdaki kullanıcı kendi parolasını değiştirir: `{"current_password": "...", "new_password": "..."}`. Mevcut parola yanlışsa ya da yeni parola kurala uymuyorsa 422. Yanıt: kullanıcı (`GET /auth/me` ile aynı). Denetim kaydına `user.password_changed` yazılır.

**Parola kuralı** (hesap ekleme, sıfırlama ve değiştirmede): 12–128 karakter, boşlukla başlayıp bitemez, e-posta adresini içeremez. Aykırılık 422 ve Türkçe gerekçe döner.

### `GET /api/v1/users`

Yalnızca `admin`. Tüm personel hesapları (ekip sayfası ve denetim kaydındaki `actor_id`'leri isme çevirmek için).

### `POST /api/v1/users`

Yalnızca `admin`. Geçici parolayla yeni hesap ekler (201): `{"email", "full_name", "password", "role"}`; `role` verilmezse `agent_user`. E-posta küçük harfe çevrilip saklanır; aynı adres (büyük/küçük harf farkı gözetmeksizin) varsa 409 `Bu e-posta adresiyle bir hesap zaten var`. Denetim: `user.created`.

### `PATCH /api/v1/users/{user_id}`

Yalnızca `admin`. Yalnız gönderilen alanlar değişir: `full_name`, `role`, `is_active`, `password` (sıfırlama). Rol ve etkinlik değişikliği bir sonraki istekte geçerli olur (rol her istekte yeniden okunur). Yönetici kendi rolünü değiştiremez ve kendini pasifleştiremez; hiçbir değişiklik kurulumu etkin yöneticisiz bırakamaz (422 `En az bir etkin yönetici kalmalı`). Bilinmeyen hesap 404. Denetim: `user.updated` (parola değil, yalnızca sıfırlandığı yazılır).

## Talepler

### `GET /api/v1/tickets`

Personel. Talep listesi, sayfalı. Filtreler: `status`, `priority`, `category`, `customer_id`. Sıralama: `sort=created` (varsayılan, en yeni önce) ya da `sort=updated` (son güncellenen önce). Öğe:

```json
{
  "id": 1, "customer_id": "CUS-0001", "customer_name": "Elif Yılmaz", "order_id": "ORD-1001",
  "subject": "Siparişim nerede?", "status": "awaiting_review", "priority": "medium",
  "category": "delivery_delay",
  "created_at": "2026-11-03T06:50:12Z", "updated_at": "2026-11-03T08:52:41Z"
}
```

`category` analizden önce `null`'dır.

### `GET /api/v1/tickets/summary`

Personel. Genel bakış sayaçları:

```json
{
  "by_status": { "new": 12, "triaging": 0, "awaiting_review": 6, "needs_info": 5, "resolved": 7, "failed": 0 },
  "total": 30,
  "pending_proposals": 3
}
```

### `POST /api/v1/tickets`

Personel. Talep oluşturur (201). İstek:

```json
{
  "customer_id": "CUS-0003",
  "order_id": "ORD-1003",
  "subject": "Teslimat adresi değişikliği",
  "message": "Yeni adresim: Moda Caddesi No:42, Kadıköy/İstanbul.",
  "priority": "medium"
}
```

`order_id` ve `priority` isteğe bağlıdır. Müşteri yoksa ya da sipariş o müşteriye ait değilse 422 (başka müşterinin siparişi ile olmayan sipariş aynı mesajı alır). Yanıt, aşağıdaki talep detayıdır.

### `GET /api/v1/tickets/{ticket_id}`

Personel. Talep detayı: liste alanlarına ek olarak `message`, `customer` (`id`, `display_name`, `email`), `order` (bağlı sipariş ya da `null`) ve `events` (zaman çizelgesi: `event_type`, `actor_type`, `actor_id`, `payload`, `occurred_at`).

### `PATCH /api/v1/tickets/{ticket_id}`

Personel. Durumu ve/veya önceliği değiştirir: `{"status": "resolved"}`, `{"priority": "high"}`. En az biri gerekir. Personelin yapabileceği geçişler sınırlıdır ([ARCHITECTURE §4](ARCHITECTURE.md#4-durum-makineleri)): ör. `new → resolved` olur, `new → triaging` olmaz (o geçiş yalnızca analize aittir). Geçersiz geçiş 409.

## Siparişler

### `GET /api/v1/customers/{customer_id}/orders`

Personel. Müşterinin siparişleri. Müşteri yoksa 404.

### `GET /api/v1/orders/{order_id}`

Personel. Tek sipariş:

```json
{
  "id": "ORD-1003", "customer_id": "CUS-0003", "status": "processing",
  "total_amount": "1249.00", "currency": "TRY",
  "shipping_address": "Atatürk Bulvarı No:52, Kadıköy/İstanbul",
  "items": [{ "sku": "NS-BKP-03", "name": "Seyahat Sırt Çantası", "quantity": 1, "unit_price": "1249.00" }],
  "created_at": "...", "shipped_at": null, "delivered_at": null
}
```

Yoksa 404; durum asla uydurulmaz. Personel tüm siparişleri görebilir (tek şirket, tek destek ekibi); yapay zekâ ajanı ise yalnızca talebin müşterisinin siparişlerini görür ([REQUIREMENTS §3](REQUIREMENTS.md#3-erişim-modeli)).

## Yapay zekâ analizi

### `POST /api/v1/tickets/{ticket_id}/analyze`

Personel. Analizi kuyruğa alır ve hemen **202** ile çalıştırmayı döner (`status: "queued"`); analiz arka planda yürür ([ADR-005](DECISIONS.md#adr-005-analiz-çalıştırmaları-kalıcı-arka-plan-işleridir)). Yalnızca `new` durumundaki talepler analiz edilebilir; talep başka durumdaysa ya da devam eden bir analiz varsa 409. Başarısız bir analizden sonra talep `PATCH` ile `new`'e alınıp yeniden denenebilir.

### `GET /api/v1/runs/{run_id}`

Personel. Çalıştırmanın durumu ve sonucu; tamamlanana kadar yoklanır (panel 800 ms aralıkla). Alanlar:

| Alan | Açıklama |
|---|---|
| `status` | `queued`, `running`, `succeeded`, `failed` |
| `steps` | Çalışan graf düğümleri: `node`, `status`, `duration_ms`, `summary` (araç çağrıları, sayılar; müşteri metni yok) |
| `result.analysis` | `category`, `suggested_priority`, `summary`, `needs_human_review`, `draft_reply`, `missing_information`, `evidence_order_ids` |
| `result.verified_order_ids` / `unverified_order_ids` | Kanıtların backend doğrulaması; doğrulanmayanlar kanıt olarak gösterilmez |
| `result.policy_excerpts` | Kural sonucunu açıklamak için getirilen politika maddeleri: `policy_id`, `title`, `version`, `effective_from`, `clause_id`, `heading`, `text` |
| `result.cited_clause_ids` / `unverified_clause_ids` | Taslağın atıf yaptığı ve getirilen maddelerle doğrulanan madde kimlikleri; doğrulanmayanlar ayrı listelenir ve gösterilmez |
| `result.policy_checks` | `rule`, `order_id`, `allowed`, `reason`, `informational` |
| `result.proposed_action` | Önerilen aksiyon ya da `null`; aynı transaction'da bekleyen bir öneri olarak kaydedilir |
| `result.warnings`, `result.outcome_status` | Personele uyarılar; talebin varacağı durum (`awaiting_review` / `needs_info`) |
| `error_code`, `error_message` | Başarısızlıkta kararlı kod ve Türkçe mesaj ([Sözlük](GLOSSARY.md#analiz-çalıştırması-durumları-ve-hata-kodları)) |
| `model`, `prompt_version`, `input_tokens`, `output_tokens`, `latency_ms` | İzlenebilirlik |

Örnek `result` (S3, adres değişikliği):

```json
{
  "analysis": {
    "category": "address_change",
    "summary": "Talep 'adres değişikliği' olarak sınıflandırıldı (ORD-1003 numaralı sipariş).",
    "needs_human_review": false,
    "draft_reply": "Merhaba Zeynep Şahin,\n\nORD-1003 numaralı siparişinizle ilgili talebinizi aldık. ...",
    "missing_information": [],
    "evidence_order_ids": ["ORD-1003"]
  },
  "verified_order_ids": ["ORD-1003"],
  "policy_checks": [{
    "rule": "address_change_v1", "order_id": "ORD-1003", "allowed": true,
    "reason": "Sipariş henüz kargoya verilmedi; teslimat adresi değiştirilebilir.", "informational": false
  }],
  "policy_excerpts": [{
    "policy_id": "address_change", "title": "Adres Değişikliği Politikası", "version": 1,
    "effective_from": "2026-01-01", "clause_id": "ADRES-1", "heading": "Ne zaman mümkün",
    "text": "Teslimat adresi yalnızca sipariş \"beklemede\" ya da \"hazırlanıyor\" durumundayken ..."
  }],
  "cited_clause_ids": ["ADRES-1"],
  "proposed_action": {
    "type": "change_shipping_address", "order_id": "ORD-1003",
    "payload": { "current_address": "Atatürk Bulvarı No:52, Kadıköy/İstanbul",
                 "new_address": "Moda Caddesi No:42, Kadıköy/İstanbul" },
    "requires_approval": true
  },
  "outcome_status": "awaiting_review",
  "prompt_version": "graph-v4"
}
```

### `GET /api/v1/tickets/{ticket_id}/runs`

Personel. Talebin tüm çalıştırmaları, en yeni önce.

## Öneriler ve onay

### `GET /api/v1/proposals`

Personel. Öneri listesi, sayfalı. Filtreler: `status` (onay kuyruğu için `pending`), `ticket_id`. Öğe:

```json
{
  "id": 1, "ticket_id": 2, "run_id": 1, "order_id": "ORD-1002",
  "type": "create_refund_request",
  "payload": { "refund_reason": "damaged_item", "order_total": "749.50 TRY" },
  "reason": "Hasar bildirimi teslimattan sonraki 30 gün içinde yapıldı.",
  "policy_rule": "damaged_goods_v1",
  "status": "pending", "version": 1,
  "created_at": "...", "expires_at": "...",
  "decided_by": null, "decided_at": null, "decision_note": null,
  "executed_at": null, "failure_reason": null,
  "can_decide": true
}
```

`can_decide`, oturumdaki kullanıcının rolünün bu tipte karar verip veremeyeceğini söyler (iadeler yalnızca `admin`).

### `GET /api/v1/proposals/{proposal_id}`

Personel. Tek öneri.

### `POST /api/v1/proposals/{proposal_id}/decision`

Personel; aksiyon tipine göre rol kontrolü yapılır. İstek:

```json
{ "decision": "approve", "expected_version": 1, "note": "Müşteri telefonda teyit etti." }
```

- `expected_version`: istemcinin gösterdiği önerinin `version`'ı. Arada değiştiyse 409 (iyimser kilitleme).
- `approve` aksiyonu **hemen ve tam olarak bir kez** uygular ([ADR-012](DECISIONS.md#adr-012-idempotent-yürütücü-ile-iki-adımlı-onay)). Yanıttaki öneri `executed` (uygulandı) ya da `failed` (onay anındaki yeniden kontrol izin vermedi; neden `failure_reason`'da) olur.
- `reject` hiçbir şeyi değiştirmez; öneri `rejected` olur.
- Aynı kararı tekrarlamak (çift tıklama, ikinci inceleyen) 409 alır ve ikinci bir etki üretmez. Süresi dolmuş öneri 409 alır ve asla yürütülmez. İçeriği veritabanında değiştirilmiş öneri 409 alır.
- 403: rol bu tipe karar veremez (ör. destek uzmanı ve iade).

### `GET /api/v1/audit`

Yalnızca `admin`. Denetim kaydı. Filtreler: `ticket_id`; `limit` (1–200, varsayılan 50), `offset`; `sort=oldest` (varsayılan, kronolojik) ya da `sort=newest`. Sayfalı değil, dizi döner. Öğe: `actor_type`, `actor_id`, `action` (`proposal.created`, `proposal.approved`, `proposal.rejected`, `proposal.expired`, `proposal.integrity_failed`, `action.executed`, `action.failed`), `resource_type`, `resource_id`, `ticket_id`, `details` (adres ve e-posta maskelenmiş), `occurred_at`.
