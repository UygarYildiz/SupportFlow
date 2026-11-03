## Ne değişti ve neden

<!-- Bir-iki cümle. İlgili issue: #... -->

## Nasıl doğrulandı

<!-- Çalıştırılan komutlar ve sonuçları; arayüz değiştiyse ekran görüntüsü. -->

## Kontrol listesi

- [ ] `uv run poe check` geçiyor (backend; doküman kontrolü dahil)
- [ ] Frontend değiştiyse `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` geçiyor
- [ ] Analiz davranışı değiştiyse `uv run poe eval` geçiyor; prompt değiştiyse `PROMPT_VERSION` artırıldı
- [ ] [Ne değişince ne güncellenir](../docs/README.md#ne-değişince-ne-güncellenir) tablosuna göre dokümanlar güncellendi (ya da gerek yok: neden)
- [ ] Kullanıcıya görünen değişiklik `CHANGELOG.md` "Yayınlanmamış" bölümünde
- [ ] Yeni bir yazma yolu, yetki ya da güvenlik önlemi yok; varsa `docs/SECURITY.md` ve testleri güncel
- [ ] Gerçek müşteri verisi ya da sır yok
