# MAHI OCEAN — 鬼頭刀海況研究站

公開測試網站：https://marinechchang-rgb.github.io/mahi-ocean-web/

真實 JMA 每日資料，提供日期切換、SST、50/100/200/400m 水溫、三個獨立 HSI 情境、表面海流、拖曳縮放、點位查值、JSON 下載。手機亦可使用。缺少所選日資料時停用該圖層，不跨日補值。

## 科學限制

HSI 模型 2.0.0 沿用桌面計算核心。PSAT 與 CPUE 僅為 SST-only proxy；舊版 T100 獨立呈現。尚未取得 SSS、MLD 與原 GAM。0–1 是未校準相對適合度，不是捕獲機率、魚群位置或預報。

PSAT 最適區間 25–27°C，過渡帶 24–25 / 27–28°C；CPUE 26–28°C，過渡帶 25–26 / 28–29°C；T100 17.8–23.1°C，過渡帶 16.8–17.8 / 23.1–24.1°C。線性過渡是工程假設。

資料來源 JMA GOOS，逐日 JSON 包含來源 URL、檔名、日期、原始檔 SHA256、模型參數。缺值保留 null。海流單位 m/s，只供疊圖。Natural Earth 公有領域陸地資料經範圍裁切與簡化，不供航行。

## 更新與部署

GitHub Actions 將 main 的 docs 目錄部署至 GitHub Pages。更新工作流程每日執行，下載三來源最新十日並重新產製；失敗不覆蓋已發布資料。頁面顯示真實觀測日期與產製時間，不代表資料每次都更新成功。

```sh
pip install -r requirements.txt
python tools/export.py --download
python -m http.server 8765 --directory docs
```

離線重建：`python tools/export.py --raw-root /path/to/JMA/data`。首次發布資料為 2026-10-09 至 2026-10-18，各來源實際供應日不同。只公開程式與公開海洋資料衍生成果，不含桌面 EXE 或原始研究簡報。
