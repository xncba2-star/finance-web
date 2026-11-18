# RuangUang – Personal Finance Tracker

Aplikasi pencatatan keuangan pribadi berbasis Streamlit.

## Fitur
- Dashboard saldo gabungan, pemasukan, pengeluaran, dan transaksi terbaru.
- Multi-account: rekening bank, e-wallet, uang tunai, dan akun lain.
- Transfer internal antar akun milik sendiri (tidak dihitung sebagai income/expense).
- Catatan cicilan, tagihan, dan PayLater.
- Scan struk menggunakan OCR (hasil wajib diperiksa sebelum disimpan).
- Analisis kategori, tren, dan rekap periode.
- Ekspor backup JSON dan ekspor transaksi CSV.
- PIN aplikasi opsional.

## Menjalankan di Streamlit Community Cloud
1. Buat repository GitHub baru.
2. Upload seluruh isi folder ini ke root repository.
3. Buka https://share.streamlit.io/ dan login dengan GitHub.
4. Pilih **New app**, pilih repository, branch, dan file `app.py`.
5. Deploy.

## Menjalankan secara lokal (tanpa VS Code)
Jika ingin mencoba di komputer, instal Python lalu jalankan dari terminal:
```bash
pip install -r requirements.txt
streamlit run app.py
```
Untuk OCR lokal, Tesseract OCR juga perlu dipasang. Di Streamlit Cloud, `packages.txt` memasang Tesseract dan paket bahasa Indonesia.

## Catatan penting tentang penyimpanan
Versi awal ini menggunakan SQLite (`ruanguang.db`). Pada hosting cloud, filesystem lokal dapat bersifat sementara dan data dapat hilang saat aplikasi di-restart atau di-redeploy. Gunakan tombol **Download backup JSON** secara berkala. Untuk pemakaian jangka panjang/multi-device, hubungkan database persisten seperti Supabase pada tahap berikutnya.

## Keamanan
- Jangan pernah memasukkan PIN, password, atau OTP mobile banking.
- PIN aplikasi adalah pengunci sederhana, bukan autentikasi akun yang kuat.
- Jangan publikasikan data keuangan pribadi. Repository kode boleh public, tetapi jangan pernah mengunggah database atau backup berisi transaksi.
- Versi ini belum terhubung langsung ke bank/e-wallet. Input manual dan import mutasi CSV adalah jalur awal yang aman.
