# AI-HSO Middleware (Flask + TM1py)

Middleware yang terima data dari luar , generate jadi CSV, jalankan TI di TM1, lalu pindahin file CSV-nya ke folder backup.

## Cara jalanin

1. Pastikan `.env` udah bener isinya (path, kredensial TM1, secret key, dll).
2. Jalankan:
   ```
   python run.py
   ```
   `run.py` otomatis matiin instance lama (kalau ada), bersihin `__pycache__`, lalu start `app.py`.
3. Cek server hidup: `http://localhost:5001/health` → harus balas `{"status":"running"}`.

## Alur pakainya

1. **Get token** dulu: `POST /auth/token` (form-urlencoded: `grant_type`, `username`, `password`, `scope`, `client_id`, `client_secret`). Token cuma satu yang aktif dalam satu waktu — generate baru = token lama otomatis invalid.
2. **Kirim data**: `POST /sync-dealer`, `/sync-catalogue`, `/sync-polreg`, atau `/sync-workdays` (JSON, header `Authorization: Bearer <token>`).
3. Di belakang layar: validasi payload → tulis CSV → jalankan TI di TM1 → kalau TI sukses, CSV dipindah ke folder backup dengan nama ditambah timestamp.

## Struktur folder penting

```
tm1py/
├── app.py                      # entry point, endpoint /auth/token & /health
├── run.py                      # start/restart server (cross-platform Windows & Linux)
├── config.json                 # daftar endpoint sync + settingan server
├── README.md
├── .gitignore
├── secret_key.py                # generate SECRET_KEY baru
├── Core/
│   ├── auth.py                  # generate & verifikasi token
│   ├── router.py                # daftarin route /sync-*, validasi awal request
│   ├── logger.py                # logging + auto rotate + auto hapus log lama
│   ├── response.py
│   └── settings.py
├── Services/
│   ├── base_service.py          # facade — cuma re-export, gak ada logic sendiri
│   ├── control_panel.py         # baca cube Control Panel di TM1 (path, cache duration)
│   ├── file_naming.py           # nama file CSV dinamis based on attribute SyncCode
│   ├── ti_runner.py             # jalanin TI process
│   ├── file_ops.py              # tulis CSV, pindahin file, build error row
│   └── master_data/
│       ├── masterdata_dealer.py
│       ├── masterdata_catalogue.py
│       ├── masterdata_polreg.py
│       └── workdays.py
├── Validation/
│   ├── validator.py             # validasi isi JSON, termasuk lokasi error (line/col)
│   └── validation_rules.py      # skema tiap SyncCode
├── Utils/
│   └── normalizer.py
└── Integrations/
    └── tm1_connection.py
```

## Hal-hal penting yang perlu diinget

- **Path folder (CSV, backup, log) dan nama file CSV itu dinamis** — diambil dari cube TM1 (`00-ControlPanelAPI` buat path, attribute `FileNamePrefix` di dimensi `SyncCode` buat nama file). Kalau di cube kosong, otomatis fallback ke default (`.env` untuk path, nama hardcode untuk file).
- **Cache aktif cuma kalau `CacheDuration(Seconds)` di cube ≠ 0 DAN semua path ketemu di cube.** Kalau salah satu kosong, sistem selalu fetch ulang ke cube tiap request — gak pernah cache setengah-setengah.
- **Nama TI process harus PERSIS sama** dengan yang ada di TM1 (`LoadData-Dealer`, `LoadData-01-MappingCatalogue`, `LoadData-01-MappingDealerPolreg`, `LoadData-01-Workdays`). Salah satu huruf aja beda, TI-nya gak ketemu.
- **Kalau move file ke folder backup gagal** (misal permission error), itu cuma di-log ERROR, gak bikin proses gagal, soalnya TI nya udah sukses duluan. Tapi konsekuensinya, file lama bakal ketimpa run berikutnya kalau emang gak pernah kepindah.
- **Cross-platform**: kill-process pas start pakai `psutil`, jalan di Windows maupun Linux tanpa perlu ubah kode.



#Author
Mohamad Asep Shayfullah
GitHub: https://github.com/asepms2023
Website: https://asepms20.my.id/


#License

This project is provided for internal and educational use.
