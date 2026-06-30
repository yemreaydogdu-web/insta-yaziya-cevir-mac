# Insta Yazıya Çevir v1.6

Video linkinden veya bilgisayardaki video/ses dosyasından Türkçe metin, zamanlı metin ve SRT altyazı çıkaran macOS uygulaması.

## v1.6 ile gelenler

- Instagram linklerinde çerez `Yok` seçiliyken kullanıcıya ön uyarı verir.
- Kısa `Altyazı M.K.` / altyazı imzası gibi sahte kapanış segmentlerini de temizler.
- `çeviriyor` gibi normal konuşma kelimelerini yanlışlıkla “çeviri imzası” sanan filtre gevşetildi.
- İşlem bittiğinde ilerleme çubuğu ve durum alanı artık %100 / kalan 00:00 gösterir.
- v1.5 özellikleri korundu: YouTube/Instagram link indirme, ffmpeg gerektirmeyen ses/tek dosya indirme, canlı ilerleme, iptal, ilk 1 dakika test modu, model cache.

## Önerilen kullanım

- Kısa ve hızlı test: `small`
- Kaliteli transkripsiyon: `large-v3`
- Deneysel hızlı kalite: `turbo`
- Instagram linkleri için çoğu zaman `Tarayıcı çerezi: Chrome` veya `Safari` seçmek gerekir.

## GitHub Actions ile build

1. Dosyaları GitHub reposuna yükle.
2. Actions sekmesinde `Build macOS app` workflow'unu çalıştır.
3. Artifacts bölümünden DMG dosyasını indir.
4. DMG'yi açıp uygulamayı Applications klasörüne sürükle.
