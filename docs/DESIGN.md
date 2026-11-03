# Tasarım

NovaShop destek ekibi için operasyon konsolu. Görevi: bir çalışanın yapay zekânın taslak yanıtları ve önerdiği sipariş değişiklikleri hakkında **hızlı ve güvenli** karar vermesini sağlamak; yapay zekânın neyi kullandığını ve mağaza kurallarının ne dediğini her zaman göstermek.

## Araştırma notları

- E-ticaret yardım masaları (ör. Shopify ile Gorgias), sipariş bilgisini **konuşmanın yanındaki** bir panelde gösterir ve çalışanların siparişler üzerinde oradan işlem yapmasına izin verir.
- İnsan onaylı (human-in-the-loop) tasarım önerileri aynı noktada buluşur: yapay zekâ **asla kendiliğinden gönderilmeyen bir taslak** hazırlar, taslak düzenlenebilir kalır ve dış dünyada sonuç doğuran an bir insana aittir. İki kez onaylamak hiçbir şey yapmamalıdır.

SupportFlow ikisini de uygular: konuşma ve yapay zekâ taslağı ana sütunda, sipariş ve kararlar yan sütunda; her sipariş değişikliği açık bir onayın arkasında.

## Konsept: bir sevkiyat masası

Görsel dil, taleplerin konusu olan dünyadan, yani kargo evrakından gelir:

| Öğe | Görünüm | Neden |
|---|---|---|
| Sipariş | Bir **kargo etiketi**: kalın mürekkep çerçeve, neredeyse kare köşeler, büyük sipariş numarası | Müşterinin sorduğu fiziksel nesne bu |
| Yapay zekâ çıktısı | Bir **karbon kopya taslak**: kesikli çerçeve, soluk mavi-gri kâğıt, "Yapay zekâ taslağı" etiketi | Kesikli çizgi "kesin değil" demektir; bir bilgi olarak değil, her zaman bir öneri olarak okunmalı |
| Önerilen değişiklik | Değişikliği mevcut ve yeni olarak gösteren bir etiket | Karar tek, somut bir farka dairdir |
| Karar | Etiketin üzerine basılan bir **lastik mühür** (ONAYLANDI / REDDEDİLDİ / ENGELLENDİ / SÜRESİ DOLDU) | Akılda kalan tek öğe; sonucun doğduğu anı işaretler |
| Bekleyen öneri | Etiketin arkasında kehribar renkli kaydırılmış gölge | Bekleyen iş, ek bir rozete gerek kalmadan öne çıkar |

Geri kalan her şey sakin kalır: arayüz için tek yazı tipi, sade cümle düzeninde metinler, sola hizalama, dekoratif gradyan ya da kart gölgesi yok.

## Token'lar

| Ad | Değer | Kullanım |
|---|---|---|
| Ink (mürekkep) | `#1C2B3A` | Metin, etiket çerçeveleri |
| Paper (kâğıt) | `#EEF1F4` | Uygulama arka planı (krem değil, soğuk ton) |
| Sheet (sayfa) | `#FFFFFF` | Yüzeyler |
| Rule (çizgi) | `#CBD3DC` | Ayırıcılar |
| Carbon (karbon) | `#F3F5FA` / `#8494AD` | Yapay zekâ taslağı arka planı / kesikli çerçeve |
| Route teal (rota turkuazı) | `#0F6B73` | Linkler, birincil aksiyonlar, odak |
| Mühür yeşili / kırmızısı / kehribarı | `#1E7B4F` / `#B42318` / `#A15C07` | Uygulandı / reddedildi ya da engellendi / bekliyor |

`frontend/src/styles/tokens.css` içinde tanımlıdır. Köşe yarıçapı hiyerarşiyi izler: etiketler 3px, sayfalar 8px, kontroller 6px.

**Yazı tipi:** Tüm arayüz için Atkinson Hyperlegible (okunabilirlik için tasarlanmıştır; belirgin harf biçimleri sipariş numaralarını karışıklığa yer bırakmadan okutur). Big Shoulders Stencil Display yalnızca logo ve mühür için. Ölçek 13 / 14 / 16 / 20 / 26 px; her yerde tabular rakamlar.

## Yerleşim

