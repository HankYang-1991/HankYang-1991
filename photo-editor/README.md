# 暗房 Darkroom — 手機／電腦通用修圖與剪輯 App

一套程式碼，同時在 **手機（iPhone / Android）** 與 **電腦（Windows / Mac / Linux）** 使用的圖層式修圖、AI 去背與照片影片剪輯工具。
純 HTML + JavaScript + Canvas，不需安裝任何套件或編譯；可「加入主畫面」當 App 用，並支援離線。

## 功能

| 類別 | 功能 |
|---|---|
| 工具 | 移動、平移、裁切（含 1:1 / 4:3 / 16:9 等比例）、筆刷（大小／不透明度／硬度，支援觸控筆壓力）、橡皮擦、形狀（矩形／橢圓／直線，Shift 鎖定比例）、油漆桶（容許度）、文字、滴管 |
| 圖層 | 新增、複製、刪除、上下移、向下合併、顯示／隱藏、重新命名（雙擊）、不透明度、16 種混合模式（色彩增值、濾色、覆蓋、柔光…） |
| 調整（即時預覽） | 曝光、亮度、對比、亮部、陰影、色溫、色調、色相、飽和度、自然飽和度、銳利化、模糊、暈影、顆粒 |
| 濾鏡（縮圖預覽） | 黑白、高反差黑白、懷舊、暖陽、冷調、褪色底片、鮮豔、復古、負片、自動色階、馬賽克、浮雕、邊緣、柔焦 |
| 影像 | 旋轉 90°、水平／垂直翻轉、影像尺寸、新增畫布（Full HD / 4K / IG / A4 / A3 預設）、置入影像為圖層、平面化 |
| AI 去背 | 在裝置上執行（照片不上傳）；新背景可選透明／前景色／模糊原背景（人像模式）／黑白背景（色彩焦點）；可調邊緣貼合、硬度、羽化，調整後「重新套用」不必重新辨識；另有不需模型的「純色背景去除」 |
| 剪輯模式 | 照片＋影片排在時間軸（拖曳或箭頭排序）、影片起點／終點裁剪、分割、速度 0.25×–4×、音量；照片長度與動態效果（放大、縮小、平移）；轉場（交叉淡化、黑場、滑入、縮放）；濾鏡；字幕；背景音樂（音量、結尾淡出）；比例 16:9／9:16／1:1／4:5；720p／1080p 匯出 MP4（不支援時為 WebM）；修圖↔剪輯互傳畫面 |
| 其他 | 復原／重做（30 步）、拖放開檔、貼上剪貼簿影像、雙指縮放、滑鼠滾輪縮放、匯出 PNG / JPEG / WebP（可調品質與縮放） |

## 快捷鍵（電腦）

`V` 移動　`H` 平移（或按住空白鍵）　`C` 裁切　`B` 筆刷　`E` 橡皮擦　`U` 形狀　`G` 油漆桶　`T` 文字　`I` 滴管
`[` `]` 筆刷大小　`Ctrl+Z` 復原　`Ctrl+Shift+Z` / `Ctrl+Y` 重做　`Ctrl+S` 匯出　`Ctrl+O` 開啟　`Ctrl+0` 符合視窗　`1` 100%
`Ctrl+J` 複製圖層　`Ctrl+E` 向下合併　`Enter` 套用裁切　`Esc` 取消

## 剪輯模式快捷鍵

`空白鍵` 播放／暫停　`← →` 前後 1 秒（加 Shift 為 5 秒）　`S` 在播放位置分割影片　`Delete` 刪除片段

## 執行

```bash
cd photo-editor
python -m http.server 8000
# 電腦開 http://localhost:8000
# 手機與電腦同一個 Wi-Fi：開 http://<電腦IP>:8000
```

要安裝成 App（離線可用）需要 HTTPS，最簡單是開啟 **GitHub Pages**（Settings → Pages → 選這個分支），
之後在手機 Safari「分享 → 加入主畫面」或 Chrome「安裝應用程式」即可。

單一檔案版本（方便寄送或放到任何地方）：

```bash
python build_single.py darkroom.html
```

## 檔案

| 檔案 | 說明 |
|---|---|
| `index.html` | 介面 |
| `style.css` | 樣式（寬度 < 760px 自動切換手機版：底部工具列、上滑面板） |
| `app.js` | 修圖引擎：圖層合成、工具、調整、濾鏡、復原、匯出 |
| `ai.js` | AI 去背：U²-Net-p 模型 + guided filter 邊緣精修；純色背景去除 |
| `video.js` | 剪輯模式：時間軸、轉場、字幕、音訊混音、MediaRecorder 匯出 |
| `models/u2netp.onnx` | AI 去背模型（4.6 MB） |
| `sw.js`, `manifest.webmanifest`, `icon.svg` | PWA（安裝與離線） |
| `build_single.py` | 打包成單一 HTML |

## 參考的開源專案（GitHub 研究結果，2026-10）

| 專案 | ⭐ | 授權 / 狀態 | 參考點 |
|---|---|---|---|
| [KDE/krita](https://github.com/KDE/krita) | 10.6k | GPL，C++/Qt 桌面 | 筆刷與圖層概念；無法直接用於手機網頁 |
| [GNOME/gimp](https://github.com/GNOME/gimp) | 6.5k | GPL，C 桌面 | 最完整的 Photoshop 替代品；同上 |
| [nhn/tui.image-editor](https://github.com/nhn/tui.image-editor) | 7.7k | MIT，**已封存** | 網頁 Canvas 修圖 UI 架構 |
| [viliusle/miniPaint](https://github.com/viliusle/miniPaint) | 3.5k | MIT，持續維護 | 最接近「網頁版 Photoshop」：圖層 + 效果 |
| [photopea/photopea](https://github.com/photopea/photopea) | 8.5k | **非開源**（只有 issue 追蹤） | 介面操作參考 |

本專案程式碼為自行撰寫，未複製上述專案原始碼。

### AI 模型與執行環境

| 元件 | 來源 | 授權 |
|---|---|---|
| `models/u2netp.onnx` | [U²-Net](https://github.com/xuebinqin/U-2-Net)（輕量版 U²-Netp，ONNX 版取自 [rembg](https://github.com/danielgatis/rembg)） | Apache-2.0 |
| onnxruntime-web 1.17.3 | 執行時從 jsDelivr CDN 載入（若頁面旁有 `vendor/ort-wasm-simd.wasm` 則優先使用本機檔） | MIT |

注意事項：
- U²-Netp 是「顯著物體」模型，對人像、商品、動物效果好；複雜背景或細髮絲邊緣可能需要再用橡皮擦微調。
- 影片匯出是「即時錄製」，10 秒的影片需要約 10 秒；匯出時請保持畫面開啟。
- iPhone 需 iOS 17.4 以上才能匯出 MP4。
