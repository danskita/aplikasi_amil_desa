import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os
import modul_cetak as mc

def format_rupiah(angka):
    if pd.isna(angka) or angka == "": return "Rp 0"
    return f"Rp {int(angka):,.0f}".replace(",", ".")

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Laporan Terpadu Amil", page_icon="🕌", layout="wide")
DB_NAME = "database_upz_desa.db"

# ==========================================
# 2. AUTO-SETUP DATABASE & MULTI-USER
# ==========================================
def setup_multiuser():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, nama_desa TEXT)''')
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role, nama_desa) VALUES ('adminkec', 'kecamatan123', 'kecamatan', 'KECAMATAN')")
    
    tabel_list = ["pengaturan", "qurban", "master_dkm", "guru_ngaji", "majlis_talim", "master_kategori_sab", "master_jabatan_amil"]
    for tb in tabel_list:
        try: c.execute(f"ALTER TABLE {tb} ADD COLUMN nama_desa TEXT")
        except: pass

    tabel_list_bobot = ["master_kategori_sab", "master_jabatan_amil", "guru_ngaji"]
    for tb in tabel_list_bobot:
        try: c.execute(f"ALTER TABLE {tb} ADD COLUMN bobot REAL DEFAULT 1.0")
        except: pass

    kolom_baru_pengaturan = [
        ("bendahara", "TEXT"), ("pct_amil_kec", "REAL DEFAULT 12.5"),
        ("no_hp", "TEXT"), ("total_jiwa", "INTEGER"), ("total_kk", "INTEGER"),
        ("nominal_kupon", "REAL DEFAULT 2000.0"),
        ("pct_amil_desa", "REAL DEFAULT 12.5")
    ]
    for col, tipe in kolom_baru_pengaturan:
        try: c.execute(f"ALTER TABLE pengaturan ADD COLUMN {col} {tipe}")
        except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS setoran_kecamatan (id INTEGER PRIMARY KEY AUTOINCREMENT, nama_desa TEXT, beras_disetor REAL, uang_disetor REAL, tanggal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS distribusi_kec_program (id INTEGER PRIMARY KEY AUTOINCREMENT, program TEXT, penerima TEXT, beras REAL, uang REAL, tanggal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS distribusi_kec_amil (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, jabatan TEXT, beras REAL, uang REAL, tanggal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sabilillah (id INTEGER PRIMARY KEY AUTOINCREMENT, program TEXT, penerima TEXT, beras REAL, uang REAL, nama_desa TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS amilin (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, jabatan TEXT, beras REAL, uang REAL, nama_desa TEXT)''')
    
    conn.commit()
    conn.close()

setup_multiuser()

# ==========================================
# 3. SISTEM LOGIN & SESSION
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = ""
    st.session_state["nama_desa"] = ""

def form_login():
    st.title("🕌 Sistem Laporan Terpadu Amil")
    st.markdown("Silakan masuk menggunakan akun Kecamatan atau Desa.")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Masuk / Login", width='stretch', type="primary"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT role, nama_desa FROM users WHERE username=? AND password=?", (username, password))
                user = c.fetchone()
                conn.close()
                if user:
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = user[0]
                    st.session_state["nama_desa"] = user[1]
                    st.rerun()
                else: 
                    st.error("Username atau Password salah!")

def logout():
    st.session_state["logged_in"] = False
    st.session_state["role"] = ""
    st.session_state["nama_desa"] = ""
    st.rerun()

if not st.session_state["logged_in"]:
    form_login()
    st.stop()

# ==========================================
# 4. MENU NAVIGASI (SIDEBAR)
# ==========================================
st.sidebar.title(f"🕌 Amil {st.session_state['nama_desa']}")
st.sidebar.caption(f"Hak Akses: {st.session_state['role'].title()}")

if st.sidebar.button("🚪 Keluar (Logout)", width='stretch'): 
    logout()
st.sidebar.markdown("---")

if st.session_state["role"] in ["kecamatan", "admin"]:
    menu_halaman = ["📊 Rekapitulasi Kecamatan", "📥 Setoran UPZ Desa", "📤 Distribusi UPZ Kecamatan", "📂 Kelola Data Master", "🖨️ Laporan Rekap Desa", "⚙️ Profil Kecamatan", "👥 Kelola Pengguna"]
else:
    menu_halaman = ["📊 Dashboard Utama", "📥 Penerimaan Zakat", "📤 Distribusi UPZ", "🐄 Data Qurban", "🕌 Data Majlis Ta'lim", "📂 Kelola Data Master", "🖨️ Cetak Laporan PDF", "📁 Arsip Data Lama", "⚙️ Pengaturan"]

pilihan_menu = st.sidebar.radio("Pilih Halaman:", menu_halaman)
st.sidebar.markdown("---")
st.sidebar.info("💡 Buka di HP untuk kemudahan akses saat di lapangan.")


# =========================================================================
# ======================== HALAMAN KHUSUS KECAMATAN =======================
# =========================================================================
if pilihan_menu == "📊 Rekapitulasi Kecamatan":
    st.title("📊 Dashboard Rekapitulasi Kecamatan")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    tab_zakat, tab_qurban, tab_majlis = st.tabs(["💰 Rekap Zakat & Infaq", "🐄 Rekap Hewan Qurban", "🕌 Rekap Majlis Ta'lim"])
    
    with tab_zakat:
        c.execute("SELECT SUM(total_beras), SUM(total_uang), SUM(infaq), SUM(jiwa_beras), SUM(jiwa_uang) FROM setoran_dkm")
        himpun = c.fetchone()
        t_beras = himpun[0] or 0
        t_uang = himpun[1] or 0
        t_infaq = himpun[2] or 0
        j_beras = himpun[3] or 0
        j_uang = himpun[4] or 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Muzakki", f"{j_beras + j_uang} Jiwa")
        col2.metric("Total Beras", f"{t_beras:,.2f} Kg")
        col3.metric("Total Uang", format_rupiah(t_uang))
        col4.metric("Total Infaq", format_rupiah(t_infaq))
        
        st.markdown("---")
        st.subheader("📋 Rekapitulasi & Status Setoran per Desa")
        try:
            df_rekap = pd.read_sql_query("""SELECT d.nama_desa AS 'Nama Desa', SUM(d.jiwa_beras + d.jiwa_uang) AS 'Total Jiwa', SUM(d.total_beras) AS 'Total Beras (Kg)', SUM(d.total_uang) AS 'Total Uang Zakat (Rp)', SUM(d.infaq) AS 'Total Infaq (Rp)', CASE WHEN k.nama_desa IS NOT NULL THEN '✅ Sudah Setor' ELSE '❌ Belum Setor' END AS 'Status Fisik 11%' FROM setoran_dkm d LEFT JOIN (SELECT DISTINCT nama_desa FROM setoran_kecamatan) k ON d.nama_desa = k.nama_desa GROUP BY d.nama_desa ORDER BY d.nama_desa ASC""", conn)
        except:
            df_rekap = pd.read_sql_query("""SELECT nama_desa AS 'Nama Desa', SUM(jiwa_beras + jiwa_uang) AS 'Total Jiwa', SUM(total_beras) AS 'Total Beras (Kg)', SUM(total_uang) AS 'Total Uang Zakat (Rp)', SUM(infaq) AS 'Total Infaq (Rp)', '❌ Belum Setor' AS 'Status Fisik 11%' FROM setoran_dkm GROUP BY nama_desa ORDER BY nama_desa ASC""", conn)
        
        if not df_rekap.empty:
            df_rekap['Total Uang Zakat (Rp)'] = df_rekap['Total Uang Zakat (Rp)'].apply(format_rupiah)
            df_rekap['Total Infaq (Rp)'] = df_rekap['Total Infaq (Rp)'].apply(format_rupiah)
            st.dataframe(df_rekap, width='stretch', hide_index=True)
        else: 
            st.info("Belum ada data setoran zakat yang masuk dari desa manapun.")

    with tab_qurban:
        st.subheader("🐄 Data Rekapitulasi Hewan Qurban se-Kecamatan")
        try:
            df_q = pd.read_sql_query("SELECT nama_desa AS 'Asal Desa', tahun AS 'Tahun', nama_dkm AS 'Nama DKM', jenis_hewan AS 'Jenis Hewan', jumlah_hewan AS 'Jumlah (Ekor)', jumlah_mudhohi AS 'Jumlah Mudhohi' FROM qurban ORDER BY tahun DESC, nama_desa ASC", conn)
        except:
            df_q = pd.DataFrame()
        if not df_q.empty:
            st.dataframe(df_q, width='stretch', hide_index=True)
        else:
            st.info("Belum ada data Qurban.")

    with tab_majlis:
        st.subheader("🕌 Data Rekapitulasi Majlis Ta'lim se-Kecamatan")
        try:
            df_m = pd.read_sql_query("SELECT nama_desa AS 'Asal Desa', nama_majlis AS 'Nama Majlis Ta\\'lim', pimpinan AS 'Nama Pimpinan' FROM majlis_talim ORDER BY nama_desa ASC", conn)
        except:
            df_m = pd.DataFrame()
        if not df_m.empty:
            st.dataframe(df_m, width='stretch', hide_index=True)
        else:
            st.info("Belum ada data Majlis Ta'lim.")
    conn.close()

