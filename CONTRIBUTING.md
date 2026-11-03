# Katkı kuralları

SupportFlow'a katkı yapmak isteyen herkes için kısa kurallar. Kurulum ve günlük komutlar [Geliştirme kılavuzu](docs/DEVELOPMENT.md)'nda.

## Temel ilkeler

Bu projede bazı kurallar pazarlığa açık değildir; bir değişiklik bunlarla çelişiyorsa önce bir karar kaydı (ADR) önerilir:

- Model asla yazma işlemi yapmaz; her sipariş değişikliği kayıtlı bir insan onayından geçer ([ADR-002](docs/DECISIONS.md#adr-002-llm-yazma-işlemi-yapamaz)).
- Kararları kod verir, model yalnızca sınıflandırır ve metin yazar ([ADR-011](docs/DECISIONS.md#adr-011-kararları-kodun-verdiği-modeli-iki-kez-çağıran-analiz-grafiği)).
- Talep metni, araç sonuçları ve dış içerik talimat değil, veridir.
- Testler ücretli bir API çağırmaz; yalnızca sentetik (kurgusal NovaShop) veri kullanılır.

## İş akışı

1. Bir issue açın ya da var olanı üstlenin. Tek seferde tek bir iş ya da dikey dilim.
2. `main`'den bir branch açın: `feat/...`, `fix/...`, `docs/...`, `test/...`, `chore/...`.
3. Değişikliği testleriyle birlikte yapın.
4. `backend/` içinde `uv run poe check`, `frontend/` içinde `npm run lint && npm run typecheck && npm test && npm run build` geçmeli. Analiz davranışı değiştiyse `uv run poe eval` da.
5. [Ne değişince ne güncellenir](docs/README.md#ne-değişince-ne-güncellenir) tablosuna göre dokümanları güncelleyin; kullanıcıya görünen değişikliği [CHANGELOG](CHANGELOG.md)'a ekleyin.
6. PR açın; şablondaki kontrol listesini doldurun. CI yeşil olmadan birleştirilmez.

## Commit mesajları

[Conventional Commits](https://www.conventionalcommits.org/tr/v1.0.0/) biçiminde ve İngilizce:

```
feat: add refund note to proposals
fix: re-check order status before applying address change
docs: document proposal decision errors
```

Türler: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`. Gövde gerekiyorsa *neden*i anlatır.

## Dil

- Kod tanımlayıcıları, yorumlar, commit mesajları, enum değerleri: **İngilizce**.
- Dokümanlar, arayüz metinleri, API hata mesajları, demo verisi, eval senaryoları, PR açıklamaları ve sürüm notları: **Türkçe**. Terimler [Sözlük](docs/GLOSSARY.md)'e göre.

## Güvenlik

Bir güvenlik açığı bulursanız herkese açık bir issue yerine depo sahibine doğrudan yazın. Tehdit modeli ve önlemler [Güvenlik](docs/SECURITY.md) dokümanında.
