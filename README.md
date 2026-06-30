# Zelka Scribe v2.1.0

Video linklerinden veya bilgisayardaki video/ses dosyalarından metin çıkaran macOS/Windows uygulaması.

## v2.1.0 yenilikleri

- Sağdaki işlevsiz transcript preview alanı kaldırıldı.
- Yerine Zelka maskotlu animasyon / işlem durumu paneli eklendi.
- Sol kontrol paneli daha minimal ve açılır/kapanır hale getirildi.
- Kırık beyaz, siyah ve editorial Zelka görsel dili güçlendirildi.
- Çalışan transkripsiyon motoru, yt-dlp indirme, model cache ve çıktı mantığı korunur.
- Normal kullanıcı için yalnızca iki temiz çıktı üretilir:
  - `*.zamanli.txt`
  - `*.duz_metin.txt`
- Şüpheli kelime yoksa düzeltme editörü gereksiz yere açılmaz.

## Kullanım

1. Video linki gir veya dosya seç.
2. Model seç:
   - `small`: hızlı günlük kullanım
   - `large-v3`: kalite modu
   - `turbo`: hızlı kalite denemesi
3. Gerekirse tarayıcı çerezi olarak Chrome/Safari seç.
4. `İşlemeyi Başlat` butonuna bas.
5. Çıktılar seçili klasöre kaydedilir.

## Build

macOS:

```bash
bash build_macos.sh
```

Windows:

```powershell
.\build_windows.ps1
```

GitHub Actions içinde macOS ve Windows workflow dosyaları hazırdır.