elif pilihan_menu == "📥 Setoran UPZ Desa":
    st.title("📥 Pencatatan Setoran Fisik dari UPZ Desa")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nama_desa FROM users WHERE role='desa' OR role='user' ORDER BY nama_desa ASC")
    daftar_desa = [r[0] for r in c.fetchall()]

    s_desa = st.selectbox("Pilih Desa yang Menyetor:", ["Pilih Desa..."] + daftar_desa) if daftar_desa else "Pilih Desa..."

    if s_desa != "Pilih Desa...":
        c.execute("SELECT SUM(total_beras), SUM(total_uang) FROM setoran_dkm WHERE nama_desa=?", (s_desa,))
        tot = c.fetchone()
        tot_beras = tot[0] if tot[0] else 0
        tot_uang = tot[1] if tot[1] else 0
        kec_b = tot_beras * 0.05
        kec_u = tot_uang * 0.05
        kab_b = tot_beras * 0.06
        kab_u = tot_uang * 0.06
        total_setor_b = kec_b + kab_b
        total_setor_u = kec_u + kab_u
        
        st.info(f"💡 **Data Otomatis Ditarik dari {s_desa.upper()}**\n\nTotal Penghimpunan Desa: Beras {tot_beras:,.2f} Kg | Uang {format_rupiah(tot_uang)}\n- Hak Kec. (5%): Beras {kec_b:,.2f} Kg | Uang {format_rupiah(kec_u)}\n- Hak Kab. (6%): Beras {kab_b:,.2f} Kg | Uang {format_rupiah(kab_u)}")

        with st.form("form_setoran_desa"):
            col1, col2 = st.columns(2)
            with col1: 
                s_tgl = st.date_input("Tanggal Penyerahan:", datetime.date.today())
            with col2:
                s_b = st.number_input("Fisik Beras Diserahkan (Kg):", value=float(total_setor_b), step=0.5)
                s_u = st.number_input("Fisik Uang Diserahkan (Rp):", value=int(total_setor_u), step=1000)
            if st.form_submit_button("💾 Konfirmasi & Simpan Bukti Setoran", width='stretch'):
                c.execute("SELECT id FROM setoran_kecamatan WHERE nama_desa=? AND tanggal=?", (s_desa, str(s_tgl)))
                if c.fetchone(): 
                    st.error("⚠️ GAGAL! Data setoran untuk desa ini di tanggal tersebut sudah ada.")
                else:
                    c.execute("INSERT INTO setoran_kecamatan (nama_desa, beras_disetor, uang_disetor, tanggal) VALUES (?,?,?,?)", (s_desa, s_b, s_u, str(s_tgl)))
                    conn.commit()
                    st.success(f"Berhasil!")
                    st.rerun()
    else: 
        st.warning("👈 Pilih nama desa terlebih dahulu.")

    df_set = pd.read_sql_query("SELECT id as ID, tanggal as Tanggal, nama_desa as 'Nama Desa', beras_disetor as 'Beras (Kg)', uang_disetor as 'Uang (Rp)' FROM setoran_kecamatan ORDER BY id DESC", conn)
    if not df_set.empty:
        df_set_disp = df_set.copy()
        df_set_disp['Uang (Rp)'] = df_set_disp['Uang (Rp)'].apply(format_rupiah)
        st.dataframe(df_set_disp, width='stretch', hide_index=True)
        col_del, col_edit = st.columns(2)
        with col_del:
            with st.expander("🗑️ Hapus Setoran"):
                id_hapus = st.number_input("ID Hapus:", min_value=0, step=1, key="del_set_kec")
                if st.button("Hapus Data", key="btn_hapus_set_kec"): 
                    c.execute("DELETE FROM setoran_kecamatan WHERE id=?", (id_hapus,))
                    conn.commit()
                    st.rerun()
        with col_edit:
            with st.expander("✏️ Ubah Setoran"):
                pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Nama Desa']}" for _, r in df_set.iterrows()])
                if pil_edit != "Pilih...":
                    id_e = pil_edit.split(" - ")[0]
                    c.execute("SELECT tanggal, beras_disetor, uang_disetor FROM setoran_kecamatan WHERE id=?", (id_e,))
                    r_e = c.fetchone()
                    if r_e:
                        with st.form("f_edit_set"):
                            es_tgl = st.text_input("Tanggal:", value=r_e[0])
                            es_b = st.number_input("Beras:", value=float(r_e[1]), step=0.5)
                            es_u = st.number_input("Uang:", value=int(r_e[2]), step=1000)
                            if st.form_submit_button("Simpan", width='stretch'):
                                c.execute("UPDATE setoran_kecamatan SET tanggal=?, beras_disetor=?, uang_disetor=? WHERE id=?", (es_tgl, es_b, es_u, id_e))
                                conn.commit()
                                st.rerun()
    conn.close()

elif pilihan_menu == "📤 Distribusi UPZ Kecamatan":
    st.title("📤 Distribusi UPZ Kecamatan")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Kalkulasi Kecamatan (5% Hak Kecamatan)
    c.execute("SELECT SUM(total_beras), SUM(total_uang) FROM setoran_dkm")
    tot_zakat = c.fetchone()
    z_b = tot_zakat[0] or 0.0  
    z_u = tot_zakat[1] or 0.0  
    
    hak_kec_b = z_b * 0.05
    hak_kec_u = z_u * 0.05

    c.execute("SELECT pct_amil_kec FROM pengaturan WHERE nama_desa='KECAMATAN'")
    p_data = c.fetchone()
    p_amil = float(p_data[0] or 12.5) if p_data else 12.5
    p_sab = 100.0 - p_amil
    
    amil_b = hak_kec_b * (p_amil / 100.0)
    amil_u = hak_kec_u * (p_amil / 100.0)
    sab_b = hak_kec_b * (p_sab / 100.0)
    sab_u = hak_kec_u * (p_sab / 100.0)

    # Master Data Bobot Kecamatan
    c.execute("SELECT nama, bobot FROM master_kategori_sab WHERE nama_desa=? ORDER BY nama ASC", (st.session_state["nama_desa"],))
    daftar_sab = c.fetchall()
    tot_bobot_sab = sum([k[1] for k in daftar_sab]) or 1.0

    c.execute("SELECT nama, bobot FROM master_jabatan_amil WHERE nama_desa=? ORDER BY nama ASC", (st.session_state["nama_desa"],))
    daftar_amil = c.fetchall()
    tot_bobot_amil = sum([j[1] for j in daftar_amil]) or 1.0

    tab_sab, tab_amil = st.tabs([f"📌 Asnaf Sabilillah ({p_sab}%)", f"👔 Asnaf Amilin ({p_amil}%)"])
    
    with tab_sab:
        st.info(f"💡 **Total Hak Sabilillah Kecamatan:** Uang {format_rupiah(sab_u)} | Beras {sab_b:.2f} Kg")
        
        if daftar_sab:
            st.write("**Simulasi Pembagian berdasarkan Bobot Master Data:**")
            for k in daftar_sab:
                j_u = sab_u * (k[1] / tot_bobot_sab)
                j_b = sab_b * (k[1] / tot_bobot_sab)
                st.caption(f"- **{k[0]}** (Bobot {k[1]}): Uang {format_rupiah(j_u)} | Beras {j_b:.2f} Kg")

            with st.form("f_auto_sab_kec"):
                if st.form_submit_button("🤖 Distribusikan 100% Sabilillah Otomatis", width='stretch', type="primary"):
                    for k in daftar_sab:
                        j_u = sab_u * (k[1] / tot_bobot_sab)
                        j_b = sab_b * (k[1] / tot_bobot_sab)
                        c.execute("SELECT id FROM distribusi_kec_program WHERE penerima=? AND uang=? AND tanggal=?", (k[0], j_u, str(datetime.date.today())))
                        if not c.fetchone():
                            c.execute("INSERT INTO distribusi_kec_program (program, penerima, beras, uang, tanggal) VALUES (?,?,?,?,?)", ("Sabilillah (Auto)", k[0], j_b, j_u, str(datetime.date.today())))
                    conn.commit()
                    st.success("✅ Distribusi Sabilillah Berhasil Tersimpan!")
                    st.rerun()
        else:
            st.warning("⚠️ Kategori Sabilillah belum diatur. Silakan atur di 'Kelola Data Master'.")

        df_sab = pd.read_sql_query(f"SELECT id as ID, tanggal as Tanggal, program as 'Kategori Program', penerima as 'Nama Penerima', beras as 'Beras (Kg)', uang as 'Uang (Rp)' FROM distribusi_kec_program ORDER BY id DESC", conn)
        if not df_sab.empty:
            df_sab_disp = df_sab.copy()
            df_sab_disp['Uang (Rp)'] = df_sab_disp['Uang (Rp)'].apply(format_rupiah)
            st.dataframe(df_sab_disp, width='stretch', hide_index=True)
            c_del, c_edit = st.columns(2)
            with c_del:
                with st.expander("🗑️ Hapus Data Terpilih"):
                    id_h = st.number_input("ID Baris yang dihapus:", min_value=0, key="dsab_z")
                    if st.button("Hapus", key="btn_h_sab_z"): 
                        c.execute("DELETE FROM distribusi_kec_program WHERE id=?", (id_h,)); conn.commit(); st.rerun()
            with c_edit:
                with st.expander("✏️ Ubah Data Terpilih"):
                    pil_edit = st.selectbox("Pilih Baris:", ["Pilih..."] + [f"{r['ID']} - {r['Nama Penerima']}" for _, r in df_sab.iterrows()], key="esab")
                    if pil_edit != "Pilih...":
                        id_e = pil_edit.split(" - ")[0]
                        c.execute("SELECT program, penerima, beras, uang FROM distribusi_kec_program WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_esab"):
                                e_pr = st.text_input("Kategori Program:", value=r_e[0])
                                e_pe = st.text_input("Nama Penerima:", value=r_e[1])
                                e_b = st.number_input("Beras (Kg):", value=float(r_e[2]), step=0.5)
                                e_u = st.number_input("Uang (Rp):", value=int(r_e[3]), step=1000)
                                if st.form_submit_button("💾 Simpan Perubahan", width='stretch'):
                                    c.execute("UPDATE distribusi_kec_program SET program=?, penerima=?, beras=?, uang=? WHERE id=?", (e_pr, e_pe, e_b, e_u, id_e))
                                    conn.commit(); st.rerun()

    with tab_amil:
        st.info(f"💡 **Total Hak Amil Kecamatan:** Uang {format_rupiah(amil_u)} | Beras {amil_b:.2f} Kg")
        
        if daftar_amil:
            st.write("**Simulasi Pembagian berdasarkan Bobot Master Data:**")
            for j in daftar_amil:
                j_u = amil_u * (j[1] / tot_bobot_amil)
                j_b = amil_b * (j[1] / tot_bobot_amil)
                st.caption(f"- **{j[0]}** (Bobot {j[1]}): Uang {format_rupiah(j_u)} | Beras {j_b:.2f} Kg")

            with st.form("f_auto_amil_kec"):
                if st.form_submit_button("🤖 Distribusikan 100% Amilin Otomatis", width='stretch', type="primary"):
                    for j in daftar_amil:
                        j_u = amil_u * (j[1] / tot_bobot_amil)
                        j_b = amil_b * (j[1] / tot_bobot_amil)
                        c.execute("SELECT id FROM distribusi_kec_amil WHERE nama=? AND uang=? AND tanggal=?", (j[0], j_u, str(datetime.date.today())))
                        if not c.fetchone():
                            c.execute("INSERT INTO distribusi_kec_amil (nama, jabatan, beras, uang, tanggal) VALUES (?,?,?,?,?)", (j[0], "Amilin (Auto)", j_b, j_u, str(datetime.date.today())))
                    conn.commit()
                    st.success("✅ Distribusi Amilin Berhasil Tersimpan!")
                    st.rerun()
        else:
            st.warning("⚠️ Jabatan Amil belum diatur. Silakan atur di 'Kelola Data Master'.")
                        
        df_amil = pd.read_sql_query(f"SELECT id as ID, tanggal as Tanggal, nama as 'Nama Pengurus', jabatan as Jabatan, beras as 'Beras (Kg)', uang as 'Uang (Rp)' FROM distribusi_kec_amil ORDER BY id DESC", conn)
        if not df_amil.empty:
            df_amil_disp = df_amil.copy()
            df_amil_disp['Uang (Rp)'] = df_amil_disp['Uang (Rp)'].apply(format_rupiah)
            st.dataframe(df_amil_disp, width='stretch', hide_index=True)
            
            c_del, c_edit = st.columns(2)
            with c_del:
                with st.expander("🗑️ Hapus Data Terpilih"):
                    id_h = st.number_input("ID Baris yang dihapus:", min_value=0, key="dami")
                    if st.button("Hapus", key="btn_hapus_amil_kec"): 
                        c.execute("DELETE FROM distribusi_kec_amil WHERE id=?", (id_h,)); conn.commit(); st.rerun()
            with c_edit:
                with st.expander("✏️ Ubah Data Terpilih"):
                    pil_edit = st.selectbox("Pilih Baris:", ["Pilih..."] + [f"{r['ID']} - {r['Nama Pengurus']}" for _, r in df_amil.iterrows()], key="eami")
                    if pil_edit != "Pilih...":
                        id_e = pil_edit.split(" - ")[0]
                        c.execute("SELECT nama, jabatan, beras, uang FROM distribusi_kec_amil WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_eami"):
                                e_nm = st.text_input("Nama Pengurus:", value=r_e[0])
                                e_jb = st.text_input("Jabatan:", value=r_e[1])
                                e_b = st.number_input("Beras (Kg):", value=float(r_e[2]), step=0.5)
                                e_u = st.number_input("Uang (Rp):", value=int(r_e[3]), step=1000)
                                if st.form_submit_button("💾 Simpan Perubahan", width='stretch'):
                                    c.execute("UPDATE distribusi_kec_amil SET nama=?, jabatan=?, beras=?, uang=? WHERE id=?", (e_nm, e_jb, e_b, e_u, id_e))
                                    conn.commit(); st.rerun()
    conn.close()

