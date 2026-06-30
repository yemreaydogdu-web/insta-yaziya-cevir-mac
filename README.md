# Insta Yazıya Çevir v1.7

Video linkinden veya bilgisayardaki video/ses dosyasından Türkçe metin çıkaran macOS uygulaması.

## v1.7 yenilikleri

- Hızlı düzeltme editörü eklendi.
- Şüpheli kelime/ifadeler sarı işaretlenir.
- İşaretli kelimeye tıklayınca öneriler altta görünür.
- Öneriye tıklayınca metin düzelir.
- Kaydet dediğinde sadece iki temiz çıktı güncellenir:
  - `*.zamanli.txt`
  - `*.duz_metin.txt`
- Artık varsayılan akışta `ham` dosya ve `srt` dosyası üretilmez.
- v1.6’daki Instagram çerez uyarısı, kısa altyazı imzası filtresi ve %100 ilerleme düzeltmesi korunur.

## Kullanım

1. Video linki yapıştır veya dosya seç.
2. Model seç:
   - `small`: hızlı taslak
   - `large-v3`: daha kaliteli sonuç
   - `turbo`: deneysel hızlı kalite
3. Instagram linklerinde genellikle Tarayıcı çerezi olarak Chrome/Safari seçmek gerekir.
4. Yazıya çevir.
5. İşlem bitince editör açılır.
6. Sarı işaretli şüpheli kelime/ifadelere tıkla, önerilerden doğru olanı seç.
7. Kaydet veya Kaydet ve kapat de.

## GitHub Actions ile build

Actions > Build macOS app > Run workflow

Çıktıdan `InstaYaziyaCevir-macOS-dmg` indir.