```
┌────────┬────────────────────────────────────┬──────────────────────┐
│ ray    │ Talep başlığı, durum, aksiyonlar                          │
│        ├────────────────────────────────────┬──────────────────────┤
│Talepler│ Müşteri mesajı                     │ Önerilen değişiklik  │
│Onaylar │ ┌ ─ Önerilen yanıt (taslak) ─ ─ ─┐ │ (etiket + karar)     │
│        │   özet, uyarılar, düzenle, kopyala │ Sipariş (etiket)     │
│        │ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │ Mağaza kuralı        │
│ kişi   │ Geçmiş                             │                      │
└────────┴────────────────────────────────────┴──────────────────────┘
```

1024px'in altında sütunlar karar sırasıyla birleşir: mesaj, taslak, öneri, sipariş, kural, geçmiş. 760px'in altında yan ray üst çubuğa dönüşür.

## Genel bakış (ana sayfa)

Sahibin ilk incelemesinden sonra eklendi. "Gelen kutusunda ne var?" sorusundan önce "Benim ilgilenmem gereken ne var?" sorusunu yanıtlar:

```
Merhaba, Selin                   Destek uzmanı. Adres değişikliklerini onaylayabilirsiniz; iadeler yöneticiye gider.
[5 İncelemeye hazır] [14 Yeni] [6 Müşteriden bilgi bekleniyor] [0 Analiz ediliyor] [0 Başarısız] [5 Çözüldü]   -> filtrelenmiş liste
┌ Kararınızı bekleyenler ┐  ┌ Yönetici bekleyenler (destek uzmanı) / Denetim kaydı (yönetici) ┐
└────────────────────────┘  └──────────────────────────────────────────────────────────────────┘
┌ Son güncellenen talepler ┐  ┌ Denetim kaydı: "yalnızca yöneticiler görebilir" (destek uzmanı) ┐
```

Bir önerinin hangi listeye düşeceği tarayıcıdaki bir rol kontrolünden değil, API'nin `can_decide` alanından gelir. Destek uzmanlarına denetim kaydının sessizce kaybolması yerine, var olduğu ve yalnızca yöneticilerin görebildiği söylenir.

## Davranış kuralları

- Yapay zekâ çıktısı her zaman taslak olarak etiketlenir; dayandığı bilgiler listelenir ("ORD-1001'e dayanarak"), uyarılar gizlenmez, gösterilir.
- Bir karar işlenirken Onayla ve Reddet devre dışıdır; 409 durumunda sunucunun gerekçesi gösterilir ve kart gerçek durumla yenilenir.
- Karar veremeyen roller gizemli bir devre dışı buton değil, nedenini görür.
- Tek animasyon, kullanıcının kararıyla tetiklenen mühür basmasıdır (260ms); `prefers-reduced-motion` açıkken kapalıdır.
- Klavye: görünür odak halkası, içeriğe atlama linki, gerçek buton ve linkler; durum değişiklikleri `role="status"` / `role="alert"` ile duyurulur.

## Sahip inceleme kaydı

**1. tur (2026-11-03).**

- Genel görünüm: onaylandı ("güzel bir atmosfer"). Sevkiyat masası konsepti korunacak.
- Talep listesi: olduğu gibi iyi.
- Giriş sayfasının boş sağ tarafı: artık kısa bir "bir talep nasıl ilerler" açıklaması (müşteri, yapay zekâ taslağı, karar veren kişi) ve iki rol için "kim ne yapabilir" tablosu var.
- "Destek uzmanı ile yönetici arasında görünür bir fark yok": kural vardı (iadeler yönetici ister) ama demo verisinde bekleyen iade yoktu ve yöneticiye özel verinin bir ekranı yoktu. Yukarıdaki genel bakış sayfası, iade önerilerindeki "Yalnızca yönetici" işareti, selamlamanın altındaki rol satırı ve bekleyen iadeleri olan seed demo hareketleriyle düzeltildi.
- Yeni: girişten sonra ana sayfa genel bakış sayfasıdır.

**Türkçeleştirme (2026-11-03).** Proje Türk işverenlere Türkçe sunulacağı için arayüz metinleri, demo verisi ve dokümanlar Türkçeye çevrildi. Mühür metinleri Türkçe karakter içeriyor (İ, Ü); iki fontun da Fontsource paketi latin-ext alt kümesini (U+0100–02BA) yüklediği için bu karakterler kendi fontuyla çizilir. Ekran görüntüleri (`docs/images/`) Türkçe arayüzle yeniden alınmalı.

Hâlâ açık: taslak düzenleyicinin özetin üstünde mi durması gerektiği.
