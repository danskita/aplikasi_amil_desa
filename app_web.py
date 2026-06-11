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

    # Menambahkan kolom "nominal_kupon" untuk fitur Kupon Infaq
    kolom_baru_pengaturan = [
        ("bendahara", "TEXT"), ("pct_amil_kec", "REAL DEFAULT 12.5"), ("pct_ketua_kec", "REAL DEFAULT 40.0"), 
        ("pct_sekretaris_kec", "REAL DEFAULT 30.0"), ("pct_bendahara_kec", "REAL DEFAULT 20.0"), ("pct_lainnya_kec", "REAL DEFAULT 10.0"),
        ("pct_olk_kec", "REAL DEFAULT 25.0"), ("pct_sarana_kec", "REAL DEFAULT 25.0"), ("pct_ngaji_kec", "REAL DEFAULT 25.0"), 
        ("pct_madrasah_kec", "REAL DEFAULT 25.0"), ("no_hp", "TEXT"), ("total_jiwa", "INTEGER"), ("total_kk", "INTEGER"),
        ("nominal_kupon", "REAL DEFAULT 2000.0")
    ]
    for col, tipe in kolom_baru_pengaturan:
        try: c.execute(f"ALTER TABLE pengaturan ADD COLUMN {col} {tipe}")
        except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS setoran_kecamatan (id INTEGER PRIMARY KEY AUTOINCREMENT, nama_desa TEXT, beras_disetor REAL, uang_disetor REAL, tanggal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS master_penerima_kec (id INTEGER PRIMARY KEY AUTOINCREMENT, program TEXT, nama_penerima TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS distribusi_kec_program (id INTEGER PRIMARY KEY AUTOINCREMENT, program TEXT, penerima TEXT, beras REAL, uang REAL, tanggal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS distribusi_kec_amil (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, jabatan TEXT, beras REAL, uang REAL, tanggal TEXT)''')
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
    menu_halaman = ["📊 Rekapitulasi Kecamatan", "📥 Setoran UPZ Desa", "📤 Distribusi UPZ Kecamatan", "📂 Master Penerima Kecamatan", "🖨️ Laporan Rekap Desa", "⚙️ Profil Kecamatan", "👥 Kelola Pengguna"]
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
            c.execute("CREATE TABLE IF NOT EXISTS qurban (id INTEGER PRIMARY KEY AUTOINCREMENT, tahun TEXT, nama_dkm TEXT, jenis_hewan TEXT, jumlah_hewan INTEGER, jumlah_mudhohi INTEGER, nama_desa TEXT)")
            df_q = pd.DataFrame()
            
        if not df_q.empty:
            c_sapi = df_q[df_q['Jenis Hewan'] == 'Sapi']['Jumlah (Ekor)'].sum()
            c_domba = df_q[df_q['Jenis Hewan'] == 'Domba']['Jumlah (Ekor)'].sum()
            c_kambing = df_q[df_q['Jenis Hewan'] == 'Kambing']['Jumlah (Ekor)'].sum()
            c_kerbau = df_q[df_q['Jenis Hewan'] == 'Kerbau']['Jumlah (Ekor)'].sum()
            c_mudhohi = df_q['Jumlah Mudhohi'].sum()
            
            cq1, cq2, cq3, cq4, cq5 = st.columns(5)
            cq1.metric("Total Sapi", f"{c_sapi} Ekor")
            cq2.metric("Total Domba", f"{c_domba} Ekor")
            cq3.metric("Total Kambing", f"{c_kambing} Ekor")
            cq4.metric("Total Kerbau", f"{c_kerbau} Ekor")
            cq5.metric("Total Mudhohi", f"{c_mudhohi} Orang")
            
            st.markdown("---")
            st.dataframe(df_q, width='stretch', hide_index=True)
        else:
            st.info("Belum ada data laporan penyembelihan hewan Qurban dari UPZ Desa.")

    with tab_majlis:
        st.subheader("🕌 Data Rekapitulasi Majlis Ta'lim se-Kecamatan")
        try:
            df_m = pd.read_sql_query("SELECT nama_desa AS 'Asal Desa', nama_majlis AS 'Nama Majlis Ta\\'lim', pimpinan AS 'Nama Pimpinan' FROM majlis_talim ORDER BY nama_desa ASC", conn)
        except:
            c.execute("CREATE TABLE IF NOT EXISTS majlis_talim (id INTEGER PRIMARY KEY AUTOINCREMENT, nama_majlis TEXT, pimpinan TEXT, nama_desa TEXT)")
            df_m = pd.DataFrame()
            
        if not df_m.empty:
            st.metric("Total Majlis Ta'lim Terdata", f"{len(df_m)} Lembaga")
            st.markdown("---")
            st.dataframe(df_m, width='stretch', hide_index=True)
        else:
            st.info("Belum ada data pendaftaran Majlis Ta'lim dari UPZ Desa.")
            
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
                    st.error("⚠️ Data setoran sudah ada!")
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

elif pilihan_menu == "📂 Master Penerima Kecamatan":
    st.title("📂 Master Data Penerima Program Kecamatan")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    with st.form("form_master_kec"):
        col1, col2 = st.columns(2)
        with col1: 
            m_prog = st.selectbox("Kategori Program:", ["Operasional Lembaga Keagamaan", "Sarana Keagamaan", "Insentif Guru Ngaji", "Insentif Guru Madrasah Diniyah"])
        with col2: 
            m_nama = st.text_input("Nama Lembaga / Pimpinan / Guru:")
        if st.form_submit_button("💾 Daftarkan Penerima", width='stretch'):
            if m_nama: 
                c.execute("INSERT INTO master_penerima_kec (program, nama_penerima) VALUES (?,?)", (m_prog, m_nama))
                conn.commit()
                st.rerun()
            else: 
                st.error("Nama Penerima wajib diisi!")
    
    df_mp = pd.read_sql_query("SELECT id as ID, program as Program, nama_penerima as 'Nama Penerima' FROM master_penerima_kec ORDER BY program ASC", conn)
    if not df_mp.empty:
        st.dataframe(df_mp, width='stretch', hide_index=True)
        col_del, col_edit = st.columns(2)
        with col_del:
            with st.expander("🗑️ Hapus Data Penerima"):
                id_h = st.number_input("ID Hapus:", min_value=0, step=1, key="del_master_pen_kec")
                if st.button("Hapus Data", key="btn_hapus_master_pen_kec"): 
                    c.execute("DELETE FROM master_penerima_kec WHERE id=?", (id_h,))
                    conn.commit()
                    st.rerun()
        with col_edit:
            with st.expander("✏️ Ubah Data Penerima"):
                pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Nama Penerima']}" for _, r in df_mp.iterrows()])
                if pil_edit != "Pilih...":
                    id_e = pil_edit.split(" - ")[0]
                    c.execute("SELECT program, nama_penerima FROM master_penerima_kec WHERE id=?", (id_e,))
                    r_e = c.fetchone()
                    if r_e:
                        with st.form("f_edit_master_kec"):
                            es_prog = st.selectbox("Program:", ["Operasional Lembaga Keagamaan", "Sarana Keagamaan", "Insentif Guru Ngaji", "Insentif Guru Madrasah Diniyah"], index=["Operasional Lembaga Keagamaan", "Sarana Keagamaan", "Insentif Guru Ngaji", "Insentif Guru Madrasah Diniyah"].index(r_e[0]))
                            es_nama = st.text_input("Nama Penerima:", value=r_e[1])
                            if st.form_submit_button("Simpan Perubahan", width='stretch'):
                                c.execute("UPDATE master_penerima_kec SET program=?, nama_penerima=? WHERE id=?", (es_prog, es_nama, id_e))
                                conn.commit()
                                st.rerun()
    conn.close()

elif pilihan_menu == "📤 Distribusi UPZ Kecamatan":
    st.title("📤 Distribusi Alokasi UPZ Kecamatan (5%)")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT SUM(total_beras), SUM(total_uang) FROM setoran_dkm")
    tot = c.fetchone()
    hak_kec_b = (tot[0] or 0.0) * 0.05
    hak_kec_u = (tot[1] or 0.0) * 0.05
    
    c.execute("SELECT pct_amil_kec, pct_ketua_kec, pct_sekretaris_kec, pct_bendahara_kec, pct_lainnya_kec, pct_olk_kec, pct_sarana_kec, pct_ngaji_kec, pct_madrasah_kec FROM pengaturan WHERE nama_desa='KECAMATAN'")
    p_data = c.fetchone()
    if p_data:
        p_amil, p_ketua, p_sek, p_ben, p_lain = float(p_data[0] or 12.5), float(p_data[1] or 40.0), float(p_data[2] or 30.0), float(p_data[3] or 20.0), float(p_data[4] or 10.0)
        p_olk, p_sar, p_ngj, p_mdr = float(p_data[5] or 25.0), float(p_data[6] or 25.0), float(p_data[7] or 25.0), float(p_data[8] or 25.0)
    else:
        p_amil, p_ketua, p_sek, p_ben, p_lain = 12.5, 40.0, 30.0, 20.0, 10.0
        p_olk, p_sar, p_ngj, p_mdr = 25.0, 25.0, 25.0, 25.0
        
    p_sab = 100.0 - p_amil
    sab_b = hak_kec_b * (p_sab / 100.0)
    sab_u = hak_kec_u * (p_sab / 100.0)
    amil_b = hak_kec_b * (p_amil / 100.0)
    amil_u = hak_kec_u * (p_amil / 100.0)
    
    ketua_b = amil_b * (p_ketua / 100.0); ketua_u = amil_u * (p_ketua / 100.0)
    sek_b = amil_b * (p_sek / 100.0); sek_u = amil_u * (p_sek / 100.0)
    ben_b = amil_b * (p_ben / 100.0); ben_u = amil_u * (p_ben / 100.0)
    lain_b = amil_b * (p_lain / 100.0); lain_u = amil_u * (p_lain / 100.0)
    
    b_olk = sab_b * (p_olk / 100.0); u_olk = sab_u * (p_olk / 100.0)
    b_sar = sab_b * (p_sar / 100.0); u_sar = sab_u * (p_sar / 100.0)
    b_ngj = sab_b * (p_ngj / 100.0); u_ngj = sab_u * (p_ngj / 100.0)
    b_mdr = sab_b * (p_mdr / 100.0); u_mdr = sab_u * (p_mdr / 100.0)

    st.info("💡 **ALOKASI ANGGARAN OTOMATIS**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Hak Kecamatan (5%)", f"{hak_kec_b:,.2f} Kg", format_rupiah(hak_kec_u))
    col2.metric(f"Sabilillah ({p_sab:.1f}%)", f"{sab_b:,.2f} Kg", format_rupiah(sab_u))
    col3.metric(f"Hak Amil ({p_amil:.1f}%)", f"{amil_b:,.2f} Kg", format_rupiah(amil_u))
    
    tab_prog, tab_amil = st.tabs(["📌 Program Keagamaan (Sabilillah)", "📌 Amilin Kecamatan"])
    
    with tab_prog:
        prog_pilihan = st.selectbox("Pilih Program:", ["Pilih Program...", "Operasional Lembaga Keagamaan", "Sarana Keagamaan", "Insentif Guru Ngaji", "Insentif Guru Madrasah Diniyah"])
        c.execute("SELECT nama_penerima FROM master_penerima_kec WHERE program=?", (prog_pilihan,))
        list_penerima = [r[0] for r in c.fetchall()]
        jml_terdaftar = len(list_penerima)
        
        auto_prog_b = 0.0; auto_prog_u = 0
        if prog_pilihan != "Pilih Program..." and jml_terdaftar > 0:
            if prog_pilihan == "Operasional Lembaga Keagamaan": 
                auto_prog_b = b_olk / jml_terdaftar; auto_prog_u = u_olk / jml_terdaftar
            elif prog_pilihan == "Sarana Keagamaan": 
                auto_prog_b = b_sar / jml_terdaftar; auto_prog_u = u_sar / jml_terdaftar
            elif prog_pilihan == "Insentif Guru Ngaji": 
                auto_prog_b = b_ngj / jml_terdaftar; auto_prog_u = u_ngj / jml_terdaftar
            elif prog_pilihan == "Insentif Guru Madrasah Diniyah": 
                auto_prog_b = b_mdr / jml_terdaftar; auto_prog_u = u_mdr / jml_terdaftar
            st.success(f"Terdapat **{jml_terdaftar} entitas terdaftar**. Sistem otomatis membagi rata.")

        with st.form("form_kec_prog"):
            col1, col2 = st.columns(2)
            with col1: 
                penerima_prog = st.selectbox("Penerima:", ["Pilih dari Master..."] + list_penerima) if list_penerima else st.text_input("Penerima (Manual):")
            with col2:
                beras_prog = st.number_input("Beras (Kg):", value=float(auto_prog_b), step=0.5)
                uang_prog = st.number_input("Uang (Rp):", value=int(auto_prog_u), step=1000)
            if st.form_submit_button("💾 Simpan", width='stretch'):
                p_simpan = penerima_prog if penerima_prog != "Pilih dari Master..." else ""
                if p_simpan and prog_pilihan != "Pilih Program...":
                    c.execute("INSERT INTO distribusi_kec_program (program, penerima, beras, uang, tanggal) VALUES (?,?,?,?,?)", (prog_pilihan, p_simpan, beras_prog, uang_prog, str(datetime.date.today())))
                    conn.commit()
                    st.rerun()
                else: 
                    st.error("Pilih Program dan Penerima!")
        
        df_prog = pd.read_sql_query("SELECT id as ID, tanggal as Tanggal, program as Program, penerima as Penerima, beras as 'Beras (Kg)', uang as 'Uang (Rp)' FROM distribusi_kec_program ORDER BY id DESC", conn)
        if not df_prog.empty:
            df_p = df_prog.copy()
            df_p['Uang (Rp)'] = df_p['Uang (Rp)'].apply(format_rupiah)
            st.dataframe(df_p, width='stretch', hide_index=True)
            col_del, col_edit = st.columns(2)
            with col_del:
                with st.expander("🗑️ Hapus Data Program"):
                    id_h = st.number_input("ID Hapus Program:", min_value=0, step=1, key="d_p")
                    if st.button("Hapus Program", key="hapus_prog_kec"): 
                        c.execute("DELETE FROM distribusi_kec_program WHERE id=?", (id_h,))
                        conn.commit()
                        st.rerun()
            with col_edit:
                with st.expander("✏️ Ubah Data Program"):
                    pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Penerima']}" for _, r in df_prog.iterrows()], key="e_prog_k")
                    if pil_edit != "Pilih...":
                        id_e = pil_edit.split(" - ")[0]
                        c.execute("SELECT program, penerima, beras, uang FROM distribusi_kec_program WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_e_prog_k"):
                                e_prog = st.text_input("Program:", value=r_e[0])
                                e_pen = st.text_input("Penerima:", value=r_e[1])
                                e_b = st.number_input("Beras:", value=float(r_e[2]), step=0.5)
                                e_u = st.number_input("Uang:", value=int(r_e[3]), step=1000)
                                if st.form_submit_button("Simpan Perubahan", width='stretch'):
                                    c.execute("UPDATE distribusi_kec_program SET program=?, penerima=?, beras=?, uang=? WHERE id=?", (e_prog, e_pen, e_b, e_u, id_e))
                                    conn.commit()
                                    st.rerun()

    with tab_amil:
        jab_pilihan = st.selectbox("Pilih Jabatan (Auto-Hitung):", ["Pilih Jabatan...", "Ketua", "Sekretaris", "Bendahara", "Anggota / Ops"])
        jml_anggota = 1
        if jab_pilihan == "Anggota / Ops": 
            jml_anggota = st.number_input("Jumlah Anggota dibagi rata:", min_value=1, value=1)
            
        auto_b = 0.0; auto_u = 0
        if jab_pilihan == "Ketua": auto_b = ketua_b; auto_u = ketua_u
        elif jab_pilihan == "Sekretaris": auto_b = sek_b; auto_u = sek_u
        elif jab_pilihan == "Bendahara": auto_b = ben_b; auto_u = ben_u
        elif jab_pilihan == "Anggota / Ops": auto_b = lain_b / jml_anggota; auto_u = lain_u / jml_anggota
        
        with st.form("form_kec_amil"):
            col1, col2 = st.columns(2)
            with col1:
                nama_amil = st.text_input("Nama Pejabat:")
                jabatan_amil = st.text_input("Jabatan:", value=jab_pilihan if jab_pilihan != "Pilih Jabatan..." else "")
            with col2:
                beras_amil = st.number_input("Beras (Kg):", value=float(auto_b), step=0.5, key=f"b_{jab_pilihan}_{jml_anggota}")
                uang_amil = st.number_input("Uang (Rp):", value=int(auto_u), step=1000, key=f"u_{jab_pilihan}_{jml_anggota}")
            if st.form_submit_button("💾 Simpan", width='stretch'):
                if nama_amil:
                    c.execute("INSERT INTO distribusi_kec_amil (nama, jabatan, beras, uang, tanggal) VALUES (?,?,?,?,?)", (nama_amil, jabatan_amil, beras_amil, uang_amil, str(datetime.date.today())))
                    conn.commit()
                    st.rerun()
                    
        df_amil = pd.read_sql_query("SELECT id as ID, tanggal as Tanggal, nama as 'Nama Amil', jabatan as Jabatan, beras as 'Beras (Kg)', uang as 'Uang (Rp)' FROM distribusi_kec_amil ORDER BY id DESC", conn)
        if not df_amil.empty:
            df_a = df_amil.copy()
            df_a['Uang (Rp)'] = df_a['Uang (Rp)'].apply(format_rupiah)
            st.dataframe(df_a, width='stretch', hide_index=True)
            col_del, col_edit = st.columns(2)
            with col_del:
                with st.expander("🗑️ Hapus Data Amil"):
                    id_ha = st.number_input("ID Hapus Amil:", min_value=0, step=1, key="d_a")
                    if st.button("Hapus Amil", key="hapus_amil_kec"): 
                        c.execute("DELETE FROM distribusi_kec_amil WHERE id=?", (id_ha,))
                        conn.commit()
                        st.rerun()
            with col_edit:
                with st.expander("✏️ Ubah Data Amil"):
                    pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Nama Amil']}" for _, r in df_amil.iterrows()], key="e_amil_k")
                    if pil_edit != "Pilih...":
                        id_e = pil_edit.split(" - ")[0]
                        c.execute("SELECT nama, jabatan, beras, uang FROM distribusi_kec_amil WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_e_amil_k"):
                                e_na = st.text_input("Nama Amil:", value=r_e[0])
                                e_ja = st.text_input("Jabatan:", value=r_e[1])
                                e_b = st.number_input("Beras:", value=float(r_e[2]), step=0.5)
                                e_u = st.number_input("Uang:", value=int(r_e[3]), step=1000)
                                if st.form_submit_button("Simpan Perubahan", width='stretch'):
                                    c.execute("UPDATE distribusi_kec_amil SET nama=?, jabatan=?, beras=?, uang=? WHERE id=?", (e_na, e_ja, e_b, e_u, id_e))
                                    conn.commit()
                                    st.rerun()
    conn.close()

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
    c.execute("SELECT nama_kecamatan, kabupaten, ketua_upz, sekretaris, bendahara, pct_amil_kec, pct_ketua_kec, pct_sekretaris_kec, pct_bendahara_kec, pct_lainnya_kec, pct_olk_kec, pct_sarana_kec, pct_ngaji_kec, pct_madrasah_kec FROM pengaturan WHERE nama_desa='KECAMATAN'")
    res = c.fetchone()
    v_kec = res[0] if res else ""
    v_kab = res[1] if res else ""
    v_ketua = res[2] if res else ""
    v_sek = res[3] if res else ""
    v_ben = res[4] if res else ""
    v_pa = float(res[5] or 12.5)
    v_pk = float(res[6] or 40.0)
    v_ps = float(res[7] or 30.0)
    v_pb = float(res[8] or 20.0)
    v_pl = float(res[9] or 10.0)
    v_po = float(res[10] or 25.0)
    v_psar = float(res[11] or 25.0)
    v_pn = float(res[12] or 25.0)
    v_pm = float(res[13] or 25.0)

    with st.form("form_master_kecamatan"):
        col1, col2 = st.columns(2)
        with col1:
            in_kec = st.text_input("Kecamatan:", value=v_kec)
            in_kab = st.text_input("Kabupaten:", value=v_kab)
            in_ketua = st.text_input("Ketua:", value=v_ketua)
            in_sek = st.text_input("Sekretaris:", value=v_sek)
            in_ben = st.text_input("Bendahara:", value=v_ben)
            st.markdown("---")
            st.subheader("Program Sabilillah (%)")
            i_po = st.number_input("OLK:", value=v_po)
            i_psar = st.number_input("Sarana:", value=v_psar)
            i_pn = st.number_input("Ngaji:", value=v_pn)
            i_pm = st.number_input("Madrasah:", value=v_pm)
        with col2:
            st.subheader("Prosentase Amilin")
            i_pa = st.number_input("Hak Amil Total (%):", value=v_pa)
            st.markdown("---")
            st.markdown("**Internal Amil:**")
            i_pk = st.number_input("Ketua:", value=v_pk)
            i_ps = st.number_input("Sekretaris:", value=v_ps)
            i_pb = st.number_input("Bendahara:", value=v_pb)
            i_pl = st.number_input("Anggota:", value=v_pl)
        if st.form_submit_button("💾 Simpan", width='stretch'):
            if (i_pk+i_ps+i_pb+i_pl) == 100.0 and (i_po+i_psar+i_pn+i_pm) == 100.0:
                c.execute("""UPDATE pengaturan SET nama_kecamatan=?, kabupaten=?, ketua_upz=?, sekretaris=?, bendahara=?, pct_amil_kec=?, pct_ketua_kec=?, pct_sekretaris_kec=?, pct_bendahara_kec=?, pct_lainnya_kec=?, pct_olk_kec=?, pct_sarana_kec=?, pct_ngaji_kec=?, pct_madrasah_kec=? WHERE nama_desa='KECAMATAN'""", (in_kec, in_kab, in_ketua, in_sek, in_ben, i_pa, i_pk, i_ps, i_pb, i_pl, i_po, i_psar, i_pn, i_pm))
                conn.commit()
                st.rerun()
            else: 
                st.error("Total Persentase Program atau Internal Amil harus 100%!")
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
                try: 
                    c.execute("INSERT INTO users (username, password, role, nama_desa) VALUES (?,?,?,?)", (u_name, u_pass, u_role, u_desa))
                    conn.commit()
                    st.rerun()
                except: 
                    st.error("Username sudah ada!")
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
            tipe_input = "jiwa" if mode_input == "Berdasarkan Data Jiwa" else "fisik"
            if tipe_input == "jiwa": 
                tb = j_b * t_b; tu = j_u * t_u; fb = tb * 0.175; fu = tu * 0.175; jiwa_b=j_b; jiwa_u=j_u
            else:
                fb = f_b; fu = f_u; tb = fb / 0.175 if fb > 0 else 0; tu = fu / 0.175 if fu > 0 else 0
                jiwa_b = int(round(tb / t_b)) if t_b > 0 else 0; jiwa_u = int(round(tu / t_u)) if t_u > 0 else 0
            
            # --- LOGIKA KUPON DIKEMBALIKAN (Uang Tunai + Hasil Kupon x Rp 2000) ---
            infaq_rp = float(infaq_uang) + float(k_terjual * nom_kupon)
            # ----------------------------------------------------------------------
            c.execute('''INSERT INTO setoran_dkm (nama_dkm, alamat_dkm, perwakilan, alamat_perwakilan, tipe_input, jiwa_beras, jiwa_uang, fisik_beras, fisik_uang, total_beras, total_uang, infaq, kupon_diterima, kupon_terjual, kupon_kembali, nama_desa) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (selected_dkm, alamat_dkm, wakil_upz, alamat_wakil, tipe_input, jiwa_b, jiwa_u, fb, fu, tb, tu, infaq_rp, k_diterima, k_terjual, k_kembali, st.session_state["nama_desa"]))
            conn.commit()
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
    st.title("📤 Distribusi Alokasi UPZ Desa")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    tab_sab, tab_amil = st.tabs(["📌 Sabilillah", "📌 Amilin"])
    
    with tab_sab:
        with st.form("form_sab"):
            col1, col2 = st.columns(2)
            with col1: 
                prog_sab = st.text_input("Kategori:")
                penerima_sab = st.text_input("Penerima:")
            with col2: 
                beras_sab = st.number_input("Beras (Kg):", min_value=0.0, step=0.5)
                uang_sab = st.number_input("Uang (Rp):", min_value=0, step=1000)
            if st.form_submit_button("Simpan", width='stretch'):
                c.execute("INSERT INTO sabilillah (program, penerima, beras, uang, nama_desa) VALUES (?,?,?,?,?)", (prog_sab, penerima_sab, beras_sab, uang_sab, st.session_state["nama_desa"]))
                conn.commit()
                st.rerun()
        df_sab = pd.read_sql_query(f"SELECT id as ID, program as Program, penerima as Penerima, beras as Beras, uang as Uang FROM sabilillah WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        if not df_sab.empty:
            df_sab_disp = df_sab.copy()
            df_sab_disp['Uang'] = df_sab_disp['Uang'].apply(format_rupiah)
            st.dataframe(df_sab_disp, width='stretch', hide_index=True)
            col_del, col_edit = st.columns(2)
            with col_del:
                with st.expander("🗑️ Hapus Sabilillah"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="dsab")
                    if st.button("Hapus Sabilillah", key="btn_hapus_sab"): 
                        c.execute("DELETE FROM sabilillah WHERE id=?", (id_h,))
                        conn.commit()
                        st.rerun()
            with col_edit:
                with st.expander("✏️ Ubah Sabilillah"):
                    pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Penerima']}" for _, r in df_sab.iterrows()], key="esab")
                    if pil_edit != "Pilih...":
                        id_e = pil_edit.split(" - ")[0]
                        c.execute("SELECT program, penerima, beras, uang FROM sabilillah WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_esab"):
                                e_pr = st.text_input("Program:", value=r_e[0])
                                e_pe = st.text_input("Penerima:", value=r_e[1])
                                e_b = st.number_input("Beras (Kg):", value=float(r_e[2]), step=0.5)
                                e_u = st.number_input("Uang (Rp):", value=int(r_e[3]), step=1000)
                                if st.form_submit_button("Simpan Perubahan", width='stretch'):
                                    c.execute("UPDATE sabilillah SET program=?, penerima=?, beras=?, uang=? WHERE id=?", (e_pr, e_pe, e_b, e_u, id_e))
                                    conn.commit()
                                    st.rerun()

    with tab_amil:
        with st.form("form_amil"):
            col1, col2 = st.columns(2)
            with col1: 
                nama_amil = st.text_input("Nama Amil:")
                jabatan_amil = st.text_input("Jabatan:")
            with col2: 
                beras_amil = st.number_input("Beras (Kg):", min_value=0.0, step=0.5)
                uang_amil = st.number_input("Uang (Rp):", min_value=0, step=1000)
            if st.form_submit_button("Simpan", width='stretch'):
                c.execute("INSERT INTO amilin (nama, jabatan, beras, uang, nama_desa) VALUES (?,?,?,?,?)", (nama_amil, jabatan_amil, beras_amil, uang_amil, st.session_state["nama_desa"]))
                conn.commit()
                st.rerun()
        df_amil = pd.read_sql_query(f"SELECT id as ID, nama as Nama, jabatan as Jabatan, beras as Beras, uang as Uang FROM amilin WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        if not df_amil.empty:
            df_amil_disp = df_amil.copy()
            df_amil_disp['Uang'] = df_amil_disp['Uang'].apply(format_rupiah)
            st.dataframe(df_amil_disp, width='stretch', hide_index=True)
            col_del, col_edit = st.columns(2)
            with col_del:
                with st.expander("🗑️ Hapus Amilin"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="dami")
                    if st.button("Hapus Amilin", key="btn_hapus_amil_desa"): 
                        c.execute("DELETE FROM amilin WHERE id=?", (id_h,))
                        conn.commit()
                        st.rerun()
            with col_edit:
                with st.expander("✏️ Ubah Amilin"):
                    pil_edit = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Nama']}" for _, r in df_amil.iterrows()], key="eami")
                    if pil_edit != "Pilih...":
                        id_e = pil_edit.split(" - ")[0]
                        c.execute("SELECT nama, jabatan, beras, uang FROM amilin WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_eami"):
                                e_nm = st.text_input("Nama Amil:", value=r_e[0])
                                e_jb = st.text_input("Jabatan:", value=r_e[1])
                                e_b = st.number_input("Beras (Kg):", value=float(r_e[2]), step=0.5)
                                e_u = st.number_input("Uang (Rp):", value=int(r_e[3]), step=1000)
                                if st.form_submit_button("Simpan Perubahan", width='stretch'):
                                    c.execute("UPDATE amilin SET nama=?, jabatan=?, beras=?, uang=? WHERE id=?", (e_nm, e_jb, e_b, e_u, id_e))
                                    conn.commit()
                                    st.rerun()
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
    t1, t2, t3, t4 = st.tabs(["🕌 Master DKM", "📖 Guru Ngaji", "📌 Kategori Sabilillah", "👔 Jabatan Amilin"])
    
    with t1:
        with st.form("f_dkm"):
            i_nm = st.text_input("Nama UPZ DKM:")
            i_kt = st.text_input("Ketua DKM:")
            i_al = st.text_input("Alamat:")
            i_wk = st.text_input("Perwakilan (Koma):")
            if st.form_submit_button("Simpan Master DKM", width='stretch'):
                c.execute("INSERT INTO master_dkm (nama_dkm, ketua_dkm, alamat_dkm, perwakilan, nama_desa) VALUES (?,?,?,?,?)", (i_nm.upper(), i_kt, i_al, i_wk, st.session_state["nama_desa"]))
                conn.commit()
                st.rerun()
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
        
    with t2:
        with st.form("f_ngaji"):
            n_nm = st.text_input("Nama Pengajar:")
            n_lm = st.text_input("Lembaga:")
            n_dk = st.text_input("DKM Terkait:")
            if st.form_submit_button("Simpan Guru Ngaji", width='stretch'):
                c.execute("INSERT INTO guru_ngaji (nama, lembaga, dkm, nama_desa) VALUES (?,?,?,?)", (n_nm, n_lm, n_dk, st.session_state["nama_desa"]))
                conn.commit()
                st.rerun()
        df_ng = pd.read_sql_query(f"SELECT id as ID, nama, lembaga, dkm FROM guru_ngaji WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
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
                    pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['nama']}" for _, r in df_ng.iterrows()], key="e_ngaji")
                    if pil_e != "Pilih...":
                        id_e = pil_e.split(" - ")[0]
                        c.execute("SELECT nama, lembaga, dkm FROM guru_ngaji WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_e_ngaji"):
                                e_nm = st.text_input("Nama:", value=r_e[0])
                                e_lm = st.text_input("Lembaga:", value=r_e[1])
                                e_dk = st.text_input("DKM:", value=r_e[2])
                                if st.form_submit_button("Simpan"):
                                    c.execute("UPDATE guru_ngaji SET nama=?, lembaga=?, dkm=? WHERE id=?", (e_nm, e_lm, e_dk, id_e)); conn.commit(); st.rerun()
        
    with t3:
        with st.form("f_ksab"):
            s_nm = st.text_input("Kategori:")
            s_bb = st.number_input("Bobot:", value=0.0)
            if st.form_submit_button("Simpan Kategori", width='stretch'):
                c.execute("INSERT INTO master_kategori_sab (nama, bobot, nama_desa) VALUES (?,?,?)", (s_nm, s_bb, st.session_state["nama_desa"]))
                conn.commit()
                st.rerun()
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
                                e_bb = st.number_input("Bobot:", value=float(r_e[1]))
                                if st.form_submit_button("Simpan"):
                                    c.execute("UPDATE master_kategori_sab SET nama=?, bobot=? WHERE id=?", (e_nm, e_bb, id_e)); conn.commit(); st.rerun()
        
    with t4:
        with st.form("f_jami"):
            a_nm = st.text_input("Jabatan:")
            a_bb = st.number_input("Bobot:", value=0.0)
            if st.form_submit_button("Simpan Jabatan", width='stretch'):
                c.execute("INSERT INTO master_jabatan_amil (nama, bobot, nama_desa) VALUES (?,?,?)", (a_nm, a_bb, st.session_state["nama_desa"]))
                conn.commit()
                st.rerun()
        df_jami = pd.read_sql_query(f"SELECT id as ID, nama as Jabatan, bobot as Bobot FROM master_jabatan_amil WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
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
                    pil_e = st.selectbox("Pilih Data:", ["Pilih..."] + [f"{r['ID']} - {r['Jabatan']}" for _, r in df_jami.iterrows()], key="e_jami")
                    if pil_e != "Pilih...":
                        id_e = pil_e.split(" - ")[0]
                        c.execute("SELECT nama, bobot FROM master_jabatan_amil WHERE id=?", (id_e,))
                        r_e = c.fetchone()
                        if r_e:
                            with st.form("f_e_jami"):
                                e_nm = st.text_input("Jabatan:", value=r_e[0])
                                e_bb = st.number_input("Bobot:", value=float(r_e[1]))
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
    
    # [PERBAIKAN BUG] Agar pengaturan terpisah sesuai akun desa yang login
    c.execute("SELECT nama_desa, kepala_desa, ketua_upz, tarif_uang, nominal_kupon FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
    data = c.fetchone()
    if not data:
        c.execute("INSERT INTO pengaturan (nama_desa) VALUES (?)", (st.session_state["nama_desa"],))
        conn.commit()
        c.execute("SELECT nama_desa, kepala_desa, ketua_upz, tarif_uang, nominal_kupon FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
        data = c.fetchone()

    with st.form("form_pengaturan_desa"):
        c1, c2 = st.columns(2)
        with c1:
            in_desa = st.text_input("Nama Desa:", value=data[0] or "", disabled=True)
            in_kades = st.text_input("Kepala Desa:", value=data[1] or "")
        with c2:
            in_ketua = st.text_input("Ketua UPZ:", value=data[2] or "")
            in_tarif = st.number_input("Tarif Zakat Uang (Rp):", value=float(data[3] or 0))
            
        # Fitur Input Harga Kupon Infaq kembali muncul!
        in_kupon = st.number_input("Harga Kupon Infaq Guru Ngaji per Lembar (Rp):", value=float(data[4] or 2000.0))
        
        if st.form_submit_button("💾 Simpan Pengaturan", width='stretch'):
            c.execute('''UPDATE pengaturan SET kepala_desa=?, ketua_upz=?, tarif_uang=?, nominal_kupon=? WHERE nama_desa=?''', (in_kades, in_ketua, float(in_tarif), float(in_kupon), st.session_state["nama_desa"]))
            conn.commit()
            st.rerun()
    conn.close()

elif pilihan_menu == "🖨️ Cetak Laporan PDF":
    st.title("🖨️ Pencetakan Dokumen Laporan Desa (PDF)")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    desa_aktif = st.session_state["nama_desa"]

    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("Atur Titimangsa Surat")
        with st.container(border=True):
            no_ba = st.text_input("Nomor Surat:", value=f"001/BAST/UPZ-DESA/III/{datetime.datetime.now().year}")
            tgl_ba = st.text_input("Tanggal Surat:", value="15 Ramadhan 1446")
            tempat_ba = st.text_input("Tempat TTD:", value=desa_aktif.capitalize())

    with col2:
        st.subheader("Daftar Dokumen Desa Siap Unduh")
        
        with st.expander("📄 Format D3 (Rekapitulasi 100%)", expanded=True):
            if st.button("🔄 Buat / Perbarui D3", width='stretch'):
                st.session_state['pdf_d3'] = mc.cetak_d3_desa(DB_NAME, desa_aktif, tempat_ba, tgl_ba, no_ba)
            if 'pdf_d3' in st.session_state:
                st.download_button("📥 KLIK UNTUK UNDUH PDF D3", data=st.session_state['pdf_d3'], file_name=f"Format_D3_{desa_aktif}.pdf", mime="application/pdf", width='stretch')

        with st.expander("📄 Format D2 (Rincian Penerimaan Per DKM)"):
            if st.button("🔄 Buat / Perbarui D2", width='stretch'):
                st.session_state['pdf_d2'] = mc.cetak_d2_desa(DB_NAME, desa_aktif, tempat_ba, tgl_ba)
            if 'pdf_d2' in st.session_state:
                st.download_button("📥 KLIK UNTUK UNDUH PDF D2", data=st.session_state['pdf_d2'], file_name=f"Format_D2_{desa_aktif}.pdf", mime="application/pdf", width='stretch')

        with st.expander("📄 Format D4 & D5 (Distribusi Sabilillah)"):
            if st.button("🔄 Buat / Perbarui D4 & D5", width='stretch'):
                st.session_state['pdf_d45'] = mc.cetak_d45_desa(DB_NAME, desa_aktif, tempat_ba, tgl_ba)
            if 'pdf_d45' in st.session_state:
                st.download_button("📥 KLIK UNTUK UNDUH PDF D4 & D5", data=st.session_state['pdf_d45'], file_name=f"Format_D4_D5_{desa_aktif}.pdf", mime="application/pdf", width='stretch')

        with st.expander("📄 Format D6 (Asnaf Amilin)"):
            if st.button("🔄 Buat / Perbarui D6", width='stretch'):
                st.session_state['pdf_d6'] = mc.cetak_d6_desa(DB_NAME, desa_aktif, tempat_ba, tgl_ba)
            if 'pdf_d6' in st.session_state:
                st.download_button("📥 KLIK UNTUK UNDUH PDF D6", data=st.session_state['pdf_d6'], file_name=f"Format_D6_{desa_aktif}.pdf", mime="application/pdf", width='stretch')
                
        with st.expander("🎟️ BAST Kupon Infaq"):
            if st.button("🔄 Buat / Perbarui Kupon", width='stretch'):
                st.session_state['pdf_kupon'] = mc.cetak_kupon_desa(DB_NAME, desa_aktif, tempat_ba, tgl_ba)
            if 'pdf_kupon' in st.session_state:
                st.download_button("📥 KLIK UNTUK UNDUH BAST KUPON", data=st.session_state['pdf_kupon'], file_name=f"BAST_Kupon_{desa_aktif}.pdf", mime="application/pdf", width='stretch')
        with st.expander("🐄 Laporan Hewan Qurban (Desa)"):
            if st.button("🔄 Buat Laporan Qurban", width='stretch'):
                st.session_state['pdf_q_desa'] = mc.cetak_qurban_desa(DB_NAME, desa_aktif, tempat_ba, tgl_ba)
            if 'pdf_q_desa' in st.session_state:
                st.download_button("📥 UNDUH PDF QURBAN", data=st.session_state['pdf_q_desa'], file_name=f"Laporan_Qurban_{desa_aktif}.pdf", mime="application/pdf", width='stretch')

        with st.expander("🕌 Laporan Majlis Ta'lim (Desa)"):
            if st.button("🔄 Buat Laporan Majlis", width='stretch'):
                st.session_state['pdf_m_desa'] = mc.cetak_majlis_desa(DB_NAME, desa_aktif, tempat_ba, tgl_ba)
            if 'pdf_m_desa' in st.session_state:
                st.download_button("📥 UNDUH PDF MAJLIS", data=st.session_state['pdf_m_desa'], file_name=f"Laporan_Majlis_{desa_aktif}.pdf", mime="application/pdf", width='stretch')
    conn.close()