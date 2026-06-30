# Insta Yazıya Çevir v1.5

Bu sürüm video linkinden veya bilgisayardaki video/ses dosyasından metin ve SRT üretir.

## v1.5 değişiklikleri

- İşlem sırasında **canlı ilerleme yüzdesi** eklendi.
- Transkripsiyon sırasında **işlenen medya süresi / toplam süre** gösterilir.
- **Tahmini kalan süre** gösterilir.
- Son algılanan metin satırı ekranda canlı görünür.
- Uzun videolar için **Sadece ilk 1 dakikayı test et** seçeneği eklendi.
- **İptal** butonu eklendi. İptal isteği mevcut segment tamamlanınca uygulanır.
- Linkten gelen videolar için uzun video uyarısı eklendi.
- v1.4'teki ffmpeg gerektirmeyen tek dosya/ses indirme mantığı korunur.
- v1.3 güvenli bitiş filtresi korunur.
- Model cache, model hazırlama, sayaç ve RAM'den temizleme özellikleri korunur.

## Kullanım

1. Video linki yapıştır veya bilgisayardan video/ses dosyası seç.
2. Link testi için önce `small` modelle dene.
3. Uzun YouTube videolarında önce **Sadece ilk 1 dakikayı test et** seçeneğini kullan.
4. Kalite gerekiyorsa `large-v3` kullan.
5. Instagram giriş istiyorsa tarayıcıda Instagram açıkken `Tarayıcı çerezi: Chrome` veya `Safari` seç.
6. macOS Chrome Safe Storage / Anahtar Zinciri izni isterse Mac kullanıcı parolanı girip izin ver.

## Build

GitHub Actions üzerinden build almak için dosyaları repoya yükle ve Actions > Build macOS app workflow'unu çalıştır.
