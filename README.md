# Insta Yazıya Çevir — macOS app projesi v1.1

Bu proje Instagram/Reels linkinden veya bilgisayardaki video/ses dosyasından metin çıkarmak için basit bir macOS uygulaması üretir.

## v1.1'de gelen değişiklikler

- Varsayılan model `small` yapıldı.
- Model cache eklendi: Uygulama açık kaldığı sürece aynı model tekrar tekrar yüklenmez.
- "Modeli RAM'den temizle" butonu eklendi.
- "Video konusu / özel terimler" alanı eklendi. Örneğin: `retainer, şeffaf plak, braket` veya `Gemini, Kling, prompt`.
- Transkripsiyonda konu/terim alanı `initial_prompt` olarak kullanılır.
- Hallucination riskini azaltmak için desteklenen sürümlerde `condition_on_previous_text=False` ve `temperature=0` denenir.

## En kolay kullanım

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

Uygulama FFmpeg'i sistemden istemez; ses/video okuma tarafını `faster-whisper`/PyAV halleder. İlk kullanımda seçtiğin Whisper modeli indirileceği için biraz bekleyebilir. Aynı uygulama oturumunda aynı model tekrar kullanılınca yeniden yüklenmez.

## GitHub Actions ile `.app` üretme

1. GitHub'da mevcut repoya bu dosyaları yükle veya yeni repo aç.
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

## Kullanım önerisi

1. Uygulamayı aç.
2. Bilgisayardan kısa bir video seçerek test et.
3. Modeli `small` bırak.
4. Dil `tr` olsun.
5. "Video konusu / özel terimler" alanına videoda geçebilecek özel kelimeleri yaz.
6. **Yazıya çevir** butonuna bas.
7. Aynı modelle ikinci video işlenirken model tekrar yüklenmez.

## Model seçimi

- `tiny`: çok hızlı, kalite düşük.
- `base`: hızlı, Türkçe kalite bazı videolarda zayıf.
- `small`: önerilen varsayılan denge.
- `medium`: daha iyi olabilir ama yavaş.
- `large-v3`: en ağır seçenek; Mac'te çok uzun sürebilir.

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
