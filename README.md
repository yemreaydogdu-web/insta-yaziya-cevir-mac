# Insta Yazıya Çevir — macOS app projesi

Bu proje Instagram/Reels linkinden veya bilgisayardaki video/ses dosyasından Türkçe metin çıkarmak için basit bir macOS uygulaması üretir.

## Senin için en kolay hedef

Mac'te kurulabilir dosya olarak şunlardan biri üretilecek:

- `InstaYaziyaCevir.app`
- `InstaYaziyaCevir.dmg`

Uygulama açılınca Instagram linkini yapıştırırsın veya dosya seçersin. Çıktı olarak:

- `*.duz_metin.txt`
- `*.zamanli.txt`
- `*.srt`

oluşturur.

## Önemli not

Bu klasör kaynak projedir. Final `.app` dosyası Mac üzerinde derlenmelidir. En temiz yöntem GitHub Actions kullanmaktır; bu sayede kendi Mac'ine Python/FFmpeg kurmadan `.app` ve `.dmg` çıktısı alırsın.

Uygulama FFmpeg'i sistemden istemez; ses/video okuma tarafını `faster-whisper`/PyAV halleder. İlk kullanımda seçtiğin Whisper modeli indirileceği için biraz bekleyebilir.

## GitHub Actions ile `.app` üretme

1. GitHub'da yeni bir repo aç.
2. Bu zip'in içindeki tüm dosyaları repoya yükle.
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
2. Instagram linkini yapıştır.
3. Gerekirse "Instagram çerezi" kısmından Chrome/Safari/Firefox seç.
4. Model seç:
   - `base`: hızlı ve yeterli
   - `small`: daha iyi Türkçe sonuç, biraz daha yavaş
   - `medium`: daha iyi ama ağır
5. **Yazıya çevir** butonuna bas.
6. Çıktı klasöründen `.txt` dosyasını al.

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
