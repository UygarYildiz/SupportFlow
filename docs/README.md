# Dokümantasyon

SupportFlow'un dokümanları tek bir kurala göre düzenlenir: **her bilginin tek bir evi vardır.** Bir bilgi başka bir yerde gerekiyorsa kopyalanmaz, evine link verilir. Böylece bir şey değiştiğinde güncellenecek tek bir yer olur.

## Nereden başlamalı

| Siz kimsiniz | Okuma sırası |
|---|---|
| Projeyi değerlendiren (işveren, mühendis) | [README](../README.md) → [Mimari](ARCHITECTURE.md) → [Güvenlik](SECURITY.md) → [Kararlar](DECISIONS.md) |
| Projede geliştirme yapacak kişi | [Geliştirme kılavuzu](DEVELOPMENT.md) → [Mimari](ARCHITECTURE.md) → [Sözlük](GLOSSARY.md) → [Katkı kuralları](../CONTRIBUTING.md) |
| API'yi kullanacak kişi | [API referansı](API.md) → [Sözlük](GLOSSARY.md) |
| Uygulamayı çalıştıran, sorun gideren kişi | [Operasyon kılavuzu](OPERATIONS.md) |
| Projeyi gösterecek kişi (sunum, video) | [Demo senaryosu](DEMO_SCRIPT.md) → [Operasyon kılavuzu](OPERATIONS.md#demo-öncesi-hazırlık) |

## Doküman haritası

| Doküman | Cevapladığı soru | Tek doğruluk kaynağı olduğu konular |
|---|---|---|
| [README](../README.md) | Bu nedir, neden var, nasıl denerim? | Ürün tanımı, hızlı başlangıç, bilinen sınırlamalar |
| [REQUIREMENTS](REQUIREMENTS.md) | Sistem ne yapmalı? | Roller, erişim modeli, NovaShop kuralları, S1–S6 senaryoları, kapsam |
| [ARCHITECTURE](ARCHITECTURE.md) | Nasıl kurulu? | Modüller ve bağımlılık kuralları, akışlar, durum makineleri, güven sınırları |
| [DECISIONS](DECISIONS.md) | Neden böyle? | Mimari karar kayıtları (ADR) |
| [SECURITY](SECURITY.md) | Neye karşı korunuyor? | Tehditler, önlemler, önlemleri kanıtlayan testler |
| [TEST_PLAN](TEST_PLAN.md) | Nasıl doğrulanıyor? | Test matrisi (TC-01…TC-20), eval'ler, test ve eval sayıları |
| [DESIGN](DESIGN.md) | Arayüz neden böyle görünüyor? | Görsel dil, token'lar, davranış kuralları, sahip inceleme kaydı |
| [API](API.md) | Uç noktalar nasıl kullanılır? | Uç nokta listesi, kimlik doğrulama, hata kodları |
| [DEVELOPMENT](DEVELOPMENT.md) | Nasıl geliştiririm? | Kurulum, klasör yapısı, komutlar, sık yapılan işlerin tarifleri |
| [OPERATIONS](OPERATIONS.md) | Nasıl çalıştırır, nasıl düzeltirim? | Ortam değişkenleri, servisler, prosedürler, sorun giderme |
| [DEMO_SCRIPT](DEMO_SCRIPT.md) | Nasıl gösteririm? | 3–5 dakikalık gösterim akışı, yedek planlar |
| [GLOSSARY](GLOSSARY.md) | Bu terim ne demek? | Kod terimi ↔ arayüz metni ↔ anlam eşlemesi |
| [CHANGELOG](../CHANGELOG.md) | Ne değişti? | Sürüm notları |
| [CONTRIBUTING](../CONTRIBUTING.md) | Nasıl katkı yaparım? | Branch, commit, inceleme ve doküman kuralları |

Haritada olmayan iki dosya bilerek dışarıda tutulur: `ROADMAP.md` proje sahibinin kişisel planıdır; `CLAUDE.md` dosyaları yapay zekâ asistanı için yazılmış çalışma talimatlarıdır (İngilizce).

## Yazım kuralları

- **Dil:** Dokümanlar Türkçedir. Kod tanımlayıcıları, enum değerleri, komutlar ve dosya adları olduğu gibi (İngilizce) yazılır ve `kod` biçiminde gösterilir.
- **Terimler:** [Sözlük](GLOSSARY.md)'teki karşılıklar kullanılır. Yeni bir terim önce sözlüğe eklenir.
- **Önce en faydalı bilgi:** Her doküman bir-iki cümlelik amaçla başlar, ardından okuyucunun en sık ihtiyaç duyduğu bölüm gelir.
- **Göster:** Mümkün olduğunda açıklama yerine çalıştırılabilir komut, istek örneği ya da tablo.
- **Kopyalama, link ver:** Bir ADR'yi, bir kuralı ya da bir komut listesini başka dokümana kopyalamak yerine ona link verilir. İstisna: README'deki hızlı başlangıç (bilinçli olarak kısa bir özet).
- **Sayılar tek yerde:** Test, eval ve uç nokta sayıları yalnızca [TEST_PLAN](TEST_PLAN.md), [API](API.md) ve README'deki test tablosunda geçer; tarihli sonuçlar tarihleriyle yazılır.
- **Dürüstlük:** Henüz yapılmamış bir şey "planlandı (Faz N)" olarak yazılır, yapılmış gibi anlatılmaz. Sınırlamalar README'deki "Bilinen sınırlamalar" bölümünde toplanır.
- **Gizli bilgi yok:** Gerçek müşteri verisi, API anahtarı ya da parola dokümana girmez (demo parolası hariç).

## Ne değişince ne güncellenir

Her değişiklikten sonra bu tabloya bakılır. Aynı değişiklik birden fazla satıra uyabilir.

| Değişiklik | Güncellenecek dokümanlar |
|---|---|
| Uç nokta eklendi, silindi, yolu ya da yetkisi değişti | [API](API.md) (otomatik kontrol edilir), gerekiyorsa [REQUIREMENTS](REQUIREMENTS.md) §3 erişim modeli |
| İstek/yanıt şeması değişti | [API](API.md), frontend tipleri (`npm run gen:api`) |
| Yeni hata mesajı ya da hata kodu | [API](API.md) hata bölümü |
| Mimari karar alındı ya da eskisi değişti | [DECISIONS](DECISIONS.md)'a yeni ADR; eskisi silinmez, "Yerini aldı: ADR-0XX" notu düşülür |
| Modül, katman ya da akış değişti | [ARCHITECTURE](ARCHITECTURE.md) |
| Durum (status) eklendi ya da geçiş kuralı değişti | [ARCHITECTURE](ARCHITECTURE.md) §4, [GLOSSARY](GLOSSARY.md), [API](API.md) |
| NovaShop kuralı (iade süresi vb.) değişti | [REQUIREMENTS](REQUIREMENTS.md) §4 |
| Yeni güvenlik önlemi ya da tehdit | [SECURITY](SECURITY.md) (önlemi kanıtlayan test adıyla) |
| Test, eval senaryosu eklendi ya da sayısı değişti | [TEST_PLAN](TEST_PLAN.md), README test tablosu |
| Prompt değişti (`PROMPT_VERSION`) | [TEST_PLAN](TEST_PLAN.md) canlı sonuç tablosu (yeni sürüm satırı) |
| Ortam değişkeni eklendi ya da varsayılanı değişti | `.env.example`, [OPERATIONS](OPERATIONS.md) yapılandırma tablosu |
| Komut, araç ya da kurulum adımı değişti | [DEVELOPMENT](DEVELOPMENT.md), gerekiyorsa README hızlı başlangıç |
| Yeni operasyonel prosedür ya da bilinen arıza | [OPERATIONS](OPERATIONS.md) |
| Arayüz metni ya da yeni terim | [GLOSSARY](GLOSSARY.md), görsel değişiklikse [DESIGN](DESIGN.md) |
| Ekranı görünür şekilde değiştiren iş | `docs/images/` ekran görüntüleri, [DEMO_SCRIPT](DEMO_SCRIPT.md) (ekranda görünenler) |
| Seed verisi değişti | [DEMO_SCRIPT](DEMO_SCRIPT.md) (talep numaraları), [OPERATIONS](OPERATIONS.md#demo-öncesi-hazırlık) |
| Kullanıcıya görünen her değişiklik | [CHANGELOG](../CHANGELOG.md) "Yayınlanmamış" bölümü |
| Bilinen bir sınırlama kalktı ya da eklendi | README "Bilinen sınırlamalar" |

## Otomatik kontroller

`cd backend && uv run poe docs` aşağıdakileri kontrol eder. Aynı kontroller `uv run poe check` içindeki testlerle her CI çalıştırmasında da koşar; bir uyuşmazlık CI'ı kırmızıya çevirir.

| Kontrol | Yakaladığı sorun |
|---|---|
| Linkler | Var olmayan bir dosyaya verilen göreli link |
| Anchor'lar | `DOSYA.md#baslik` linkinde artık var olmayan başlık (Türkçe karakterler dahil, GitHub'ın kuralıyla) |
| API listesi | [API](API.md)'deki uç nokta başlıkları ile uygulamanın OpenAPI şeması arasındaki fark (eksik ya da fazla uç nokta) |
| ADR numaraları | Dokümanlarda geçen ama [DECISIONS](DECISIONS.md)'ta olmayan bir ADR numarası |
| Harita | `docs/` altında olup bu dosyadaki haritada yer almayan doküman |

Otomatik kontrol, metnin *doğru* olduğunu kanıtlamaz; yalnızca bariz biçimde eskimiş olanı yakalar. İçeriğin güncelliği yukarıdaki tabloya ve PR şablonundaki doküman maddesine dayanır.

## Sürümler ve değişiklik kaydı

- [CHANGELOG](../CHANGELOG.md), [Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/) biçimini ve [anlamsal sürümlemeyi](https://semver.org/lang/tr/) izler.
- Kullanıcıya görünen her değişiklik commit'le birlikte "Yayınlanmamış" bölümüne eklenir; sürüm çıkarken bu bölüm sürüm numarasıyla tarihlenir ve GitHub release notu oradan alınır.
