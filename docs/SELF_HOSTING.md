# Kendi kurulumu

SupportFlow'u kendi işletmeniz için, kendi bilgisayarınızda ya da sunucunuzda çalıştırma kılavuzu. Bir kurulum tek bir işletmeye hizmet eder ve müşteri verileriniz sizin makinenizde kalır ([ADR-017](DECISIONS.md#adr-017-gerçek-kullanım-için-tek-işletmelik-kendi-kurulumu-demo-sentetik-kalır)). Herkese açık demo ise sentetik NovaShop verisiyle çalışır; ikisi birbirinden bağımsızdır.

> **Durum:** Bu ilk sürüm kurulumu, ekip yönetimini ve panelin kendisini sağlar. E-posta kutusu bağlama, CSV ile müşteri/sipariş yükleme ve model seçimi sıradaki adımlardır ([yol haritası, Blok D](../ROADMAP.md)). Şimdilik talepler panelden ya da [API](API.md#post-apiv1tickets) ile açılır.

## Gerekenler

- [Docker](https://docs.docker.com/get-docker/) ve Docker Compose (Docker Desktop ikisini birlikte kurar)
- Git (ya da GitHub'dan indirilmiş kaynak kodu)
- 2 GB boş bellek, 2 GB disk

## Kurulum (5 dakika)

```bash
git clone https://github.com/UygarYildiz/SupportFlow.git
cd SupportFlow/deploy/selfhost

./init.sh                      # Windows PowerShell: .\init.ps1
docker compose up -d --build
```

1. `init.sh` / `init.ps1`, aynı klasörde rastgele sırlarla bir `.env` dosyası oluşturur ve ekrana bir **kurulum kodu** yazar. Bu kodu not edin (`.env` içinde `SETUP_TOKEN` olarak da durur).
2. İlk `docker compose up` imajları derler; birkaç dakika sürebilir.
3. Tarayıcıda http://localhost:8080 adresini açın. Boş bir kurulum sizi **kurulum sayfasına** götürür: işletme adını, kendi adınızı, e-postanızı, bir parola (en az 12 karakter) ve kurulum kodunu girin.
4. Kurulum bitince yönetici olarak oturum açılmış olursunuz. **Ekip** sayfasından çalışma arkadaşlarınızı ekleyin; her birine geçici bir parola verin, onlar da **Hesabım** sayfasından değiştirsin.

Kurulum yalnızca bir kez yapılabilir. Sonradan gelen herkes giriş ekranını görür.

PowerShell betiği engellenirse: `powershell -ExecutionPolicy Bypass -File .\init.ps1`

## Roller

| Rol | Ne yapabilir |
|---|---|
| Destek uzmanı (`agent_user`) | Talepleri görür, yapay zekâ analizini başlatır, adres değişikliklerini onaylar |
| Yönetici (`admin`) | Ayrıca iadeleri onaylar, denetim kaydını görür ve ekibi yönetir |

Ayrıntılı erişim modeli: [REQUIREMENTS](REQUIREMENTS.md). Yönetici kendi rolünü değiştiremez ve kendi hesabını pasifleştiremez; kurulumda her zaman en az bir etkin yönetici kalır.

## Ayarlar

Ayarlar `deploy/selfhost/.env` dosyasındadır. Değiştirdikten sonra `docker compose up -d` çalıştırın.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SUPPORTFLOW_BIND` | `127.0.0.1` | Panelin dinlediği adres. `127.0.0.1`: yalnız bu bilgisayar. `0.0.0.0`: yerel ağdaki diğer bilgisayarlar da erişir. |
| `SUPPORTFLOW_PORT` | `8080` | Panelin portu |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Oturumun süresi (dakika); dolunca yeniden giriş istenir |
| `LLM_MODE` | `fake` | `fake`: sabit örnek taslaklar, ücretsiz. `live`: kendi Gemini anahtarınızla gerçek model. **`live` modda müşteri mesajları Google'a gönderilir.** |
| `GEMINI_API_KEY` | boş | [Google AI Studio](https://aistudio.google.com/) anahtarı (`LLM_MODE=live` için) |
| `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `SETUP_TOKEN` | rastgele | Betik üretir. Kurulumdan sonra değiştirmeyin: `POSTGRES_PASSWORD` veritabanı ilk oluşturulurken sabitlenir; `JWT_SECRET_KEY` değişirse herkesin oturumu kapanır. |

Tüm backend değişkenlerinin anlamı: [OPERATIONS](OPERATIONS.md#yapılandırma).

## Kurulumu internete açmak

Varsayılan kurulum yalnızca bu bilgisayardan erişilebilir. Başka yerlerden erişmek istiyorsanız panelin önüne **HTTPS** sağlayan bir ters vekil koyun (ör. [Caddy](https://caddyserver.com/docs/quick-starts/reverse-proxy) ya da Cloudflare Tunnel) ve `SUPPORTFLOW_BIND`'i `127.0.0.1`'de bırakın. Parolalar ve oturum anahtarları HTTPS olmadan ağda okunabilir. Veritabanı hiçbir zaman dışarıya port açmaz.

## Günlük işler

```bash
cd deploy/selfhost
docker compose ps                      # durum
docker compose logs -f backend         # backend logları
docker compose down                    # durdur (veriler kalır)
docker compose up -d                   # yeniden başlat
```

**Güncelleme:** `git pull`, ardından `docker compose up -d --build`. Backend açılırken veritabanı şemasını kendisi günceller.

**Yedek:** Veriler `supportflow-selfhost_pgdata` Docker biriminde durur.

```bash
docker compose exec -T db pg_dump -U supportflow supportflow > yedek.sql      # yedek al
docker compose exec -T db psql -U supportflow supportflow < yedek.sql         # boş bir kuruluma geri yükle
```

**Sıfırdan başlamak** (tüm verileri siler): `docker compose down -v`, ardından `.env`'i silip kurulumu baştan yapın.

## Sorun giderme

| Belirti | Neden ve çözüm |
|---|---|
| `run init.sh / init.ps1 first` hatası | `.env` yok ya da sırlar boş. Betiği çalıştırın. |
| Kurulum sayfası "Kurulum kodu hatalı" diyor | `.env`'deki `SETUP_TOKEN` değerini girin; değeri değiştirdiyseniz `docker compose up -d` ile backend'i yeniden başlatın. |
| Kurulum sayfası yerine giriş ekranı açılıyor | Kurulum zaten yapılmış. Parolayı unuttuysanız başka bir yönetici **Ekip** sayfasından sıfırlayabilir. |
| Sayfa açılmıyor | `docker compose ps` ile servislerin `running` olduğunu, `docker compose logs backend` ile hata olmadığını kontrol edin. 8080 portu doluysa `SUPPORTFLOW_PORT`'u değiştirin. |
| Backend `SETUP_TOKEN must be set` diyerek kapanıyor | Kendi kurulum üretim modunda kurulum kodu zorunludur; `.env`'de en az 16 karakterlik bir değer olmalı. |
