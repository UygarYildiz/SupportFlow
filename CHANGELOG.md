# Değişiklik kaydı

Bu projedeki kullanıcıya görünen değişiklikler bu dosyada tutulur. Biçim [Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/), sürümleme [Anlamsal Sürümleme](https://semver.org/lang/tr/) kurallarını izler. Yeni değişiklikler "Yayınlanmamış" bölümüne eklenir; sürüm çıkarken bu bölüm sürüm numarası ve tarihle adlandırılır.

## [Yayınlanmamış]

İlk sürüm (`v0.1.0`) olarak yayınlanacak MVP.

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

- Proje Türk işverenlere sunulacağı için tüm dokümanlar, arayüz, hata mesajları, demo verisi ve eval senaryoları Türkçeye çevrildi; sahte model Türkçe mesajları anlıyor.
