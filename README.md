# Insta Yazıya Çevir — macOS app projesi

Bu proje Instagram/Reels linkinden veya bilgisayardaki video/ses dosyasından Türkçe metin çıkarmak için basit bir macOS uygulaması üretir.

## v1.2 yenilikleri

- `turbo` model seçeneği eklendi.
- Geçen süre sayacı eklendi.
- Aşama göstergesi eklendi: model yükleniyor, yazıya çevriliyor, çıktılar yazılıyor vb.
- Log satırlarına saat eklendi.
- `Seçili modeli hazırla` butonu eklendi. Böylece büyük modeli video seçmeden önce yükleyebilirsin.
- `Yüklü model` bilgisi eklendi.
- `large-v3` ve `turbo` için büyük model uyarıları eklendi.
- Model cache korunuyor: uygulama açık kaldığı sürece aynı model ikinci kez yüklenmez.

## Model mantığı

- `small`: hızlı günlük kullanım.
- `medium`: ara seviye deneme.
- `large-v3`: kalite modu.
- `turbo`: large-v3 tabanlı hızlı kalite modu denemesi.

İlk kullanımda seçilen model indirilebilir ve yüklenebilir. Bu yüzden ilk çalıştırma uzun sürebilir. Aynı model uygulama açık kaldığı sürece RAM'de tutulur; ikinci video daha hızlı başlar.

## Senin için en kolay hedef

Mac'te kurulabilir dosya olarak şunlardan biri üretilecek:

- `InstaYaziyaCevir.app`
- `InstaYaziyaCevir.dmg`

Uygulama açılınca Instagram linkini yapıştırırsın veya dosya seçersin. Çıktı olarak:

- `*.duz_metin.txt`
- `*.zamanli.txt`
- `*.srt`

oluşturur.

## GitHub Actions ile `.app` üretme

1. GitHub'da repoya gir.
2. Bu klasördeki dosyaları mevcut dosyaların üzerine yükle.
3. GitHub'da repo sayfasında **Actions** sekmesine gir.
4. **Build macOS app** workflow'unu seç.
5. **Run workflow** de.
6. İş bitince **Artifacts** bölümünden şunları indir:
   - `InstaYaziyaCevir-macOS-app`
   - `InstaYaziyaCevir-macOS-dmg`

## Mac'te ilk açılış

Uygulama imzalı/noter onaylı olmadığı için macOS ilk açılışta uyarı verebilir.

Çözüm:

1. `InstaYaziyaCevir.app` dosyasına sağ tıkla.
2. **Open / Aç** de.
3. Çıkan uyarıda tekrar **Open / Aç** de.

## Mac'te kendin build almak istersen

Mac'inde Python varsa:

```bash
bash build_macos.sh
```

Çıktılar:

```text
dist/InstaYaziyaCevir.app
dist/InstaYaziyaCevir.dmg
```

## Kullanım

1. Uygulamayı aç.
2. Instagram linkini yapıştır veya dosya seç.
3. Gerekirse "Video konusu / özel terimler" alanına konuyu ve önemli kelimeleri yaz.
4. Model seç:
   - `small`: hızlı
   - `large-v3`: kaliteli
   - `turbo`: hızlı kalite modu denemesi
5. İstersen önce **Seçili modeli hazırla** butonuna bas.
6. **Yazıya çevir** butonuna bas.
7. Çıktı klasöründen `.txt` ve `.srt` dosyalarını al.

## Instagram linkleri bazen neden çalışmaz?

Özel hesap, giriş zorunluluğu, yaş/ülke kısıtı veya Instagram'ın geçici engellemesi nedeniyle link indirme başarısız olabilir. Bu durumda:

- Tarayıcıda Instagram'a giriş yap.
- Uygulamada "Instagram çerezi" olarak kullandığın tarayıcıyı seç.
- Olmazsa videoyu dosya olarak kaydedip "Dosya seç" ile işle.

## Dosya yapısı

```text
src/InstaYaziyaCevir.py              Ana macOS GUI uygulaması
requirements.txt                     Python bağımlılıkları
InstaYaziyaCevir.spec                PyInstaller paketleme ayarı
build_macos.sh                       Mac build scripti
packaging/create_dmg.sh              DMG üretimi
.github/workflows/build-macos.yml    GitHub Actions ile otomatik Mac build
```
