# Project notes for Claude

## 暗房 Darkroom (`photo-editor/`)

- **Every change to the app must also update the software spec (軟體開發規格書)**:
  https://claude.ai/artifact/W2aiZNFAEX1rYw5GefGTYa (Claude Docs, doc id `eb118b1f-adc4-4ff2-a6a8-89c9a999bd67`).
  Read it first (changes since your last read), keep the owner's own edits, then update the affected
  sections and add a row to 「11. 版本紀錄與待辦事項」 in the same turn as the code change.
- Live preview link (Claude artifact): https://claude.ai/artifact/XnEtCKzH1WQnk7p3BjdXi1 —
  rebuild with `python photo-editor/build_single.py <out.html> --fragment` and republish it after each change.
- UI copy is Traditional Chinese (zh-Hant). Keep the one-preview-bar pattern: any live preview
  (adjust, filters, flash looks) goes through `beginPreview` / `endPreview` in `app.js`.
- Test in a browser at desktop (1366×820) and phone (390×800) sizes before pushing; the page must
  never scroll sideways on the phone layout.
