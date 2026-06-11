import sqlite3

# Sambungkan ke database yang sudah ada
conn = sqlite3.connect('database_upz_desa.db')
c = conn.cursor()

print("Memulai update database...")

# 1. Membuat tabel akun (users) untuk sistem Login
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT, 
    nama_desa TEXT 
)
''')

# 2. Membuat akun default (1 Kecamatan, 2 contoh Desa)
try:
    c.execute("INSERT INTO users (username, password, role, nama_desa) VALUES ('adminkec', 'kecamatan123', 'kecamatan', 'KECAMATAN')")
    c.execute("INSERT INTO users (username, password, role, nama_desa) VALUES ('desarancapaku', 'desa123', 'desa', 'Rancapaku')")
    c.execute("INSERT INTO users (username, password, role, nama_desa) VALUES ('desasuka', 'desa123', 'desa', 'Sukamaju')")
    print("- Akun berhasil dibuat.")
except:
    print("- Akun sudah ada.")

# 3. Menambahkan kolom 'nama_desa' sebagai "sekat kamar" ke tabel transaksi lama
tabel_list = ['setoran_dkm', 'sabilillah', 'amilin', 'qurban', 'guru_ngaji', 'majlis_talim', 'arsip_setoran_dkm', 'arsip_sabilillah', 'arsip_amilin', 'arsip_distribusi_ngaji']

for tabel in tabel_list:
    try:
        c.execute(f"ALTER TABLE {tabel} ADD COLUMN nama_desa TEXT DEFAULT 'Rancapaku'")
        print(f"- Kolom nama_desa ditambahkan ke tabel {tabel}")
    except:
        print(f"- Kolom nama_desa sudah ada di tabel {tabel} (Aman).")

conn.commit()
conn.close()
print("🎉 Update database SELESAI!")