elif pilihan_menu == "📂 Kelola Data Master":
    st.title("📂 Kelola Data Master")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    st.info("💡 **Tips Otomasi:** Atur 'Bobot' (angka pembagi). Saat Bapak klik tombol Distribusikan Otomatis, sistem akan membagi nominal Uang dan Beras secara proporsional berdasar bobot ini.")
    
    is_kecamatan = st.session_state["role"] in ["kecamatan", "admin"]
    
    if is_kecamatan:
        tabs = st.tabs(["📌 Kategori Sabilillah Kecamatan", "👔 Jabatan Amilin Kecamatan"])
        t_sab, t_amil = tabs[0], tabs[1]
    else:
        tabs = st.tabs(["🕌 Master DKM", "📖 Guru Ngaji", "📌 Kategori Sabilillah", "👔 Jabatan Amilin"])
        t_dkm, t_ngaji, t_sab, t_amil = tabs[0], tabs[1], tabs[2], tabs[3]
        
        with t_dkm:
            with st.form("f_dkm"):
                i_nm = st.text_input("Nama UPZ DKM:")
                i_kt = st.text_input("Ketua DKM:")
                i_al = st.text_input("Alamat:")
                i_wk = st.text_input("Perwakilan (Koma):")
                if st.form_submit_button("Simpan Master DKM", width='stretch'):
                    c.execute("SELECT id FROM master_dkm WHERE nama_dkm=? AND nama_desa=?", (i_nm.upper(), st.session_state["nama_desa"]))
                    if c.fetchone():
                        st.error("⚠️ GAGAL! Nama DKM ini sudah terdaftar.")
                    else:
                        c.execute("INSERT INTO master_dkm (nama_dkm, ketua_dkm, alamat_dkm, perwakilan, nama_desa) VALUES (?,?,?,?,?)", (i_nm.upper(), i_kt, i_al, i_wk, st.session_state["nama_desa"]))
                        conn.commit(); st.rerun()
            df_dkm = pd.read_sql_query(f"SELECT id as ID, nama_dkm as DKM, ketua_dkm as Ketua, alamat_dkm as Alamat FROM master_dkm WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
            st.dataframe(df_dkm, width='stretch', hide_index=True)
            if not df_dkm.empty:
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("🗑️ Hapus DKM"):
                        id_h = st.number_input("ID Hapus:", min_value=0, key="d_dkm")
                        if st.button("Hapus", key="b_d_dkm"): 
                            c.execute("DELETE FROM master_dkm WHERE id=?", (id_h,)); conn.commit(); st.rerun()
                with c2:
                    with st.expander("✏️ Edit DKM"):
                        pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['DKM']}" for _, r in df_dkm.iterrows()], key="e_dkm")
                        if pil_e != "Pilih...":
                            id_e = pil_e.split(" - ")[0]
                            c.execute("SELECT nama_dkm, ketua_dkm, alamat_dkm, perwakilan FROM master_dkm WHERE id=?", (id_e,))
                            r_e = c.fetchone()
                            if r_e:
                                with st.form("f_e_dkm"):
                                    e_nm = st.text_input("DKM:", value=r_e[0])
                                    e_kt = st.text_input("Ketua:", value=r_e[1])
                                    e_al = st.text_input("Alamat:", value=r_e[2])
                                    e_wk = st.text_input("Wakil:", value=r_e[3])
                                    if st.form_submit_button("Simpan"):
                                        c.execute("UPDATE master_dkm SET nama_dkm=?, ketua_dkm=?, alamat_dkm=?, perwakilan=? WHERE id=?", (e_nm, e_kt, e_al, e_wk, id_e)); conn.commit(); st.rerun()
            
        with t_ngaji:
            c.execute("SELECT nama_dkm FROM master_dkm WHERE nama_desa=? ORDER BY nama_dkm ASC", (st.session_state["nama_desa"],))
            daftar_dkm = [row[0] for row in c.fetchall()]
            
            with st.form("f_ngaji"):
                n_nm = st.text_input("Nama Pengajar:")
                n_lm = st.text_input("Lembaga / TPQ:")
                n_dk = st.selectbox("Terhubung ke DKM:", ["Pilih DKM..."] + daftar_dkm) if daftar_dkm else st.text_input("DKM Terkait:")
                n_bb = st.number_input("Bobot Hak Infaq (Contoh: 1.0 atau 2.0):", value=1.0, step=0.5)
                if st.form_submit_button("Simpan Guru Ngaji", width='stretch'):
                    c.execute("SELECT id FROM guru_ngaji WHERE nama=? AND lembaga=? AND dkm=? AND nama_desa=?", (n_nm, n_lm, n_dk, st.session_state["nama_desa"]))
                    if c.fetchone():
                        st.error("⚠️ GAGAL! Guru dengan nama dan lembaga tersebut sudah terdaftar.")
                    else:
                        c.execute("INSERT INTO guru_ngaji (nama, lembaga, dkm, bobot, nama_desa) VALUES (?,?,?,?,?)", (n_nm, n_lm, n_dk, n_bb, st.session_state["nama_desa"]))
                        conn.commit(); st.rerun()
            df_ng = pd.read_sql_query(f"SELECT id as ID, nama as Nama, lembaga as Lembaga, dkm as DKM, bobot as Bobot FROM guru_ngaji WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
            st.dataframe(df_ng, width='stretch', hide_index=True)
            if not df_ng.empty:
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("🗑️ Hapus Guru"):
                        id_h = st.number_input("ID Hapus:", min_value=0, key="d_ngaji")
                        if st.button("Hapus", key="b_d_ngaji"): 
                            c.execute("DELETE FROM guru_ngaji WHERE id=?", (id_h,)); conn.commit(); st.rerun()
                with c2:
                    with st.expander("✏️ Edit Guru"):
                        pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Nama']}" for _, r in df_ng.iterrows()], key="e_ngaji")
                        if pil_e != "Pilih...":
                            id_e = pil_e.split(" - ")[0]
                            c.execute("SELECT nama, lembaga, dkm, bobot FROM guru_ngaji WHERE id=?", (id_e,))
                            r_e = c.fetchone()
                            if r_e:
                                with st.form("f_e_ngaji"):
                                    e_nm = st.text_input("Nama:", value=r_e[0])
                                    e_lm = st.text_input("Lembaga:", value=r_e[1])
                                    e_dk = st.text_input("DKM:", value=r_e[2])
                                    e_bb = st.number_input("Bobot:", value=float(r_e[3] or 1.0), step=0.5)
                                    if st.form_submit_button("Simpan"):
                                        c.execute("UPDATE guru_ngaji SET nama=?, lembaga=?, dkm=?, bobot=? WHERE id=?", (e_nm, e_lm, e_dk, e_bb, id_e)); conn.commit(); st.rerun()
            
    with t_sab:
        with st.form("f_ksab"):
            s_nm = st.text_input("Nama Organisasi / Penerima Sabilillah:")
            s_bb = st.number_input("Bobot / Porsi Pembagian:", value=1.0, step=0.5)
            if st.form_submit_button("Simpan Kategori Sabilillah", width='stretch'):
                c.execute("SELECT id FROM master_kategori_sab WHERE nama=? AND nama_desa=?", (s_nm, st.session_state["nama_desa"]))
                if c.fetchone():
                    st.error("⚠️ GAGAL! Nama Organisasi Sabilillah sudah ada.")
                else:
                    c.execute("INSERT INTO master_kategori_sab (nama, bobot, nama_desa) VALUES (?,?,?)", (s_nm, s_bb, st.session_state["nama_desa"]))
                    conn.commit(); st.rerun()
        df_ksab = pd.read_sql_query(f"SELECT id as ID, nama as Kategori, bobot as Bobot FROM master_kategori_sab WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        st.dataframe(df_ksab, width='stretch', hide_index=True)
        if not df_ksab.empty:
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("🗑️ Hapus Kategori"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="d_ksab")
                    if st.button("Hapus", key="b_d_ksab"): 
                        c.execute("DELETE FROM master_kategori_sab WHERE id=?", (id_h,)); conn.commit(); st.rerun()
            with c2:
                with st.expander("✏️ Edit Kategori"):
                    pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Kategori']}" for _, r in df_ksab.iterrows()], key="e_ksab")
                    if pil_e != "Pilih...":
                        id_e = pil_e.split(" - ")[0]
                        c.execute("SELECT nama, bobot FROM master_kategori_sab WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_e_ksab"):
                                e_nm = st.text_input("Kategori:", value=r_e[0])
                                e_bb = st.number_input("Bobot:", value=float(r_e[1]), step=0.5)
                                if st.form_submit_button("Simpan"):
                                    c.execute("UPDATE master_kategori_sab SET nama=?, bobot=? WHERE id=?", (e_nm, e_bb, id_e)); conn.commit(); st.rerun()
            
    with t_amil:
        with st.form("f_jami"):
            a_nm = st.text_input("Jabatan & Nama (Misal: Ketua - Bpk Ahmad):")
            a_bb = st.number_input("Bobot / Porsi Pembagian:", value=1.0, step=0.5)
            if st.form_submit_button("Simpan Pengurus Amil", width='stretch'):
                c.execute("SELECT id FROM master_jabatan_amil WHERE nama=? AND nama_desa=?", (a_nm, st.session_state["nama_desa"]))
                if c.fetchone():
                    st.error("⚠️ GAGAL! Jabatan & Nama Amil tersebut sudah terdaftar.")
                else:
                    c.execute("INSERT INTO master_jabatan_amil (nama, bobot, nama_desa) VALUES (?,?,?)", (a_nm, a_bb, st.session_state["nama_desa"]))
                    conn.commit(); st.rerun()
        df_jami = pd.read_sql_query(f"SELECT id as ID, nama as 'Jabatan & Nama', bobot as Bobot FROM master_jabatan_amil WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        st.dataframe(df_jami, width='stretch', hide_index=True)
        if not df_jami.empty:
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("🗑️ Hapus Jabatan"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="d_jami")
                    if st.button("Hapus", key="b_d_jami"): 
                        c.execute("DELETE FROM master_jabatan_amil WHERE id=?", (id_h,)); conn.commit(); st.rerun()
            with c2:
                with st.expander("✏️ Edit Jabatan"):
                    pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Jabatan & Nama']}" for _, r in df_jami.iterrows()], key="e_jami")
                    if pil_e != "Pilih...":
                        id_e = pil_e.split(" - ")[0]
                        c.execute("SELECT nama, bobot FROM master_jabatan_amil WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_e_jami"):
                                e_nm = st.text_input("Jabatan:", value=r_e[0])
                                e_bb = st.number_input("Bobot:", value=float(r_e[1]), step=0.5)
                                if st.form_submit_button("Simpan"):
                                    c.execute("UPDATE master_jabatan_amil SET nama=?, bobot=? WHERE id=?", (e_nm, e_bb, id_e)); conn.commit(); st.rerun()
    conn.close()

# MENU INI SEMPAT HILANG, SEKARANG SUDAH DIKEMBALIKAN!
elif pilihan_menu == "🖨️ Laporan Rekap Desa":
    st.title("🖨️ Cetak Laporan PDF Kecamatan")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("Atur Surat & Titimangsa")
        no_surat = st.text_input("Nomor Surat (Pengajuan 6%):", value="001/UPZ-KEC/2026")
        tempat_ba = st.text_input("Tempat TTD:", value="Kecamatan")
        tgl_ba = st.text_input("Tanggal Surat:", value="15 Ramadhan 1446")
        
    with col2:
        st.subheader("Daftar Dokumen (Format K)")
        with st.expander("📄 Format K1 (Rekapitulasi 5%)", expanded=True):
            if st.button("🔄 Buat / Perbarui K1", width='stretch'):
                st.session_state['pdf_k1'] = mc.cetak_k1_kecamatan(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_k1' in st.session_state:
                st.download_button("📥 UNDUH PDF K1", data=st.session_state['pdf_k1'], file_name="Format_K1.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("📄 Format K2 (Lap. Mustahik Sabilillah)"):
            if st.button("🔄 Buat / Perbarui K2", width='stretch'):
                st.session_state['pdf_k2'] = mc.cetak_k2_sabilillah(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_k2' in st.session_state:
                st.download_button("📥 UNDUH PDF K2", data=st.session_state['pdf_k2'], file_name="Format_K2.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("📄 Format K3 (Rekapitulasi Program)"):
            if st.button("🔄 Buat / Perbarui K3", width='stretch'):
                st.session_state['pdf_k3'] = mc.cetak_k3_program(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_k3' in st.session_state:
                st.download_button("📥 UNDUH PDF K3", data=st.session_state['pdf_k3'], file_name="Format_K3.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("📄 Format K4 (Daftar Penyaluran Amilin)"):
            if st.button("🔄 Buat / Perbarui K4", width='stretch'):
                st.session_state['pdf_k4'] = mc.cetak_k4_amilin(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_k4' in st.session_state:
                st.download_button("📥 UNDUH PDF K4", data=st.session_state['pdf_k4'], file_name="Format_K4.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("✉️ Surat Pengajuan 6% ke BAZNAS Kab"):
            if st.button("🔄 Buat / Perbarui Surat 6%", width='stretch'):
                st.session_state['pdf_surat6'] = mc.cetak_surat_6persen(DB_NAME, tempat_ba, tgl_ba, no_surat)
            if 'pdf_surat6' in st.session_state:
                st.download_button("📥 UNDUH SURAT 6%", data=st.session_state['pdf_surat6'], file_name="Surat_6Persen.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("🧾 Cetak Kwitansi Kosong"):
            if st.button("🔄 Buat Kwitansi", width='stretch'):
                st.session_state['pdf_kwitansi'] = mc.cetak_kwitansi("Nama Lembaga", 1500000, "Bantuan Sarana", f"{tempat_ba}, {tgl_ba}")
            if 'pdf_kwitansi' in st.session_state:
                st.download_button("📥 UNDUH KWITANSI", data=st.session_state['pdf_kwitansi'], file_name="Kwitansi.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("🐄 Rekap Hewan Qurban (Kecamatan)"):
            if st.button("🔄 Buat Rekap Qurban", width='stretch'):
                st.session_state['pdf_q_kec'] = mc.cetak_rekap_qurban_kec(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_q_kec' in st.session_state:
                st.download_button("📥 UNDUH REKAP QURBAN", data=st.session_state['pdf_q_kec'], file_name="Rekap_Qurban_Kecamatan.pdf", mime="application/pdf", width='stretch')

        with st.expander("🕌 Rekap Majlis Ta'lim (Kecamatan)"):
            if st.button("🔄 Buat Rekap Majlis Ta'lim", width='stretch'):
                st.session_state['pdf_m_kec'] = mc.cetak_rekap_majlis_kec(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_m_kec' in st.session_state:
                st.download_button("📥 UNDUH REKAP MAJLIS", data=st.session_state['pdf_m_kec'], file_name="Rekap_Majlis_Kecamatan.pdf", mime="application/pdf", width='stretch')

elif pilihan_menu == "⚙️ Profil Kecamatan":
    st.title("⚙️ Pengaturan Profil Kecamatan")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nama_kecamatan, kabupaten, ketua_upz, sekretaris, bendahara, pct_amil_kec FROM pengaturan WHERE nama_desa='KECAMATAN'")
    res = c.fetchone()
    v_kec = res[0] if res else ""
    v_kab = res[1] if res else ""
    v_ketua = res[2] if res else ""
    v_sek = res[3] if res else ""
    v_ben = res[4] if res else ""
    v_pa = float(res[5] or 12.5)

    with st.form("form_master_kecamatan"):
        col1, col2 = st.columns(2)
        with col1:
            in_kec = st.text_input("Kecamatan:", value=v_kec)
            in_kab = st.text_input("Kabupaten:", value=v_kab)
            in_ketua = st.text_input("Ketua:", value=v_ketua)
            in_sek = st.text_input("Sekretaris:", value=v_sek)
            in_ben = st.text_input("Bendahara:", value=v_ben)
        with col2:
            st.subheader("Pintu Utama Hak Pengelolaan")
            st.caption("UPZ Kecamatan mengelola 5% dari total keseluruhan Zakat/Fitrah Desa.")
            i_pa = st.number_input("Hak Amil (%):", value=float(v_pa), help="Sisanya otomatis menjadi Sabilillah.")
            st.markdown(f"**Hak Sabilillah Otomatis: {(100 - float(v_pa)):.1f}%**")
            st.info("💡 **Info:** Untuk membagikan dana Sabilillah dan dana Amil, atur nama Penerima & Bobot-nya di menu **📂 Kelola Data Master** terlebih dahulu.")
            
        if st.form_submit_button("💾 Simpan", width='stretch'):
            c.execute("""UPDATE pengaturan SET nama_kecamatan=?, kabupaten=?, ketua_upz=?, sekretaris=?, bendahara=?, pct_amil_kec=? WHERE nama_desa='KECAMATAN'""", (in_kec, in_kab, in_ketua, in_sek, in_ben, i_pa))
            conn.commit()
            st.success("✅ Pengaturan berhasil disimpan!")
            st.rerun()
    conn.close()

elif pilihan_menu == "👥 Kelola Pengguna":
    st.title("👥 Kelola Akun")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    with st.form("form_user"):
        c1, c2 = st.columns(2)
        with c1: 
            u_desa = st.text_input("Nama Desa:")
            u_name = st.text_input("Username:")
        with c2: 
            u_pass = st.text_input("Password:")
            u_role = st.selectbox("Akses:", ["desa", "kecamatan", "user", "admin"])
        if st.form_submit_button("💾 Simpan", width='stretch'):
            if u_name and u_pass:
                c.execute("SELECT id FROM users WHERE username=?", (u_name,))
                if c.fetchone():
                    st.error("⚠️ GAGAL! Username tersebut sudah digunakan. Pilih username lain.")
                else:
                    c.execute("INSERT INTO users (username, password, role, nama_desa) VALUES (?,?,?,?)", (u_name, u_pass, u_role, u_desa))
                    conn.commit()
                    st.rerun()
    df_u = pd.read_sql_query("SELECT id as ID, username as Username, password as Password, role as Akses, nama_desa as Desa FROM users", conn)
    st.dataframe(df_u, width='stretch', hide_index=True)
    col_del, col_edit = st.columns(2)
    with col_del:
        with st.expander("🗑️ Hapus Akun"):
            id_h = st.number_input("ID Hapus Akun:", min_value=0, step=1, key="id_hapus_akun")
            if st.button("Hapus Akun", key="btn_hapus_akun"): 
                c.execute("DELETE FROM users WHERE id=?", (id_h,))
                conn.commit()
                st.rerun()
    with col_edit:
        with st.expander("✏️ Ubah Akun"):
            pil_edit = st.selectbox("Pilih Akun:", ["Pilih..."] + [f"{r['ID']} - {r['Username']}" for _, r in df_u.iterrows()], key="e_user")
            if pil_edit != "Pilih...":
                id_e = pil_edit.split(" - ")[0]
                c.execute("SELECT username, password, role, nama_desa FROM users WHERE id=?", (id_e,))
                r_e = c.fetchone()
                if r_e:
                    with st.form("f_e_user"):
                        e_usr = st.text_input("Username:", value=r_e[0])
                        e_pass = st.text_input("Password:", value=r_e[1])
                        e_role = st.selectbox("Akses:", ["desa", "kecamatan", "user", "admin"], index=["desa", "kecamatan", "user", "admin"].index(r_e[2]))
                        e_ds = st.text_input("Nama Desa:", value=r_e[3])
                        if st.form_submit_button("Simpan Perubahan", width='stretch'):
                            c.execute("UPDATE users SET username=?, password=?, role=?, nama_desa=? WHERE id=?", (e_usr, e_pass, e_role, e_ds, id_e))
                            conn.commit()
                            st.rerun()
    conn.close()

# =========================================================================
# =========================== HALAMAN KHUSUS DESA =========================
# =========================================================================
elif pilihan_menu == "📊 Dashboard Utama":
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT SUM(total_beras), SUM(total_uang), SUM(infaq), SUM(jiwa_beras), SUM(jiwa_uang) FROM setoran_dkm WHERE nama_desa=?", (st.session_state["nama_desa"],))
    himpun = c.fetchone()
    t_beras = himpun[0] or 0
    t_uang = himpun[1] or 0
    t_infaq = himpun[2] or 0
    j_beras = himpun[3] or 0
    j_uang = himpun[4] or 0
    st.title(f"📊 DASHBOARD AMIL DESA {st.session_state['nama_desa'].upper()}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Muzakki", f"{j_beras + j_uang} Jiwa")
    col2.metric("Total Beras", f"{t_beras:,.2f} Kg")
    col3.metric("Total Uang Zakat", format_rupiah(t_uang))
    col4.metric("Total Infaq", format_rupiah(t_infaq))
    
    st.subheader("Daftar Setoran per UPZ DKM")
    df_dkm = pd.read_sql_query(f"SELECT nama_dkm AS 'Nama DKM / Wakil', (jiwa_beras + jiwa_uang) AS 'Total Jiwa', total_beras AS 'Total Beras (Kg)', total_uang AS 'Total Uang Zakat (Rp)', infaq AS 'Total Infaq (Rp)' FROM setoran_dkm WHERE nama_desa = '{st.session_state['nama_desa']}' ORDER BY nama_dkm ASC", conn)
    if not df_dkm.empty:
        df_dkm['Total Uang Zakat (Rp)'] = df_dkm['Total Uang Zakat (Rp)'].apply(format_rupiah)
        df_dkm['Total Infaq (Rp)'] = df_dkm['Total Infaq (Rp)'].apply(format_rupiah)
    st.dataframe(df_dkm, width='stretch', hide_index=True)
    conn.close()

elif pilihan_menu == "📥 Penerimaan Zakat":
    st.title("📥 Penerimaan Zakat & Infaq DKM")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nama_dkm FROM master_dkm WHERE nama_desa=? ORDER BY nama_dkm ASC", (st.session_state["nama_desa"],))
    daftar_dkm = [row[0] for row in c.fetchall()]
    c.execute("SELECT tarif_beras, tarif_uang, nominal_kupon FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
    res_tarif = c.fetchone()
    t_b = float(res_tarif[0]) if res_tarif and res_tarif[0] else 2.5
    t_u = float(res_tarif[1]) if res_tarif and res_tarif[1] else 35000
    nom_kupon = float(res_tarif[2]) if res_tarif and res_tarif[2] else 2000.0

    selected_dkm = st.selectbox("Pilih UPZ DKM Induk:", ["Pilih DKM..."] + daftar_dkm) if daftar_dkm else st.text_input("Nama UPZ DKM Induk:")
    with st.form("form_penerimaan"):
        col1, col2 = st.columns(2)
        with col1: 
            alamat_dkm = st.text_input("Alamat Pusat DKM:")
            alamat_wakil = st.text_input("Alamat Wakil:")
        with col2: 
            wakil_upz = st.text_input("Wakil UPZ:")
        
        mode_input = st.radio("Metode Input:", ["Berdasarkan Data Jiwa", "Berdasarkan Setoran Fisik"], horizontal=True)
        cz, ci = st.columns(2)
        with cz:
            j_b = st.number_input("Muzakki Beras (Jiwa):", min_value=0, value=0)
            j_u = st.number_input("Muzakki Uang (Jiwa):", min_value=0, value=0)
            f_b = st.number_input("Fisik Beras (Kg):", min_value=0.0, value=0.0, step=0.5)
            f_u = st.number_input("Fisik Uang (Rp):", min_value=0, value=0, step=1000)
        with ci:
            k_diterima = st.number_input("Kupon Diterima:", min_value=0, value=0)
            k_terjual = st.number_input("Kupon Terjual:", min_value=0, value=0)
            k_kembali = st.number_input("Kupon Kembali:", min_value=0, value=0)
            infaq_uang = st.number_input("Uang Infaq Tunai (Rp):", min_value=0, value=0)

        if st.form_submit_button("💾 Simpan", width='stretch'):
            c.execute("SELECT id FROM setoran_dkm WHERE nama_dkm=? AND nama_desa=?", (selected_dkm, st.session_state["nama_desa"]))
            if c.fetchone():
                st.error(f"⚠️ GAGAL! Data setoran untuk DKM '{selected_dkm}' sudah ada. Silakan gunakan fitur EDIT di bawah.")
            else:
                tipe_input = "jiwa" if mode_input == "Berdasarkan Data Jiwa" else "fisik"
                if tipe_input == "jiwa": 
                    tb = j_b * t_b; tu = j_u * t_u; fb = tb * 0.175; fu = tu * 0.175; jiwa_b=j_b; jiwa_u=j_u
                else:
                    fb = f_b; fu = f_u; tb = fb / 0.175 if fb > 0 else 0; tu = fu / 0.175 if fu > 0 else 0
                    jiwa_b = int(round(tb / t_b)) if t_b > 0 else 0; jiwa_u = int(round(tu / t_u)) if t_u > 0 else 0
                
                infaq_rp = float(infaq_uang) + float(k_terjual * nom_kupon)
                
                c.execute('''INSERT INTO setoran_dkm (nama_dkm, alamat_dkm, perwakilan, alamat_perwakilan, tipe_input, jiwa_beras, jiwa_uang, fisik_beras, fisik_uang, total_beras, total_uang, infaq, kupon_diterima, kupon_terjual, kupon_kembali, nama_desa) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (selected_dkm, alamat_dkm, wakil_upz, alamat_wakil, tipe_input, jiwa_b, jiwa_u, fb, fu, tb, tu, infaq_rp, k_diterima, k_terjual, k_kembali, st.session_state["nama_desa"]))
                conn.commit()
                st.success("✅ Tersimpan!")
                st.rerun()

    df_setoran = pd.read_sql_query(f"SELECT id as 'ID', nama_dkm as 'Nama DKM', (jiwa_beras + jiwa_uang) as 'Total Jiwa', total_beras as 'Beras (Kg)', total_uang as 'Uang (Rp)', infaq as 'Infaq (Rp)' FROM setoran_dkm WHERE nama_desa = '{st.session_state['nama_desa']}' ORDER BY id DESC", conn)
    if not df_setoran.empty:
        df_sd = df_setoran.copy()
        df_sd['Uang (Rp)'] = df_sd['Uang (Rp)'].apply(format_rupiah)
        df_sd['Infaq (Rp)'] = df_sd['Infaq (Rp)'].apply(format_rupiah)
        st.dataframe(df_sd, width='stretch', hide_index=True)
        col_del, col_edit = st.columns(2)
        with col_del:
            with st.expander("🗑️ Hapus Setoran"):
                id_hapus = st.number_input("ID Hapus:", min_value=0, step=1, key="del_pen_desa")
                if st.button("Hapus Setoran", key="btn_hapus_pen_desa"): 
                    c.execute("DELETE FROM setoran_dkm WHERE id=?", (id_hapus,))
                    conn.commit()
                    st.rerun()
        with col_edit:
            with st.expander("✏️ Ubah Total Infaq & Kupon"):
                pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Nama DKM']}" for _, r in df_setoran.iterrows()], key="e_pen_desa")
                if pil_edit != "Pilih...":
                    id_e = pil_edit.split(" - ")[0]
                    c.execute("SELECT kupon_terjual, infaq FROM setoran_dkm WHERE id=?", (id_e,))
                    r_e = c.fetchone()
                    if r_e:
                        uang_cash_lama = float(r_e[1]) - float(r_e[0] * nom_kupon) if float(r_e[1]) >= float(r_e[0] * nom_kupon) else float(r_e[1])
                        with st.form("f_e_pen_desa"):
                            st.info("Edit nilai Kupon dan Tunai untuk menyesuaikan Total Infaq.")
                            e_kupon = st.number_input("Kupon Terjual Baru:", value=int(r_e[0]))
                            e_tunai = st.number_input("Uang Infaq Tunai Baru (Rp):", value=int(uang_cash_lama), step=1000)
                            if st.form_submit_button("Simpan Perubahan Infaq", width='stretch'):
                                in_rp_baru = float(e_tunai) + float(e_kupon * nom_kupon)
                                c.execute("UPDATE setoran_dkm SET kupon_terjual=?, infaq=? WHERE id=?", (e_kupon, in_rp_baru, id_e))
                                conn.commit()
                                st.rerun()
    conn.close()

elif pilihan_menu == "📤 Distribusi UPZ":
    st.title("📤 Distribusi UPZ Desa")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Kalkulasi Desa (6,5% Hak Desa)
    c.execute("SELECT SUM(total_beras), SUM(total_uang) FROM setoran_dkm WHERE nama_desa=?", (st.session_state["nama_desa"],))
    tot_zakat = c.fetchone()
    z_b = tot_zakat[0] or 0.0  
    z_u = tot_zakat[1] or 0.0  
    
    hak_desa_b = z_b * 0.065
    hak_desa_u = z_u * 0.065

    c.execute("SELECT pct_amil_desa FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
    p_desa = c.fetchone()
    p_amil = float(p_desa[0] or 12.5) if p_desa else 12.5
    p_sab = 100.0 - p_amil
    
    amil_b = hak_desa_b * (p_amil / 100.0)
    amil_u = hak_desa_u * (p_amil / 100.0)
    sab_b = hak_desa_b * (p_sab / 100.0)
    sab_u = hak_desa_u * (p_sab / 100.0)

    # Ambil Data Master untuk Kategori & Jabatan beserta bobotnya
    c.execute("SELECT nama, bobot FROM master_kategori_sab WHERE nama_desa=? ORDER BY nama ASC", (st.session_state["nama_desa"],))
    daftar_sab = c.fetchall()
    tot_bobot_sab = sum([k[1] for k in daftar_sab]) or 1.0

    c.execute("SELECT nama, bobot FROM master_jabatan_amil WHERE nama_desa=? ORDER BY nama ASC", (st.session_state["nama_desa"],))
    daftar_amil = c.fetchall()
    tot_bobot_amil = sum([j[1] for j in daftar_amil]) or 1.0

    c.execute("SELECT nama_dkm FROM master_dkm WHERE nama_desa=? ORDER BY nama_dkm ASC", (st.session_state["nama_desa"],))
    list_dkm = [r[0] for r in c.fetchall()]

    tab_sab, tab_infaq, tab_amil = st.tabs([f"📌 Asnaf Sabilillah Zakat ({p_sab}%)", "📖 Insentif Guru Ngaji (Infaq)", f"👔 Asnaf Amilin ({p_amil}%)"])
    
    # ================= TAB SABILILLAH (ZAKAT) =================
    with tab_sab:
        st.info(f"💡 **PANDUAN ANGGARAN:**\n"
                f"- **Total Setoran Zakat (100%):** Uang {format_rupiah(z_u)} | Beras {z_b:.2f} Kg\n"
                f"- **Hak Pengelolaan UPZ Desa (6,5%):** Uang {format_rupiah(hak_desa_u)} | Beras {hak_desa_b:.2f} Kg\n"
                f"- **Total Hak Sabilillah ({p_sab}% dari Hak Desa):** Uang {format_rupiah(sab_u)} | Beras {sab_b:.2f} Kg")
        
        if daftar_sab:
            st.write("**Simulasi Pembagian berdasarkan Bobot Master Data:**")
            for k in daftar_sab:
                j_u = sab_u * (k[1] / tot_bobot_sab)
                j_b = sab_b * (k[1] / tot_bobot_sab)
                st.caption(f"- **{k[0]}** (Bobot {k[1]}): Uang {format_rupiah(j_u)} | Beras {j_b:.2f} Kg")

            with st.form("f_auto_sab"):
                if st.form_submit_button("🤖 Distribusikan 100% Sabilillah Otomatis", width='stretch', type="primary"):
                    for k in daftar_sab:
                        j_u = sab_u * (k[1] / tot_bobot_sab)
                        j_b = sab_b * (k[1] / tot_bobot_sab)
                        c.execute("SELECT id FROM sabilillah WHERE penerima=? AND uang=? AND nama_desa=?", (k[0], j_u, st.session_state["nama_desa"]))
                        if not c.fetchone():
                            c.execute("INSERT INTO sabilillah (program, penerima, beras, uang, nama_desa) VALUES (?,?,?,?,?)", ("Sabilillah (Auto)", k[0], j_b, j_u, st.session_state["nama_desa"]))
                    conn.commit()
                    st.success("✅ Distribusi Sabilillah Berhasil Tersimpan!")
                    st.rerun()
        else:
            st.warning("⚠️ Kategori Sabilillah belum diatur di 'Kelola Data Master'.")

        df_sab = pd.read_sql_query(f"SELECT id as ID, program as 'Kategori Program', penerima as 'Nama Penerima', beras as 'Beras (Kg)', uang as 'Uang (Rp)' FROM sabilillah WHERE nama_desa='{st.session_state['nama_desa']}' AND program != 'Insentif Guru Ngaji' ORDER BY id DESC", conn)
        if not df_sab.empty:
            df_sab_disp = df_sab.copy()
            df_sab_disp['Uang (Rp)'] = df_sab_disp['Uang (Rp)'].apply(format_rupiah)
            st.dataframe(df_sab_disp, width='stretch', hide_index=True)
            c_del, c_edit = st.columns(2)
            with c_del:
                with st.expander("🗑️ Hapus Data Terpilih"):
                    id_h = st.number_input("ID Baris yang dihapus:", min_value=0, key="dsab_z")
                    if st.button("Hapus", key="btn_h_sab_z"): 
                        c.execute("DELETE FROM sabilillah WHERE id=?", (id_h,)); conn.commit(); st.rerun()
            with c_edit:
                with st.expander("✏️ Ubah Data Terpilih"):
                    pil_edit = st.selectbox("Pilih Baris:", ["Pilih..."] + [f"{r['ID']} - {r['Nama Penerima']}" for _, r in df_sab.iterrows()], key="esab")
                    if pil_edit != "Pilih...":
                        id_e = pil_edit.split(" - ")[0]
                        c.execute("SELECT program, penerima, beras, uang FROM sabilillah WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_esab"):
                                e_pr = st.text_input("Kategori Program:", value=r_e[0])
                                e_pe = st.text_input("Nama Penerima:", value=r_e[1])
                                e_b = st.number_input("Beras (Kg):", value=float(r_e[2]), step=0.5)
                                e_u = st.number_input("Uang (Rp):", value=int(r_e[3]), step=1000)
                                if st.form_submit_button("💾 Simpan Perubahan", width='stretch'):
                                    c.execute("UPDATE sabilillah SET program=?, penerima=?, beras=?, uang=? WHERE id=?", (e_pr, e_pe, e_b, e_u, id_e))
                                    conn.commit(); st.rerun()

    # ================= TAB INFAQ (GURU NGAJI) =================
    with tab_infaq:
        st.info("💡 **Insentif Guru Ngaji dibagikan 100% murni dari Uang Infaq DKM.**\nSistem akan otomatis memecah total uang infaq DKM sesuai **Bobot Hak** masing-masing guru ngaji yang terdaftar di DKM tersebut.")
        
        dkm_guru = st.selectbox("Pilih DKM untuk pencairan Infaq Guru Ngaji:", ["Pilih DKM..."] + list_dkm)
        
        if dkm_guru != "Pilih DKM...":
            c.execute("SELECT SUM(infaq) FROM setoran_dkm WHERE nama_dkm=? AND nama_desa=?", (dkm_guru, st.session_state["nama_desa"]))
            tot_infaq_dkm = c.fetchone()[0] or 0
            
            c.execute("SELECT nama, bobot FROM guru_ngaji WHERE dkm=? AND nama_desa=?", (dkm_guru, st.session_state["nama_desa"]))
            gurus = c.fetchall()
            tot_b_guru = sum([g[1] for g in gurus]) or 1.0
            
            st.metric(f"Total 100% Infaq Terkumpul di {dkm_guru}", format_rupiah(tot_infaq_dkm))
            
            if not gurus:
                st.warning(f"⚠️ Belum ada Guru Ngaji yang terdaftar di DKM {dkm_guru}. Silakan daftarkan di menu Master.")
            elif tot_infaq_dkm <= 0:
                st.warning(f"⚠️ DKM {dkm_guru} belum menyetorkan Uang Infaq.")
            else:
                st.write("**Simulasi Pembagian berdasarkan Bobot Hak Guru:**")
                for g in gurus:
                    j_u = tot_infaq_dkm * (g[1] / tot_b_guru)
                    st.caption(f"- **{g[0]}** (Bobot {g[1]}): {format_rupiah(j_u)}")
                    
                with st.form("f_auto_guru"):
                    if st.form_submit_button("🤖 Distribusikan 100% Infaq Otomatis", width='stretch', type="primary"):
                        for g in gurus:
                            j_u = tot_infaq_dkm * (g[1] / tot_b_guru)
                            c.execute("SELECT id FROM sabilillah WHERE program=? AND penerima=? AND uang=? AND nama_desa=?", ("Insentif Guru Ngaji", g[0], j_u, st.session_state["nama_desa"]))
                            if not c.fetchone():
                                c.execute("INSERT INTO sabilillah (program, penerima, beras, uang, nama_desa) VALUES (?,?,?,?,?)", ("Insentif Guru Ngaji", g[0], 0, j_u, st.session_state["nama_desa"]))
                        conn.commit()
                        st.success("✅ Dana Infaq berhasil dibagikan!")
                        st.rerun()

        st.markdown("---")
        df_guru = pd.read_sql_query(f"SELECT id as ID, penerima as 'Nama Guru Ngaji', uang as 'Uang Insentif (Infaq)' FROM sabilillah WHERE nama_desa='{st.session_state['nama_desa']}' AND program = 'Insentif Guru Ngaji' ORDER BY id DESC", conn)
        if not df_guru.empty:
            df_g_disp = df_guru.copy()
            df_g_disp['Uang Insentif (Infaq)'] = df_g_disp['Uang Insentif (Infaq)'].apply(format_rupiah)
            st.dataframe(df_g_disp, width='stretch', hide_index=True)
            c_del, c_edit = st.columns(2)
            with c_del:
                with st.expander("🗑️ Hapus Riwayat"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="dguru")
                    if st.button("Hapus", key="btn_h_guru"): 
                        c.execute("DELETE FROM sabilillah WHERE id=?", (id_h,)); conn.commit(); st.rerun()

    # ================= TAB AMILIN (ZAKAT) =================
    with tab_amil:
        st.info(f"💡 **Total Hak Amil Desa ({p_amil}% dari Hak Desa 6,5%):** Uang {format_rupiah(amil_u)} | Beras {amil_b:.2f} Kg")
        
        if daftar_amil:
            st.write("**Simulasi Pembagian berdasarkan Bobot Master Data:**")
            for j in daftar_amil:
                j_u = amil_u * (j[1] / tot_bobot_amil)
                j_b = amil_b * (j[1] / tot_bobot_amil)
                st.caption(f"- **{j[0]}** (Bobot {j[1]}): Uang {format_rupiah(j_u)} | Beras {j_b:.2f} Kg")

            with st.form("f_auto_amil"):
                if st.form_submit_button("🤖 Distribusikan 100% Amilin Otomatis", width='stretch', type="primary"):
                    for j in daftar_amil:
                        j_u = amil_u * (j[1] / tot_bobot_amil)
                        j_b = amil_b * (j[1] / tot_bobot_amil)
                        c.execute("SELECT id FROM amilin WHERE nama=? AND uang=? AND nama_desa=?", (j[0], j_u, st.session_state["nama_desa"]))
                        if not c.fetchone():
                            c.execute("INSERT INTO amilin (nama, jabatan, beras, uang, nama_desa) VALUES (?,?,?,?,?)", (j[0], "Amilin (Auto)", j_b, j_u, st.session_state["nama_desa"]))
                    conn.commit()
                    st.success("✅ Distribusi Amilin Berhasil Tersimpan!")
                    st.rerun()
        else:
            st.warning("⚠️ Jabatan Amil belum diatur. Silakan atur di 'Kelola Data Master'.")
                        
        df_amil = pd.read_sql_query(f"SELECT id as ID, nama as 'Nama Pengurus', jabatan as Jabatan, beras as 'Beras (Kg)', uang as 'Uang (Rp)' FROM amilin WHERE nama_desa='{st.session_state['nama_desa']}' ORDER BY id DESC", conn)
        if not df_amil.empty:
            df_amil_disp = df_amil.copy()
            df_amil_disp['Uang (Rp)'] = df_amil_disp['Uang (Rp)'].apply(format_rupiah)
            st.dataframe(df_amil_disp, width='stretch', hide_index=True)
            
            c_del, c_edit = st.columns(2)
            with c_del:
                with st.expander("🗑️ Hapus Data Terpilih"):
                    id_h = st.number_input("ID Baris yang dihapus:", min_value=0, key="dami")
                    if st.button("Hapus", key="btn_hapus_amil_desa"): 
                        c.execute("DELETE FROM amilin WHERE id=?", (id_h,)); conn.commit(); st.rerun()
            with c_edit:
                with st.expander("✏️ Ubah Data Terpilih"):
                    pil_edit = st.selectbox("Pilih Baris:", ["Pilih..."] + [f"{r['ID']} - {r['Nama Pengurus']}" for _, r in df_amil.iterrows()], key="eami")
                    if pil_edit != "Pilih...":
                        id_e = pil_edit.split(" - ")[0]
                        c.execute("SELECT nama, jabatan, beras, uang FROM amilin WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_eami"):
                                e_nm = st.text_input("Nama Pengurus:", value=r_e[0])
                                e_jb = st.text_input("Jabatan:", value=r_e[1])
                                e_b = st.number_input("Beras (Kg):", value=float(r_e[2]), step=0.5)
                                e_u = st.number_input("Uang (Rp):", value=int(r_e[3]), step=1000)
                                if st.form_submit_button("💾 Simpan Perubahan", width='stretch'):
                                    c.execute("UPDATE amilin SET nama=?, jabatan=?, beras=?, uang=? WHERE id=?", (e_nm, e_jb, e_b, e_u, id_e))
                                    conn.commit(); st.rerun()
    conn.close()

elif pilihan_menu == "🐄 Data Qurban":
    st.title("🐄 Data Hewan Qurban")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try: 
        c.execute("SELECT nama_dkm FROM master_dkm WHERE nama_desa=? ORDER BY nama_dkm ASC", (st.session_state["nama_desa"],))
        daftar_dkm = [row[0] for row in c.fetchall()]
    except: 
        daftar_dkm = []
        
    with st.form("form_qurban"):
        col1, col2 = st.columns(2)
        with col1:
            in_tahun = st.text_input("Tahun:", value=str(datetime.datetime.now().year))
            in_dkm = st.selectbox("DKM / Wilayah:", ["Pilih..."] + daftar_dkm) if daftar_dkm else st.text_input("DKM:")
            in_jenis = st.selectbox("Jenis Hewan:", ["Sapi", "Domba", "Kambing", "Kerbau"])
        with col2:
            in_hewan = st.number_input("Jumlah Hewan (Ekor):", min_value=0, value=0)
            in_mudhohi = st.number_input("Jumlah Mudhohi (Orang):", min_value=0, value=0, help="0 = hitung otomatis")
        if st.form_submit_button("Simpan Data Qurban", width='stretch'):
            c.execute("SELECT id FROM qurban WHERE tahun=? AND nama_dkm=? AND jenis_hewan=? AND nama_desa=?", (in_tahun, in_dkm, in_jenis, st.session_state["nama_desa"]))
            if c.fetchone():
                st.error(f"⚠️ GAGAL! Laporan hewan {in_jenis} untuk DKM '{in_dkm}' tahun {in_tahun} sudah ada.")
            else:
                if in_mudhohi == 0: 
                    in_mudhohi = in_hewan * (7 if in_jenis in ["Sapi", "Kerbau"] else 1)
                c.execute("INSERT INTO qurban (tahun, nama_dkm, jenis_hewan, jumlah_hewan, jumlah_mudhohi, nama_desa) VALUES (?,?,?,?,?,?)", (in_tahun, in_dkm, in_jenis, in_hewan, in_mudhohi, st.session_state["nama_desa"]))
                conn.commit()
                st.rerun()
            
    df_qurban = pd.read_sql_query(f"SELECT id as ID, tahun as Tahun, nama_dkm as DKM, jenis_hewan as Hewan, jumlah_hewan as Ekor, jumlah_mudhohi as Mudhohi FROM qurban WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
    if not df_qurban.empty: 
        st.dataframe(df_qurban, width='stretch', hide_index=True)
        col_del, col_edit = st.columns(2)
        with col_del:
            with st.expander("🗑️ Hapus Data Qurban"):
                id_h = st.number_input("ID Hapus:", min_value=0, key="id_hapus_qurban")
                if st.button("Hapus Data", key="btn_hapus_qurban"): 
                    c.execute("DELETE FROM qurban WHERE id=?", (id_h,))
                    conn.commit()
                    st.rerun()
        with col_edit:
            with st.expander("✏️ Ubah Data Qurban"):
                pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['DKM']}" for _, r in df_qurban.iterrows()], key="e_qurban")
                if pil_edit != "Pilih...":
                    id_e = pil_edit.split(" - ")[0]
                    c.execute("SELECT tahun, nama_dkm, jenis_hewan, jumlah_hewan, jumlah_mudhohi FROM qurban WHERE id=?", (id_e,))
                    r_e = c.fetchone()
                    if r_e:
                        with st.form("f_e_qurban"):
                            e_th = st.text_input("Tahun:", value=r_e[0])
                            e_dkm = st.text_input("DKM:", value=r_e[1])
                            e_jns = st.selectbox("Jenis Hewan:", ["Sapi", "Domba", "Kambing", "Kerbau"], index=["Sapi", "Domba", "Kambing", "Kerbau"].index(r_e[2]))
                            e_hwn = st.number_input("Ekor:", value=int(r_e[3]))
                            e_mud = st.number_input("Mudhohi:", value=int(r_e[4]))
                            if st.form_submit_button("Simpan Perubahan", width='stretch'):
                                c.execute("UPDATE qurban SET tahun=?, nama_dkm=?, jenis_hewan=?, jumlah_hewan=?, jumlah_mudhohi=? WHERE id=?", (e_th, e_dkm, e_jns, e_hwn, e_mud, id_e))
                                conn.commit()
                                st.rerun()
    conn.close()

elif pilihan_menu == "📂 Kelola Data Master":
    st.title("📂 Kelola Data Master")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    st.info("💡 **Tips Otomasi:** Atur 'Bobot' (angka pembagi). Saat Bapak klik tombol Distribusikan Otomatis, sistem akan membagi nominal Uang dan Beras secara proporsional berdasar bobot ini.")
    
    is_kecamatan = st.session_state["role"] in ["kecamatan", "admin"]
    
    if is_kecamatan:
        tabs = st.tabs(["📌 Kategori Sabilillah Kecamatan", "👔 Jabatan Amilin Kecamatan"])
        t_sab, t_amil = tabs[0], tabs[1]
    else:
        tabs = st.tabs(["🕌 Master DKM", "📖 Guru Ngaji", "📌 Kategori Sabilillah", "👔 Jabatan Amilin"])
        t_dkm, t_ngaji, t_sab, t_amil = tabs[0], tabs[1], tabs[2], tabs[3]
        
        with t_dkm:
            with st.form("f_dkm"):
                i_nm = st.text_input("Nama UPZ DKM:")
                i_kt = st.text_input("Ketua DKM:")
                i_al = st.text_input("Alamat:")
                i_wk = st.text_input("Perwakilan (Koma):")
                if st.form_submit_button("Simpan Master DKM", width='stretch'):
                    c.execute("SELECT id FROM master_dkm WHERE nama_dkm=? AND nama_desa=?", (i_nm.upper(), st.session_state["nama_desa"]))
                    if c.fetchone():
                        st.error("⚠️ GAGAL! Nama DKM ini sudah terdaftar.")
                    else:
                        c.execute("INSERT INTO master_dkm (nama_dkm, ketua_dkm, alamat_dkm, perwakilan, nama_desa) VALUES (?,?,?,?,?)", (i_nm.upper(), i_kt, i_al, i_wk, st.session_state["nama_desa"]))
                        conn.commit(); st.rerun()
            df_dkm = pd.read_sql_query(f"SELECT id as ID, nama_dkm as DKM, ketua_dkm as Ketua, alamat_dkm as Alamat FROM master_dkm WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
            st.dataframe(df_dkm, width='stretch', hide_index=True)
            if not df_dkm.empty:
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("🗑️ Hapus DKM"):
                        id_h = st.number_input("ID Hapus:", min_value=0, key="d_dkm")
                        if st.button("Hapus", key="b_d_dkm"): 
                            c.execute("DELETE FROM master_dkm WHERE id=?", (id_h,)); conn.commit(); st.rerun()
                with c2:
                    with st.expander("✏️ Edit DKM"):
                        pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['DKM']}" for _, r in df_dkm.iterrows()], key="e_dkm")
                        if pil_e != "Pilih...":
                            id_e = pil_e.split(" - ")[0]
                            c.execute("SELECT nama_dkm, ketua_dkm, alamat_dkm, perwakilan FROM master_dkm WHERE id=?", (id_e,))
                            r_e = c.fetchone()
                            if r_e:
                                with st.form("f_e_dkm"):
                                    e_nm = st.text_input("DKM:", value=r_e[0])
                                    e_kt = st.text_input("Ketua:", value=r_e[1])
                                    e_al = st.text_input("Alamat:", value=r_e[2])
                                    e_wk = st.text_input("Wakil:", value=r_e[3])
                                    if st.form_submit_button("Simpan"):
                                        c.execute("UPDATE master_dkm SET nama_dkm=?, ketua_dkm=?, alamat_dkm=?, perwakilan=? WHERE id=?", (e_nm, e_kt, e_al, e_wk, id_e)); conn.commit(); st.rerun()
            
        with t_ngaji:
            c.execute("SELECT nama_dkm FROM master_dkm WHERE nama_desa=? ORDER BY nama_dkm ASC", (st.session_state["nama_desa"],))
            daftar_dkm = [row[0] for row in c.fetchall()]
            
            with st.form("f_ngaji"):
                n_nm = st.text_input("Nama Pengajar:")
                n_lm = st.text_input("Lembaga / TPQ:")
                n_dk = st.selectbox("Terhubung ke DKM:", ["Pilih DKM..."] + daftar_dkm) if daftar_dkm else st.text_input("DKM Terkait:")
                n_bb = st.number_input("Bobot Hak Infaq (Contoh: 1.0 atau 2.0):", value=1.0, step=0.5)
                if st.form_submit_button("Simpan Guru Ngaji", width='stretch'):
                    c.execute("SELECT id FROM guru_ngaji WHERE nama=? AND lembaga=? AND dkm=? AND nama_desa=?", (n_nm, n_lm, n_dk, st.session_state["nama_desa"]))
                    if c.fetchone():
                        st.error("⚠️ GAGAL! Guru dengan nama dan lembaga tersebut sudah terdaftar.")
                    else:
                        c.execute("INSERT INTO guru_ngaji (nama, lembaga, dkm, bobot, nama_desa) VALUES (?,?,?,?,?)", (n_nm, n_lm, n_dk, n_bb, st.session_state["nama_desa"]))
                        conn.commit(); st.rerun()
            df_ng = pd.read_sql_query(f"SELECT id as ID, nama as Nama, lembaga as Lembaga, dkm as DKM, bobot as Bobot FROM guru_ngaji WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
            st.dataframe(df_ng, width='stretch', hide_index=True)
            if not df_ng.empty:
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("🗑️ Hapus Guru"):
                        id_h = st.number_input("ID Hapus:", min_value=0, key="d_ngaji")
                        if st.button("Hapus", key="b_d_ngaji"): 
                            c.execute("DELETE FROM guru_ngaji WHERE id=?", (id_h,)); conn.commit(); st.rerun()
                with c2:
                    with st.expander("✏️ Edit Guru"):
                        pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Nama']}" for _, r in df_ng.iterrows()], key="e_ngaji")
                        if pil_e != "Pilih...":
                            id_e = pil_e.split(" - ")[0]
                            c.execute("SELECT nama, lembaga, dkm, bobot FROM guru_ngaji WHERE id=?", (id_e,))
                            r_e = c.fetchone()
                            if r_e:
                                with st.form("f_e_ngaji"):
                                    e_nm = st.text_input("Nama:", value=r_e[0])
                                    e_lm = st.text_input("Lembaga:", value=r_e[1])
                                    e_dk = st.text_input("DKM:", value=r_e[2])
                                    e_bb = st.number_input("Bobot:", value=float(r_e[3] or 1.0), step=0.5)
                                    if st.form_submit_button("Simpan"):
                                        c.execute("UPDATE guru_ngaji SET nama=?, lembaga=?, dkm=?, bobot=? WHERE id=?", (e_nm, e_lm, e_dk, e_bb, id_e)); conn.commit(); st.rerun()
            
    with t_sab:
        with st.form("f_ksab"):
            s_nm = st.text_input("Nama Organisasi / Penerima Sabilillah:")
            s_bb = st.number_input("Bobot / Porsi Pembagian:", value=1.0, step=0.5)
            if st.form_submit_button("Simpan Kategori Sabilillah", width='stretch'):
                c.execute("SELECT id FROM master_kategori_sab WHERE nama=? AND nama_desa=?", (s_nm, st.session_state["nama_desa"]))
                if c.fetchone():
                    st.error("⚠️ GAGAL! Nama Organisasi Sabilillah sudah ada.")
                else:
                    c.execute("INSERT INTO master_kategori_sab (nama, bobot, nama_desa) VALUES (?,?,?)", (s_nm, s_bb, st.session_state["nama_desa"]))
                    conn.commit(); st.rerun()
        df_ksab = pd.read_sql_query(f"SELECT id as ID, nama as Kategori, bobot as Bobot FROM master_kategori_sab WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        st.dataframe(df_ksab, width='stretch', hide_index=True)
        if not df_ksab.empty:
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("🗑️ Hapus Kategori"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="d_ksab")
                    if st.button("Hapus", key="b_d_ksab"): 
                        c.execute("DELETE FROM master_kategori_sab WHERE id=?", (id_h,)); conn.commit(); st.rerun()
            with c2:
                with st.expander("✏️ Edit Kategori"):
                    pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Kategori']}" for _, r in df_ksab.iterrows()], key="e_ksab")
                    if pil_e != "Pilih...":
                        id_e = pil_e.split(" - ")[0]
                        c.execute("SELECT nama, bobot FROM master_kategori_sab WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_e_ksab"):
                                e_nm = st.text_input("Kategori:", value=r_e[0])
                                e_bb = st.number_input("Bobot:", value=float(r_e[1]), step=0.5)
                                if st.form_submit_button("Simpan"):
                                    c.execute("UPDATE master_kategori_sab SET nama=?, bobot=? WHERE id=?", (e_nm, e_bb, id_e)); conn.commit(); st.rerun()
            
    with t_amil:
        with st.form("f_jami"):
            a_nm = st.text_input("Jabatan & Nama (Misal: Ketua - Bpk Ahmad):")
            a_bb = st.number_input("Bobot / Porsi Pembagian:", value=1.0, step=0.5)
            if st.form_submit_button("Simpan Pengurus Amil", width='stretch'):
                c.execute("SELECT id FROM master_jabatan_amil WHERE nama=? AND nama_desa=?", (a_nm, st.session_state["nama_desa"]))
                if c.fetchone():
                    st.error("⚠️ GAGAL! Jabatan & Nama Amil tersebut sudah terdaftar.")
                else:
                    c.execute("INSERT INTO master_jabatan_amil (nama, bobot, nama_desa) VALUES (?,?,?)", (a_nm, a_bb, st.session_state["nama_desa"]))
                    conn.commit(); st.rerun()
        df_jami = pd.read_sql_query(f"SELECT id as ID, nama as 'Jabatan & Nama', bobot as Bobot FROM master_jabatan_amil WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        st.dataframe(df_jami, width='stretch', hide_index=True)
        if not df_jami.empty:
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("🗑️ Hapus Jabatan"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="d_jami")
                    if st.button("Hapus", key="b_d_jami"): 
                        c.execute("DELETE FROM master_jabatan_amil WHERE id=?", (id_h,)); conn.commit(); st.rerun()
            with c2:
                with st.expander("✏️ Edit Jabatan"):
                    pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Jabatan & Nama']}" for _, r in df_jami.iterrows()], key="e_jami")
                    if pil_e != "Pilih...":
                        id_e = pil_e.split(" - ")[0]
                        c.execute("SELECT nama, bobot FROM master_jabatan_amil WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_e_jami"):
                                e_nm = st.text_input("Jabatan:", value=r_e[0])
                                e_bb = st.number_input("Bobot:", value=float(r_e[1]), step=0.5)
                                if st.form_submit_button("Simpan"):
                                    c.execute("UPDATE master_jabatan_amil SET nama=?, bobot=? WHERE id=?", (e_nm, e_bb, id_e)); conn.commit(); st.rerun()
    conn.close()

elif pilihan_menu == "🕌 Data Majlis Ta'lim":
    st.title("🕌 Data Majlis Ta'lim")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    with st.form("f_mj"):
        m_nm = st.text_input("Nama Majlis:")
        m_pim = st.text_input("Pimpinan:")
        if st.form_submit_button("Simpan Majlis", width='stretch'):
            c.execute("SELECT id FROM majlis_talim WHERE nama_majlis=? AND nama_desa=?", (m_nm, st.session_state["nama_desa"]))
            if c.fetchone():
                st.error("⚠️ GAGAL! Majlis Ta'lim dengan nama tersebut sudah terdaftar.")
            else:
                c.execute("INSERT INTO majlis_talim (nama_majlis, pimpinan, nama_desa) VALUES (?,?,?)", (m_nm, m_pim, st.session_state["nama_desa"]))
                conn.commit()
                st.rerun()
    df_mj = pd.read_sql_query(f"SELECT id as ID, nama_majlis as Majlis, pimpinan as Pimpinan FROM majlis_talim WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
    if not df_mj.empty:
        st.dataframe(df_mj, width='stretch', hide_index=True)
        col_del, col_edit = st.columns(2)
        with col_del:
            with st.expander("🗑️ Hapus Data Majlis"):
                id_h = st.number_input("ID Hapus:", min_value=0, key="id_hapus_majlis")
                if st.button("Hapus Data", key="btn_hapus_majlis"): 
                    c.execute("DELETE FROM majlis_talim WHERE id=?", (id_h,))
                    conn.commit()
                    st.rerun()
        with col_edit:
            with st.expander("✏️ Ubah Data Majlis"):
                pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Majlis']}" for _, r in df_mj.iterrows()], key="e_majlis")
                if pil_edit != "Pilih...":
                    id_e = pil_edit.split(" - ")[0]
                    c.execute("SELECT nama_majlis, pimpinan FROM majlis_talim WHERE id=?", (id_e,))
                    r_e = c.fetchone()
                    if r_e:
                        with st.form("f_e_majlis"):
                            e_mj = st.text_input("Majlis:", value=r_e[0])
                            e_pm = st.text_input("Pimpinan:", value=r_e[1])
                            if st.form_submit_button("Simpan Perubahan", width='stretch'):
                                c.execute("UPDATE majlis_talim SET nama_majlis=?, pimpinan=? WHERE id=?", (e_mj, e_pm, id_e))
                                conn.commit()
                                st.rerun()
    conn.close()

elif pilihan_menu == "📁 Arsip Data Lama":
    st.title("📁 Arsip Data Tahunan")
    st.info("Fitur pengelolaan arsip data lama belum diaktifkan. Gunakan fitur arsip otomatis di menu Pengaturan.")

elif pilihan_menu == "⚙️ Pengaturan":
    st.title("⚙️ Pengaturan Profil Desa")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT nama_desa, kepala_desa, ketua_upz, tarif_uang, nominal_kupon, pct_amil_desa FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
    data = c.fetchone()
    if not data:
        c.execute("INSERT INTO pengaturan (nama_desa) VALUES (?)", (st.session_state["nama_desa"],))
        conn.commit()
        c.execute("SELECT nama_desa, kepala_desa, ketua_upz, tarif_uang, nominal_kupon, pct_amil_desa FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
        data = c.fetchone()

    with st.form("form_pengaturan_desa"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Data Dasar")
            in_desa = st.text_input("Nama Desa:", value=data[0] or "", disabled=True)
            in_kades = st.text_input("Kepala Desa:", value=data[1] or "")
            in_ketua = st.text_input("Ketua UPZ:", value=data[2] or "")
            
            st.markdown("---")
            st.subheader("Tarif Zakat & Infaq")
            in_tarif = st.number_input("Tarif Zakat Uang (Rp):", value=float(data[3] or 0))
            in_kupon = st.number_input("Harga Kupon Infaq Guru Ngaji (Rp/Lembar):", value=float(data[4] or 2000.0))
            
        with c2:
            st.subheader("Pintu Utama Hak Pengelolaan")
            st.caption("UPZ Desa berhak mengelola 6,5% dari total keseluruhan Zakat/Fitrah DKM.")
            in_pct_amil = st.number_input("Hak Amil (%):", value=float(data[5] or 12.5), help="Sisanya akan otomatis menjadi Hak Sabilillah.")
            st.markdown(f"**Hak Sabilillah Otomatis: {(100 - float(data[5] or 12.5)):.1f}%**")
            st.info("💡 **Info:** Untuk mengatur rincian pembagian Sabilillah dan Amilin, silakan atur Bobot-nya di menu **📂 Kelola Data Master**.")
            
        if st.form_submit_button("💾 Simpan Pengaturan", width='stretch'):
            c.execute('''UPDATE pengaturan SET kepala_desa=?, ketua_upz=?, tarif_uang=?, nominal_kupon=?, pct_amil_desa=? WHERE nama_desa=?''', (in_kades, in_ketua, float(in_tarif), float(in_kupon), float(in_pct_amil), st.session_state["nama_desa"]))
            conn.commit()
            st.success("✅ Pengaturan berhasil disimpan!")
            st.rerun()
    conn.close()

# MENU CETAK YANG SEMPAT HILANG TELAH DIKEMBALIKAN KE SINI!
elif pilihan_menu == "🖨️ Laporan Rekap Desa":
    st.title("🖨️ Cetak Laporan PDF Kecamatan")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("Atur Surat & Titimangsa")
        no_surat = st.text_input("Nomor Surat (Pengajuan 6%):", value="001/UPZ-KEC/2026")
        tempat_ba = st.text_input("Tempat TTD:", value="Kecamatan")
        tgl_ba = st.text_input("Tanggal Surat:", value="15 Ramadhan 1446")
        
    with col2:
        st.subheader("Daftar Dokumen (Format K)")
        with st.expander("📄 Format K1 (Rekapitulasi 5%)", expanded=True):
            if st.button("🔄 Buat / Perbarui K1", width='stretch'):
                st.session_state['pdf_k1'] = mc.cetak_k1_kecamatan(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_k1' in st.session_state:
                st.download_button("📥 UNDUH PDF K1", data=st.session_state['pdf_k1'], file_name="Format_K1.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("📄 Format K2 (Lap. Mustahik Sabilillah)"):
            if st.button("🔄 Buat / Perbarui K2", width='stretch'):
                st.session_state['pdf_k2'] = mc.cetak_k2_sabilillah(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_k2' in st.session_state:
                st.download_button("📥 UNDUH PDF K2", data=st.session_state['pdf_k2'], file_name="Format_K2.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("📄 Format K3 (Rekapitulasi Program)"):
            if st.button("🔄 Buat / Perbarui K3", width='stretch'):
                st.session_state['pdf_k3'] = mc.cetak_k3_program(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_k3' in st.session_state:
                st.download_button("📥 UNDUH PDF K3", data=st.session_state['pdf_k3'], file_name="Format_K3.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("📄 Format K4 (Daftar Penyaluran Amilin)"):
            if st.button("🔄 Buat / Perbarui K4", width='stretch'):
                st.session_state['pdf_k4'] = mc.cetak_k4_amilin(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_k4' in st.session_state:
                st.download_button("📥 UNDUH PDF K4", data=st.session_state['pdf_k4'], file_name="Format_K4.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("✉️ Surat Pengajuan 6% ke BAZNAS Kab"):
            if st.button("🔄 Buat / Perbarui Surat 6%", width='stretch'):
                st.session_state['pdf_surat6'] = mc.cetak_surat_6persen(DB_NAME, tempat_ba, tgl_ba, no_surat)
            if 'pdf_surat6' in st.session_state:
                st.download_button("📥 UNDUH SURAT 6%", data=st.session_state['pdf_surat6'], file_name="Surat_6Persen.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("🧾 Cetak Kwitansi Kosong"):
            if st.button("🔄 Buat Kwitansi", width='stretch'):
                st.session_state['pdf_kwitansi'] = mc.cetak_kwitansi("Nama Lembaga", 1500000, "Bantuan Sarana", f"{tempat_ba}, {tgl_ba}")
            if 'pdf_kwitansi' in st.session_state:
                st.download_button("📥 UNDUH KWITANSI", data=st.session_state['pdf_kwitansi'], file_name="Kwitansi.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("🐄 Rekap Hewan Qurban (Kecamatan)"):
            if st.button("🔄 Buat Rekap Qurban", width='stretch'):
                st.session_state['pdf_q_kec'] = mc.cetak_rekap_qurban_kec(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_q_kec' in st.session_state:
                st.download_button("📥 UNDUH REKAP QURBAN", data=st.session_state['pdf_q_kec'], file_name="Rekap_Qurban_Kecamatan.pdf", mime="application/pdf", width='stretch')

        with st.expander("🕌 Rekap Majlis Ta'lim (Kecamatan)"):
            if st.button("🔄 Buat Rekap Majlis Ta'lim", width='stretch'):
                st.session_state['pdf_m_kec'] = mc.cetak_rekap_majlis_kec(DB_NAME, tempat_ba, tgl_ba)
            if 'pdf_m_kec' in st.session_state:
                st.download_button("📥 UNDUH REKAP MAJLIS", data=st.session_state['pdf_m_kec'], file_name="Rekap_Majlis_Kecamatan.pdf", mime="application/pdf", width='stretch')