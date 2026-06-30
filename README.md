# Insta Yazıya Çevir v1.4

Bu sürüm video linkinden veya bilgisayardaki video/ses dosyasından metin ve SRT üretir.

## v1.4 değişiklikleri

- Üst alan artık **Video linki** olarak güncellendi.
- Özel terim / konu alanı kaldırıldı.
- Linkten indirirken ffmpeg gerektiren video+ses birleştirme yerine **tek dosya / sadece ses** indirme denenir.
- YouTube ve Instagram linklerinde ffmpeg hatasını azaltmak için `bestaudio/best[acodec!=none]/best` format seçimi kullanılır.
- Dosya seçme alanına **Temizle** butonu eklendi.
- Hem link hem dosya seçiliyse kullanıcı uyarılır.
- Chrome/Safari çerezleri seçildiğinde macOS anahtar zinciri parola izni isteyebilir.
- v1.3 güvenli bitiş filtresi korunur.
- Model cache, sayaç, model hazırlama ve RAM'den temizleme özellikleri korunur.

## Kullanım

1. Video linki yapıştır veya bilgisayardan video/ses dosyası seç.
2. Link testi için önce `small` modelle dene.
3. Kalite gerekiyorsa `large-v3` kullan.
4. Instagram giriş istiyorsa tarayıcıda Instagram açıkken `Tarayıcı çerezi: Chrome` veya `Safari` seç.
5. macOS Chrome Safe Storage / Anahtar Zinciri izni isterse Mac kullanıcı parolanı girip izin ver.

## Build

GitHub Actions üzerinden build almak için dosyaları repoya yükle ve Actions > Build macOS app workflow'unu çalıştır.

