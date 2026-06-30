# Zelka Scribe v2.0

Zelka Labs çatısı altında hazırlanan macOS video/ses yazıya çevirme uygulaması.

**Product:** Zelka Scribe  
**Descriptor:** Video to Text Converter

## v2.0 yenilikleri

- Zelka Scribe marka arayüzü eklendi.
- Program içi yatay logo ve app icon assetleri eklendi.
- Uygulama adı, DMG adı ve GitHub Actions artifact adları Zelka Scribe olarak güncellendi.
- Çalışan transkripsiyon motoru korunur:
  - yerel video/ses dosyası seçme,
  - YouTube/Instagram ve benzeri linklerden indirme,
  - Chrome/Safari/Firefox/Edge çerezi seçme,
  - small / medium / large-v3 / turbo model seçimi,
  - ilk 1 dakika test modu,
  - canlı işlem yüzdesi, geçen süre ve tahmini kalan süre,
  - iptal butonu,
  - model cache / RAM temizleme.
- Çıktı sistemi sadeleştirildi: normal kullanımda yalnızca iki temiz dosya üretilir:
  - `*.zamanli.txt`
  - `*.duz_metin.txt`
- Hızlı düzeltme editörü korunur; şüpheli kelimeler işaretlenir ve önerilerden düzeltilebilir.

## Kullanım

1. Video linki yapıştır veya bilgisayardan video/ses dosyası seç.
2. Model seç:
   - `small`: hızlı günlük kullanım
   - `large-v3`: kalite modu
   - `turbo`: hızlı kalite denemesi
3. Gerekirse tarayıcı çerezi seç. Instagram linkleri çoğunlukla Chrome/Safari çerezi isteyebilir.
4. `Convert` butonuna bas.
5. İşlem bitince editör açılır; gerekirse düzeltmeleri yapıp kaydet.

## macOS build

GitHub Actions otomatik build alır. Elle build için:

```bash
bash build_macos.sh
```

Çıktılar:

```text
dist/Zelka Scribe.app
dist/ZelkaScribe.dmg
```

## Not

Bu sürümde amaç çalışan motoru bozmadan ürünü Zelka Scribe kimliğine taşımaktır. Transkripsiyon, indirme ve model ayarlarının temel mantığı v1.7'den korunmuştur.
