import sqlite3
conn = sqlite3.connect('database_upz_desa.db')
c = conn.cursor()

desa_target = 'Rancapaku' # Ganti dengan nama desa yang ingin dihapus datanya

tabel_transaksi = ['setoran_dkm', 'sabilillah', 'amilin', 'qurban', 'guru_ngaji', 'majlis_talim', 'setoran_kecamatan']

for tabel in tabel_transaksi:
    c.execute(f"DELETE FROM {tabel} WHERE nama_desa = ?", (desa_target,))
    print(f"✅ Data desa {desa_target} telah dihapus dari tabel {tabel}")

conn.commit()
conn.close()