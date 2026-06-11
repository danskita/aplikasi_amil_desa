import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os

# ==========================================
# 1. KONFIGURASI HALAMAN (Wajib Paling Atas)
# ==========================================
st.set_page_config(
    page_title="Laporan Terpadu Amil", 
    page_icon="🕌", 
    layout="wide"
)

DB_NAME = "database_upz_desa.db"

# ==========================================
# 2. AUTO-SETUP DATABASE & MULTI-USER
# ==========================================
def setup_multiuser():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Buat tabel pengguna jika belum ada
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT,
                    nama_desa TEXT
                )''')
    # Buat akun Admin utama jika database pengguna masih kosong
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role, nama_desa) VALUES ('admin', 'admin123', 'admin', 'Pusat')")
        try: c.execute("INSERT INTO pengaturan (nama_desa) VALUES ('Pusat')")
        except: pass

    # Tambahkan kolom nama_desa di semua tabel master jika belum ada (opsional/patch)
    tabel_list = ["pengaturan", "qurban", "master_dkm", "guru_ngaji", "majlis_talim", "master_kategori_sab", "master_jabatan_amil"]
    for tb in tabel_list:
        try: c.execute(f"ALTER TABLE {tb} ADD COLUMN nama_desa TEXT")
        except: pass
        
    conn.commit()
    conn.close()

setup_multiuser()

# ==========================================
# 3. SISTEM LOGIN & SESSION (PINTU MASUK)
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
            
            if st.button("Masuk / Login", use_container_width=True, type="primary"):
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

# Hentikan eksekusi web jika belum login
if not st.session_state["logged_in"]:
    form_login()
    st.stop()

# ==========================================
# 4. MENU NAVIGASI (SIDEBAR)
# ==========================================
st.sidebar.title(f"🕌 Amil {st.session_state['nama_desa']}")
st.sidebar.caption(f"Hak Akses: {st.session_state['role'].title()}")

if st.sidebar.button("🚪 Keluar (Logout)", use_container_width=True):
    logout()

st.sidebar.markdown("---")

menu_halaman = [
    "📊 Dashboard Utama",
    "📥 Penerimaan Zakat",
    "📤 Distribusi UPZ",
    "🐄 Data Qurban",
    "🕌 Data Majlis Ta'lim",
    "📂 Kelola Data Master",
    "🖨️ Cetak Laporan PDF",
    "📁 Arsip Data Lama",
    "⚙️ Pengaturan"
]

# Tambahkan menu ekstra jika yang login adalah Admin
# Tambahkan menu ekstra jika yang login adalah Admin/Kecamatan
if st.session_state["role"] == "kecamatan" or st.session_state["role"] == "admin":
    menu_halaman.append("👥 Kelola Pengguna")

pilihan_menu = st.sidebar.radio("Pilih Halaman:", menu_halaman)
st.sidebar.markdown("---")
st.sidebar.info("💡 Buka di HP untuk kemudahan input data saat di lapangan.")

# ==========================================
# LOGIKA HALAMAN DASHBOARD
# ==========================================
if pilihan_menu == "📊 Dashboard Utama":
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute("SELECT nama_desa FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
        res = c.fetchone()
        desa = res[0] if res and res[0] else st.session_state["nama_desa"]
        
        c.execute("SELECT SUM(total_beras), SUM(total_uang), SUM(infaq), SUM(jiwa_beras), SUM(jiwa_uang) FROM setoran_dkm WHERE nama_desa=?", (st.session_state["nama_desa"],))
        himpun = c.fetchone()
        t_beras = himpun[0] or 0; t_uang = himpun[1] or 0; t_infaq = himpun[2] or 0
        j_beras = himpun[3] or 0; j_uang = himpun[4] or 0
        
        st.title(f"📊 DASHBOARD AMIL DESA {desa.upper()}")
        st.markdown("Ringkasan Data Penghimpunan dan Penyaluran Zakat")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Muzakki", f"{j_beras + j_uang} Jiwa")
        col2.metric("Total Beras", f"{t_beras:,.2f} Kg")
        col3.metric("Total Uang Zakat", f"Rp {int(t_uang):,}")
        col4.metric("Total Infaq", f"Rp {int(t_infaq):,}")
            
        st.markdown("---")
        st.subheader("Daftar Setoran per UPZ DKM")
        
        query_tabel = f"""
        SELECT 
            nama_dkm AS 'Nama DKM / Wakil', 
            (jiwa_beras + jiwa_uang) AS 'Total Jiwa', 
            total_beras AS 'Total Beras (Kg)', 
            total_uang AS 'Total Uang Zakat (Rp)', 
            infaq AS 'Total Infaq (Rp)' 
        FROM setoran_dkm 
        WHERE nama_desa = '{st.session_state["nama_desa"]}'
        ORDER BY nama_dkm ASC
        """
        df_dkm = pd.read_sql_query(query_tabel, conn)
        st.dataframe(df_dkm, use_container_width=True, hide_index=True)
        conn.close()
        
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat database: {e}")

# ==========================================
# PENERIMAAN ZAKAT
# ==========================================
elif pilihan_menu == "📥 Penerimaan Zakat":
    st.title("📥 Penerimaan Zakat & Infaq DKM")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT nama_dkm FROM master_dkm WHERE nama_desa=? ORDER BY nama_dkm ASC", (st.session_state["nama_desa"],))
    daftar_dkm = [row[0] for row in c.fetchall()]

    c.execute("SELECT tarif_beras, tarif_uang, nominal_kupon FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
    res_tarif = c.fetchone()
    t_b = res_tarif[0] if res_tarif and res_tarif[0] else 0
    t_u = res_tarif[1] if res_tarif and res_tarif[1] else 0
    nom_kupon = res_tarif[2] if res_tarif and res_tarif[2] else 0

    st.markdown("---")
    st.subheader("Form Input Setoran Baru")
    
    if daftar_dkm:
        selected_dkm = st.selectbox("Pilih UPZ DKM Induk:", ["Pilih DKM..."] + daftar_dkm)
    else:
        selected_dkm = st.text_input("Nama UPZ DKM Induk (Data Master Kosong):")

    alamat_def = ""; wakil_list = []
    if selected_dkm and selected_dkm != "Pilih DKM...":
        c.execute("SELECT alamat_dkm, perwakilan FROM master_dkm WHERE nama_dkm=? AND nama_desa=?", (selected_dkm, st.session_state["nama_desa"]))
        res_master = c.fetchone()
        if res_master:
            alamat_def = res_master[0] if res_master[0] else ""
            if res_master[1]: wakil_list = [x.strip() for x in res_master[1].split(",") if x.strip()]

    if selected_dkm and selected_dkm != "Pilih DKM...":
        with st.form("form_penerimaan"):
            col1, col2 = st.columns(2)
            with col1:
                alamat_dkm = st.text_input("Alamat Pusat DKM:", value=alamat_def)
                alamat_wakil = st.text_input("Cakupan Wilayah / Alamat Wakil:")
            with col2:
                if wakil_list:
                    wakil_upz = st.selectbox("Wakil UPZ / Mushola (Otomatis dari Master):", ["Pusat (Tidak ada wakil)"] + wakil_list)
                    if wakil_upz == "Pusat (Tidak ada wakil)": wakil_upz = ""
                else:
                    wakil_upz = st.text_input("Wakil UPZ (Ketik manual karena Master kosong):")

            st.markdown("---")
            mode_input = st.radio("Pilih Metode Input Data Zakat:", ["Berdasarkan Data Jiwa", "Berdasarkan Setoran Fisik"], horizontal=True)
            col_zakat, col_infaq = st.columns(2)
            
            with col_zakat:
                st.write("📝 **Rincian Zakat**")
                j_b = st.number_input("Jumlah Muzakki Beras (Jiwa):", min_value=0, value=0)
                j_u = st.number_input("Jumlah Muzakki Uang (Jiwa):", min_value=0, value=0)
                st.caption("Atau isi bagian bawah ini jika memilih mode Fisik:")
                f_b = st.number_input("Fisik Beras Disetor (Kg):", min_value=0.0, value=0.0, step=0.5)
                f_u = st.number_input("Fisik Uang Disetor (Rp):", min_value=0, value=0, step=1000)

            with col_infaq:
                st.write("🎟️ **Administrasi Kupon Infaq**")
                k_diterima = st.number_input("Kupon Awal Diterima (Lembar):", min_value=0, value=0)
                k_terjual = st.number_input("Kupon Laku / Terjual (Lembar):", min_value=0, value=0)
                k_kembali = st.number_input("Kupon Sisa / Kembali (Lembar):", min_value=0, value=0)
                infaq_uang = st.number_input("Nominal Uang Infaq (Rp):", min_value=0, value=0)

            submit_penerimaan = st.form_submit_button("💾 Simpan Data Setoran", use_container_width=True)

            if submit_penerimaan:
                tipe_input = "jiwa" if mode_input == "Berdasarkan Data Jiwa" else "fisik"
                tb = 0.0; tu = 0.0; fb = 0.0; fu = 0.0; jiwa_b = j_b; jiwa_u = j_u

                if tipe_input == "jiwa":
                    tb = jiwa_b * t_b; tu = jiwa_u * t_u
                    fb = tb * 0.175; fu = tu * 0.175
                else:
                    fb = f_b; fu = f_u
                    tb = fb / 0.175 if fb > 0 else 0; tu = fu / 0.175 if fu > 0 else 0
                    jiwa_b = int(round(tb / t_b)) if t_b > 0 else 0; jiwa_u = int(round(tu / t_u)) if t_u > 0 else 0

                infaq_rp = float(infaq_uang) if infaq_uang > 0 else float(k_terjual * nom_kupon)

                try:
                    c.execute('''INSERT INTO setoran_dkm 
                                 (nama_dkm, alamat_dkm, perwakilan, alamat_perwakilan, tipe_input, 
                                 jiwa_beras, jiwa_uang, fisik_beras, fisik_uang, total_beras, 
                                 total_uang, infaq, kupon_diterima, kupon_terjual, kupon_kembali, nama_desa)
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                              (selected_dkm, alamat_dkm, wakil_upz, alamat_wakil, tipe_input, 
                               jiwa_b, jiwa_u, fb, fu, tb, tu, infaq_rp, k_diterima, k_terjual, k_kembali, st.session_state["nama_desa"]))
                    conn.commit()
                    st.success(f"Berhasil! Data setoran dari **{selected_dkm}** sudah disimpan.")
                    st.rerun() 
                except Exception as e:
                    st.error(f"Gagal menyimpan data: {e}")

    st.markdown("---")
    st.subheader("📋 Daftar Penerimaan Terkini")
    query = f"SELECT id as 'ID', nama_dkm as 'Nama DKM', perwakilan as 'Wakil UPZ', (jiwa_beras + jiwa_uang) as 'Total Jiwa', total_beras as 'Total Beras (Kg)', total_uang as 'Total Uang Zakat (Rp)', infaq as 'Infaq (Rp)' FROM setoran_dkm WHERE nama_desa = '{st.session_state["nama_desa"]}' ORDER BY id DESC"
    df_setoran = pd.read_sql_query(query, conn)
    
    if not df_setoran.empty:
        st.dataframe(df_setoran, use_container_width=True, hide_index=True)
        col_del, col_edit = st.columns(2)
        
        with col_del:
            with st.expander("🗑️ Hapus Data Setoran"):
                id_hapus = st.number_input("Masukkan ID baris yang ingin dihapus:", min_value=0, step=1, key="del_pen")
                if st.button("Hapus Data", use_container_width=True):
                    c.execute("DELETE FROM setoran_dkm WHERE id=? AND nama_desa=?", (id_hapus, st.session_state["nama_desa"]))
                    conn.commit(); st.success("Terhapus!"); st.rerun()
                    
        with col_edit:
            with st.expander("✏️ Ubah Data (Edit)"):
                daftar_pilihan = [f"{str(r['ID'])} - {str(r['Nama DKM'])} ({str(r['Wakil UPZ'])})" if r['Wakil UPZ'] else f"{str(r['ID'])} - {str(r['Nama DKM'])}" for i, r in df_setoran.iterrows()]
                pilihan_edit = st.selectbox("Pilih Data yang akan diedit:", ["Pilih Data..."] + daftar_pilihan)
                
                if pilihan_edit != "Pilih Data...":
                    id_edit = pilihan_edit.split(" - ")[0]
                    c.execute("SELECT nama_dkm, jiwa_beras, jiwa_uang, fisik_beras, fisik_uang, infaq, tipe_input FROM setoran_dkm WHERE id=? AND nama_desa=?", (id_edit, st.session_state["nama_desa"]))
                    row_edit = c.fetchone()
                    if row_edit:
                        with st.form("form_edit_penerimaan"):
                            e_jb = st.number_input("Muzakki Beras (Jiwa):", value=int(row_edit[1] or 0))
                            e_ju = st.number_input("Muzakki Uang (Jiwa):", value=int(row_edit[2] or 0))
                            e_fb = st.number_input("Fisik Beras (Kg):", value=float(row_edit[3] or 0.0), step=0.5)
                            e_fu = st.number_input("Fisik Uang (Rp):", value=int(row_edit[4] or 0), step=1000)
                            e_inf = st.number_input("Total Infaq (Rp):", value=int(row_edit[5] or 0), step=1000)
                            
                            if st.form_submit_button("💾 Simpan Perubahan", use_container_width=True):
                                tipe_input = row_edit[6]
                                tb_baru = 0.0; tu_baru = 0.0; fb_baru = 0.0; fu_baru = 0.0
                                jiwa_b = e_jb; jiwa_u = e_ju
                                
                                if tipe_input == "jiwa":
                                    tb_baru = jiwa_b * t_b; tu_baru = jiwa_u * t_u
                                    fb_baru = tb_baru * 0.175; fu_baru = tu_baru * 0.175
                                else:
                                    fb_baru = e_fb; fu_baru = e_fu
                                    tb_baru = fb_baru / 0.175 if fb_baru > 0 else 0; tu_baru = fu_baru / 0.175 if fu_baru > 0 else 0
                                    jiwa_b = int(round(tb_baru / t_b)) if t_b > 0 else 0; jiwa_u = int(round(tu_baru / t_u)) if t_u > 0 else 0
                                    
                                c.execute('''UPDATE setoran_dkm SET jiwa_beras=?, jiwa_uang=?, fisik_beras=?, fisik_uang=?, total_beras=?, total_uang=?, infaq=? WHERE id=?''', (jiwa_b, jiwa_u, fb_baru, fu_baru, tb_baru, tu_baru, e_inf, id_edit))
                                conn.commit(); st.success("Tersimpan!"); st.rerun()
    conn.close()

# ==========================================
# DISTRIBUSI UPZ
# ==========================================
elif pilihan_menu == "📤 Distribusi UPZ":
    st.title("📤 Distribusi Alokasi UPZ Desa")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    tab_sab, tab_amil = st.tabs(["📌 Asnaf Sabilillah (87.5%)", "📌 Asnaf Amilin (12.5%)"])

    with tab_sab:
        try:
            c.execute("SELECT nama FROM master_kategori_sab WHERE nama_desa=? ORDER BY nama ASC", (st.session_state["nama_desa"],))
            daftar_sab = [row[0] for row in c.fetchall()]
        except: daftar_sab = []

        with st.form("form_sab"):
            col1, col2 = st.columns(2)
            with col1:
                prog_sab = st.selectbox("Kategori Program:", ["Pilih Program..."] + daftar_sab) if daftar_sab else st.text_input("Kategori Program:")
                penerima_sab = st.text_input("Nama Penerima (Mustahik):")
            with col2:
                beras_sab = st.number_input("Disalurkan Beras (Kg):", min_value=0.0, value=0.0, step=0.5)
                uang_sab = st.number_input("Disalurkan Uang (Rp):", min_value=0, value=0, step=1000)
            
            if st.form_submit_button("💾 Simpan Data Sabilillah"):
                c.execute("INSERT INTO sabilillah (program, penerima, beras, uang, nama_desa) VALUES (?,?,?,?,?)", (prog_sab, penerima_sab, beras_sab, uang_sab, st.session_state["nama_desa"]))
                conn.commit(); st.success("Tersimpan!"); st.rerun()

        df_sab = pd.read_sql_query(f"SELECT id as ID, program as 'Program', penerima as 'Nama Penerima', beras as 'Beras (Kg)', uang as 'Uang (Rp)' FROM sabilillah WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        if not df_sab.empty:
            st.dataframe(df_sab, use_container_width=True, hide_index=True)
            cd, ce = st.columns(2)
            with cd:
                with st.expander("🗑️ Hapus Sabilillah"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="dsab")
                    if st.button("Hapus"): c.execute("DELETE FROM sabilillah WHERE id=?", (id_h,)); conn.commit(); st.rerun()

    with tab_amil:
        try:
            c.execute("SELECT nama FROM master_jabatan_amil WHERE nama_desa=? ORDER BY nama ASC", (st.session_state["nama_desa"],))
            daftar_amil = [row[0] for row in c.fetchall()]
        except: daftar_amil = []

        with st.form("form_amil"):
            col1, col2 = st.columns(2)
            with col1:
                nama_amil = st.text_input("Nama Pengurus (Amil):")
                jabatan_amil = st.selectbox("Posisi Jabatan:", ["Pilih Jabatan..."] + daftar_amil) if daftar_amil else st.text_input("Posisi Jabatan:")
            with col2:
                beras_amil = st.number_input("Disalurkan Beras (Kg):", min_value=0.0, value=0.0, step=0.5, key="b_amil")
                uang_amil = st.number_input("Disalurkan Uang (Rp):", min_value=0, value=0, step=1000, key="u_amil")
            
            if st.form_submit_button("💾 Simpan Data Amilin"):
                c.execute("INSERT INTO amilin (nama, jabatan, beras, uang, nama_desa) VALUES (?,?,?,?,?)", (nama_amil, jabatan_amil, beras_amil, uang_amil, st.session_state["nama_desa"]))
                conn.commit(); st.success("Tersimpan!"); st.rerun()

        df_amil = pd.read_sql_query(f"SELECT id as ID, nama as 'Nama Pengurus', jabatan as 'Jabatan', beras as 'Beras (Kg)', uang as 'Uang (Rp)' FROM amilin WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        if not df_amil.empty:
            st.dataframe(df_amil, use_container_width=True, hide_index=True)
            cd, ce = st.columns(2)
            with cd:
                with st.expander("🗑️ Hapus Amilin"):
                    id_h = st.number_input("ID Hapus:", min_value=0, key="dami")
                    if st.button("Hapus", key="h_ami"): c.execute("DELETE FROM amilin WHERE id=?", (id_h,)); conn.commit(); st.rerun()
    conn.close()

# ==========================================
# DATA QURBAN
# ==========================================
elif pilihan_menu == "🐄 Data Qurban":
    st.title("🐄 Data Hewan Qurban Desa")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("SELECT nama_dkm FROM master_dkm WHERE nama_desa=? ORDER BY nama_dkm ASC", (st.session_state["nama_desa"],))
        daftar_dkm = [row[0] for row in c.fetchall()]
    except: daftar_dkm = []

    with st.form("form_qurban"):
        col1, col2 = st.columns(2)
        with col1:
            in_tahun = st.text_input("Tahun (Hijriah/Masehi):", value=str(datetime.datetime.now().year))
            in_dkm = st.selectbox("Nama DKM / Wilayah:", ["Pilih DKM..."] + daftar_dkm) if daftar_dkm else st.text_input("Nama DKM:")
            in_jenis = st.selectbox("Jenis Hewan Qurban:", ["Sapi", "Domba", "Kambing", "Kerbau"])
        with col2:
            in_hewan = st.number_input("Jumlah Hewan (Ekor):", min_value=0, value=0)
            in_mudhohi = st.number_input("Jumlah Mudhohi (Orang):", min_value=0, value=0, help="0 = hitung otomatis")

        if st.form_submit_button("💾 Simpan Data Qurban"):
            if in_mudhohi == 0: in_mudhohi = in_hewan * (7 if in_jenis in ["Sapi", "Kerbau"] else 1)
            c.execute("INSERT INTO qurban (tahun, nama_dkm, jenis_hewan, jumlah_hewan, jumlah_mudhohi, nama_desa) VALUES (?,?,?,?,?,?)", (in_tahun, in_dkm, in_jenis, in_hewan, in_mudhohi, st.session_state["nama_desa"]))
            conn.commit(); st.rerun()

    df_qurban = pd.read_sql_query(f"SELECT id as ID, tahun as Tahun, nama_dkm as 'Nama DKM', jenis_hewan as 'Hewan', jumlah_hewan as 'Ekor', jumlah_mudhohi as 'Mudhohi' FROM qurban WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
    if not df_qurban.empty: st.dataframe(df_qurban, use_container_width=True, hide_index=True)
    conn.close()

# ==========================================
# KELOLA DATA MASTER
# ==========================================
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
            if st.form_submit_button("Simpan"):
                c.execute("INSERT INTO master_dkm (nama_dkm, ketua_dkm, alamat_dkm, perwakilan, nama_desa) VALUES (?,?,?,?,?)", (i_nm.upper(), i_kt, i_al, i_wk, st.session_state["nama_desa"]))
                conn.commit(); st.rerun()
        df_dkm = pd.read_sql_query(f"SELECT id as ID, nama_dkm as DKM, ketua_dkm as Ketua, alamat_dkm as Alamat FROM master_dkm WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        st.dataframe(df_dkm, use_container_width=True, hide_index=True)

    with t2:
        with st.form("f_ngaji"):
            n_nm = st.text_input("Nama Pengajar:")
            n_lm = st.text_input("Lembaga:")
            n_dk = st.text_input("DKM Terkait:")
            if st.form_submit_button("Simpan"):
                c.execute("INSERT INTO guru_ngaji (nama, lembaga, dkm, nama_desa) VALUES (?,?,?,?)", (n_nm, n_lm, n_dk, st.session_state["nama_desa"]))
                conn.commit(); st.rerun()
        df_ng = pd.read_sql_query(f"SELECT id as ID, nama, lembaga, dkm FROM guru_ngaji WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
        st.dataframe(df_ng, use_container_width=True, hide_index=True)

    with t3:
        with st.form("f_ksab"):
            s_nm = st.text_input("Kategori:")
            s_bb = st.number_input("Bobot:", value=0.0)
            if st.form_submit_button("Simpan"):
                c.execute("INSERT INTO master_kategori_sab (nama, bobot, nama_desa) VALUES (?,?,?)", (s_nm, s_bb, st.session_state["nama_desa"]))
                conn.commit(); st.rerun()

    with t4:
        with st.form("f_jami"):
            a_nm = st.text_input("Jabatan:")
            a_bb = st.number_input("Bobot:", value=0.0)
            if st.form_submit_button("Simpan"):
                c.execute("INSERT INTO master_jabatan_amil (nama, bobot, nama_desa) VALUES (?,?,?)", (a_nm, a_bb, st.session_state["nama_desa"]))
                conn.commit(); st.rerun()
    conn.close()

# ==========================================
# DATA MAJLIS TA'LIM
# ==========================================
elif pilihan_menu == "🕌 Data Majlis Ta'lim":
    st.title("🕌 Data Majlis Ta'lim")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    with st.form("f_mj"):
        m_nm = st.text_input("Nama Majlis:")
        m_pim = st.text_input("Pimpinan:")
        if st.form_submit_button("Simpan"):
            c.execute("INSERT INTO majlis_talim (nama_majlis, pimpinan, nama_desa) VALUES (?,?,?)", (m_nm, m_pim, st.session_state["nama_desa"]))
            conn.commit(); st.rerun()
    df_mj = pd.read_sql_query(f"SELECT id, nama_majlis, pimpinan FROM majlis_talim WHERE nama_desa='{st.session_state['nama_desa']}'", conn)
    st.dataframe(df_mj, use_container_width=True, hide_index=True)
    conn.close()

# ==========================================
# CETAK LAPORAN PDF
# ==========================================
elif pilihan_menu == "🖨️ Cetak Laporan PDF":
    st.title("🖨️ Pencetakan Dokumen Laporan (PDF)")
    st.write("Silakan atur tanggal titimangsa dan unduh laporanmu langsung ke perangkat.")

    try: from fpdf import FPDF
    except ImportError: st.error("Library FPDF belum terinstall."); st.stop()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nama_desa FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
    p_desa = c.fetchone()
    desa_default = p_desa[0].capitalize() if p_desa and p_desa[0] else st.session_state["nama_desa"]

    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("Atur Titimangsa Surat")
        with st.container(border=True):
            no_ba = st.text_input("Nomor Surat:", value=f"......./BAST/DPH/III/{datetime.datetime.now().year}")
            hari_ba = st.text_input("Hari:", value="Senin")
            tgl_ba = st.text_input("Tanggal Surat:", value="15 Ramadhan")
            tempat_ba = st.text_input("Tempat TTD:", value=desa_default)

    def cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path="", is_landscape=False):
        page_width = 297 if is_landscape else 210
        margin_side = 10 
        pdf.set_y(10)
        if logo_path and os.path.exists(logo_path):
            try: pdf.image(logo_path, x=margin_side, y=10, w=22)
            except: pass
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 6, "BADAN AMIL ZAKAT NASIONAL (BAZNAS)", ln=True, align="C")
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 7, f"UNIT PENGUMPUL ZAKAT (UPZ) DESA {desa.upper()}", ln=True, align="C")
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 6, f"KECAMATAN {kec.upper()} - KABUPATEN {kab.upper()}", ln=True, align="C")
        pdf.ln(5)
        y_garis = max(pdf.get_y(), 34)
        line_width = page_width - (margin_side * 2)
        pdf.set_line_width(0.8)
        pdf.line(margin_side, y_garis, margin_side + line_width, y_garis)
        pdf.set_line_width(0.2)
        pdf.line(margin_side, y_garis + 1, margin_side + line_width, y_garis + 1)
        pdf.set_y(y_garis + 5)

    with col2:
        st.subheader("Daftar Dokumen Siap Unduh")
        
        # --- D3 ---
        with st.expander("📄 Format D3 (Rekapitulasi 100%)", expanded=True):
            if st.button("Siapkan Dokumen D3", use_container_width=True):
                c.execute("SELECT nama_desa, kepala_desa, nama_kecamatan, kabupaten, ketua_upz, logo_path, no_hp, total_jiwa, total_kk FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
                p_data = c.fetchone()
                desa, kades, kec, kab, ketua, logo_path, no_hp, total_jiwa, total_kk = p_data if p_data else ("", "", "", "", "", "", "", 0, 0)
                
                c.execute("SELECT total_beras, total_uang, infaq FROM setoran_dkm WHERE nama_desa=?", (st.session_state["nama_desa"],))
                dkm_rows = c.fetchall()
                t_tb = sum(r[0] for r in dkm_rows); t_tu = sum(r[1] for r in dkm_rows); t_inf = sum(r[2] for r in dkm_rows)
                
                pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(10, 10, 10); pdf.add_page()
                cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "FORMAT D3 - REKAPITULASI PENERIMAAN (100%)", ln=True, align="C"); pdf.ln(10)
                pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Total Beras: {t_tb:.2f} Kg", ln=True); pdf.cell(0, 8, f"Total Uang: Rp {int(t_tu):,}", ln=True)
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("📥 UNDUH PDF D3", data=pdf_bytes, file_name=f"D3_{desa}.pdf", mime="application/pdf", use_container_width=True)

        # --- D2 ---
        with st.expander("📄 Format D2 (Penerimaan DKM Landscape)"):
            if st.button("Siapkan Dokumen D2", use_container_width=True):
                pdf = FPDF(orientation="L", unit="mm", format="A4"); pdf.add_page()
                cetak_kop_surat_resmi_web(pdf, st.session_state["nama_desa"], "", "", "", True)
                pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "FORMAT D2 - REKAP PER DKM", ln=True, align="C")
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("📥 UNDUH PDF D2", data=pdf_bytes, file_name="D2.pdf", mime="application/pdf", use_container_width=True)

        # --- D4 & D5 ---
        with st.expander("📄 Format D4 & D5 (Distribusi Sabilillah)"):
            if st.button("Siapkan Dokumen D4 & D5", use_container_width=True):
                pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.add_page()
                cetak_kop_surat_resmi_web(pdf, st.session_state["nama_desa"], "", "")
                pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "FORMAT D4 & D5 - SABILILLAH", ln=True, align="C")
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("📥 UNDUH PDF D4 D5", data=pdf_bytes, file_name="D4_D5.pdf", mime="application/pdf", use_container_width=True)

        # --- D6 ---
        with st.expander("📄 Format D6 (Asnaf Amilin)"):
            if st.button("Siapkan Dokumen D6", use_container_width=True):
                pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.add_page()
                cetak_kop_surat_resmi_web(pdf, st.session_state["nama_desa"], "", "")
                pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "FORMAT D6 - AMILIN", ln=True, align="C")
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("📥 UNDUH PDF D6", data=pdf_bytes, file_name="D6.pdf", mime="application/pdf", use_container_width=True)
                
        # --- BAST KUPON ---
        with st.expander("🎟️ BAST Kupon Infaq"):
            if st.button("Siapkan Dokumen Kupon", use_container_width=True):
                pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.add_page()
                cetak_kop_surat_resmi_web(pdf, st.session_state["nama_desa"], "", "")
                pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "BAST KUPON INFAQ", ln=True, align="C")
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("📥 UNDUH BAST KUPON", data=pdf_bytes, file_name="BAST_Kupon.pdf", mime="application/pdf", use_container_width=True)
    conn.close()

# ==========================================
# ARSIP DATA LAMA
# ==========================================
elif pilihan_menu == "📁 Arsip Data Lama":
    st.title("📁 Arsip Data Tahunan")
    st.info("Fitur pengelolaan arsip data lama.")

# ==========================================
# PENGATURAN PROFIL DESA
# ==========================================
elif pilihan_menu == "⚙️ Pengaturan":
    st.title("⚙️ Pengaturan Profil Desa")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
    data = c.fetchone()
    
    if not data:
        c.execute("INSERT INTO pengaturan (nama_desa) VALUES (?)", (st.session_state["nama_desa"],))
        conn.commit()
        c.execute("SELECT * FROM pengaturan WHERE nama_desa=?", (st.session_state["nama_desa"],))
        data = c.fetchone()

    with st.form("form_pengaturan"):
        col1, col2 = st.columns(2)
        with col1:
            in_desa = st.text_input("Nama Desa:", value=data[1] if data[1] else st.session_state["nama_desa"], disabled=True)
            in_kades = st.text_input("Kepala Desa:", value=data[2] if data[2] else "")
            in_kec = st.text_input("Kecamatan:", value=data[3] if data[3] else "")
            in_kab = st.text_input("Kabupaten:", value=data[4] if data[4] else "")
        with col2:
            in_ketua = st.text_input("Ketua UPZ:", value=data[5] if data[5] else "")
            in_sek = st.text_input("Sekretaris:", value=data[6] if data[6] else "")
            in_ben = st.text_input("Bendahara:", value=data[7] if data[7] else "")
        
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            in_tarif = st.number_input("Tarif Zakat Uang (Rp):", value=int(data[9]) if data[9] else 0)
        with col4:
            in_nom_kupon = st.number_input("Nominal Kupon Infaq (Rp):", value=int(data[13]) if len(data)>13 and data[13] else 0)

        if st.form_submit_button("💾 Simpan Pengaturan", use_container_width=True):
            c.execute('''UPDATE pengaturan SET 
                         kepala_desa=?, nama_kecamatan=?, kabupaten=?, 
                         ketua_upz=?, sekretaris=?, bendahara=?, tarif_uang=?, nominal_kupon=?
                         WHERE nama_desa=?''', 
                      (in_kades, in_kec, in_kab, in_ketua, in_sek, in_ben, float(in_tarif), float(in_nom_kupon), st.session_state["nama_desa"]))
            conn.commit()
            st.success("Pengaturan berhasil disimpan!"); st.rerun()
    conn.close()

# ==========================================
# KELOLA PENGGUNA (KHUSUS ADMIN)
# ==========================================
elif pilihan_menu == "👥 Kelola Pengguna":
    st.title("👥 Kelola Akun Pengguna (Multi-Desa)")
    if st.session_state["role"] != "kecamatan" and st.session_state["role"] != "admin":
        st.error("Hanya Admin Pusat yang bisa mengakses halaman ini!")
        st.stop()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    with st.form("form_user"):
        st.subheader("Buat Akun UPZ Desa Baru")
        col1, col2 = st.columns(2)
        with col1:
            u_desa = st.text_input("Nama Desa (Cth: Sukamaju):")
            u_name = st.text_input("Username Login:")
        with col2:
            u_pass = st.text_input("Password Login:")
            u_role = st.selectbox("Hak Akses:", ["user", "admin"])

        if st.form_submit_button("💾 Daftarkan Desa", use_container_width=True):
            if u_name and u_pass and u_desa:
                try:
                    c.execute("INSERT INTO users (username, password, role, nama_desa) VALUES (?,?,?,?)", (u_name, u_pass, u_role, u_desa))
                    c.execute("INSERT INTO pengaturan (nama_desa) VALUES (?)", (u_desa,))
                    conn.commit()
                    st.success(f"Akun untuk UPZ Desa {u_desa} berhasil dibuat!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal! Username mungkin sudah terpakai. Detail: {e}")
            else:
                st.error("Data wajib diisi lengkap!")

    st.markdown("---")
    df_users = pd.read_sql_query("SELECT id as ID, username as Username, role as Hak_Akses, nama_desa as 'Nama Desa' FROM users", conn)
    st.dataframe(df_users, use_container_width=True, hide_index=True)
    conn.close()

elif pilihan_menu == "🖨️ Cetak Laporan PDF":
    st.title("🖨️ Pencetakan Dokumen Laporan (PDF)")
    st.write("Silakan atur tanggal titimangsa dan unduh laporanmu langsung ke perangkat.")

    # PENTING: Cek apakah library FPDF sudah terinstall
    try:
        from fpdf import FPDF
    except ImportError:
        st.error("Library FPDF belum terinstall. Buka terminal dan ketik: pip install fpdf")
        st.stop()

    import datetime
    import os

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nama_desa FROM pengaturan WHERE id=1")
    p_desa = c.fetchone()
    desa_default = p_desa[0].capitalize() if p_desa and p_desa[0] else "Desa"

    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("Atur Titimangsa Surat")
        with st.container(border=True):
            no_ba = st.text_input("Nomor Surat:", value=f"......./BAST/DPH/III/{datetime.datetime.now().year}")
            hari_ba = st.text_input("Hari:", value="Senin")
            tgl_ba = st.text_input("Tanggal Surat (Titimangsa):", value="15 Ramadhan 1446")
            tempat_ba = st.text_input("Tempat TTD:", value=desa_default)
            st.info("💡 Data ini akan tercetak otomatis di bagian bawah laporan.")

    # ==========================================
    # FUNGSI HELPER KOP SURAT UNTUK WEB
    # ==========================================
    def cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path="", is_landscape=False):
        page_width = 297 if is_landscape else 210
        margin_side = 10 
        pdf.set_y(10)
        if logo_path and os.path.exists(logo_path):
            try: pdf.image(logo_path, x=margin_side, y=10, w=22)
            except: pass
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 6, "BADAN AMIL ZAKAT NASIONAL (BAZNAS)", ln=True, align="C")
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 7, f"UNIT PENGUMPUL ZAKAT (UPZ) DESA {desa.upper()}", ln=True, align="C")
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 6, f"KECAMATAN {kec.upper()} - KABUPATEN {kab.upper()}", ln=True, align="C")
        pdf.ln(5)
        y_garis = max(pdf.get_y(), 34)
        line_width = page_width - (margin_side * 2)
        pdf.set_line_width(0.8)
        pdf.line(margin_side, y_garis, margin_side + line_width, y_garis)
        pdf.set_line_width(0.2)
        pdf.line(margin_side, y_garis + 1, margin_side + line_width, y_garis + 1)
        pdf.set_y(y_garis + 5)

    # ==========================================
    # AREA DAFTAR DOKUMEN UNDUH
    # ==========================================
    with col2:
        st.subheader("Daftar Dokumen Siap Unduh")
        
        # ------------------------------------------
        # TOMBOL 1: FORMAT D3 (Rekap 100%)
        # ------------------------------------------
        with st.expander("📄 Format D3 (Rekapitulasi 100%)", expanded=True):
            st.write("Rekapitulasi penerimaan & penyaluran keseluruhan tingkat desa.")
            
            # Sistem baru: Pengguna menekan tombol "Siapkan", lalu PDF dibuat di memori
            if st.button("Siapkan Dokumen D3", use_container_width=True):
                
                # 1. Ambil Data dari Database
                c.execute("SELECT nama_desa, kepala_desa, nama_kecamatan, kabupaten, ketua_upz, logo_path, no_hp, total_jiwa, total_kk FROM pengaturan WHERE id=1")
                p_data = c.fetchone()
                desa, kades, kec, kab, ketua, logo_path, no_hp, total_jiwa, total_kk = p_data
                
                c.execute("SELECT total_beras, total_uang, infaq FROM setoran_dkm")
                dkm_rows = c.fetchall()
                t_tb = sum(r[0] for r in dkm_rows); t_tu = sum(r[1] for r in dkm_rows); t_inf = sum(r[2] for r in dkm_rows)
                
                # 2. Gambar PDF (Logika aslimu dari modul_cetak.py)
                pdf = FPDF(orientation="P", unit="mm", format="A4")
                pdf.set_margins(10, 10, 10); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
                cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                
                pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "FORMAT D3 - REKAPITULASI PENERIMAAN & PENYALURAN (100%)", ln=True, align="C")
                pdf.set_font("Arial", "B", 12); pdf.cell(0, 6, f"TAHUN 1446 H / {datetime.datetime.now().year} M", ln=True, align="C"); pdf.ln(4)
                
                pdf.set_font("Arial", "B", 9)
                pdf.cell(25, 5, "Desa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(65, 5, f"{desa}", border=0)
                pdf.cell(30, 5, "Jumlah KK", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_kk} KK", border=0, ln=True)
                pdf.cell(25, 5, "Kecamatan", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(65, 5, f"{kec}", border=0)
                pdf.cell(30, 5, "Jumlah Jiwa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_jiwa} Jiwa", border=0, ln=True)
                pdf.cell(95, 5, "", border=0); pdf.cell(30, 5, "No. HP Pengumpul", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{no_hp}", border=0, ln=True)
                pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2); pdf.ln(6)
                
                pdf.set_font("Arial", "B", 11); pdf.cell(0, 8, "A. PENGHIMPUNAN KESELURUHAN", ln=True)
                pdf.set_font("Arial", "", 10); pdf.cell(10, 8, "1."); pdf.cell(40, 8, "Zakat Fitrah Beras"); pdf.cell(10, 8, ":"); pdf.cell(50, 8, f"{t_tb:.2f} Kg", ln=True)
                pdf.cell(10, 8, "2."); pdf.cell(40, 8, "Zakat Fitrah Uang"); pdf.cell(10, 8, ":"); pdf.cell(50, 8, f"Rp {int(t_tu):,}", ln=True)
                pdf.cell(10, 8, "3."); pdf.cell(40, 8, "Infaq Ramadhan"); pdf.cell(10, 8, ":"); pdf.cell(50, 8, f"Rp {int(t_inf):,} (Dialokasikan untuk Guru Ngaji)", ln=True); pdf.ln(5)
                
                pdf.set_font("Arial", "B", 11); pdf.cell(0, 8, "B. ALOKASI PENYALURAN ZAKAT FITRAH (100%)", ln=True)
                pdf.set_font("Arial", "B", 10); pdf.cell(10, 10, "No", border=1, align="C"); pdf.cell(70, 10, "Pihak Pengelola", border=1, align="C"); pdf.cell(25, 10, "Persentase", border=1, align="C"); pdf.cell(40, 10, "Beras (Kg)", border=1, align="C"); pdf.cell(45, 10, "Uang (Rp)", border=1, align="C"); pdf.ln()
                pdf.set_font("Arial", "", 10)
                pdf.cell(10, 8, "1", border=1, align="C"); pdf.cell(70, 8, "UPZ DKM (Fakir, Miskin, dll)", border=1); pdf.cell(25, 8, "82.5 %", border=1, align="C"); pdf.cell(40, 8, f"{t_tb*0.825:.2f} Kg", border=1, align="C"); pdf.cell(45, 8, f"Rp {int(t_tu*0.825):,}", border=1, align="R"); pdf.ln()
                pdf.cell(10, 8, "2", border=1, align="C"); pdf.cell(70, 8, "UPZ Desa (Sabilillah, Amil)", border=1); pdf.cell(25, 8, "6.5 %", border=1, align="C"); pdf.cell(40, 8, f"{t_tb*0.065:.2f} Kg", border=1, align="C"); pdf.cell(45, 8, f"Rp {int(t_tu*0.065):,}", border=1, align="R"); pdf.ln()
                pdf.cell(10, 8, "3", border=1, align="C"); pdf.cell(70, 8, "UPZ Kecamatan (Setoran)", border=1); pdf.cell(25, 8, "5.0 %", border=1, align="C"); pdf.cell(40, 8, f"{t_tb*0.05:.2f} Kg", border=1, align="C"); pdf.cell(45, 8, f"Rp {int(t_tu*0.05):,}", border=1, align="R"); pdf.ln()
                pdf.cell(10, 8, "4", border=1, align="C"); pdf.cell(70, 8, "BAZNAS Kabupaten (Setoran)", border=1); pdf.cell(25, 8, "6.0 %", border=1, align="C"); pdf.cell(40, 8, f"{t_tb*0.06:.2f} Kg", border=1, align="C"); pdf.cell(45, 8, f"Rp {int(t_tu*0.06):,}", border=1, align="R"); pdf.ln()
                pdf.set_font("Arial", "B", 10); pdf.cell(105, 8, "TOTAL KESELURUHAN ZAKAT (100%)", border=1, align="C"); pdf.cell(40, 8, f"{t_tb:.2f} Kg", border=1, align="C"); pdf.cell(45, 8, f"Rp {int(t_tu):,}", border=1, align="R"); pdf.ln()
                
                pdf.ln(15); pdf.set_font("Arial", "", 11)
                pdf.cell(90, 6, "Mengetahui,", border=0, align="C"); pdf.cell(100, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=True)
                pdf.cell(90, 6, "Kepala Desa,", border=0, align="C"); pdf.cell(100, 6, "Ketua UPZ Desa,", border=0, align="C", ln=True)
                pdf.ln(20); pdf.set_font("Arial", "B", 11)
                pdf.cell(90, 6, f"( {kades} )", border=0, align="C"); pdf.cell(100, 6, f"( {ketua} )", border=0, align="C", ln=True)
                
                # 3. MENGUBAH PDF MENJADI DATA UNDUHAN (Rahasia Web App!)
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                
                st.success("✨ Dokumen D3 berhasil disiapkan!")
                # Menampilkan tombol unduh yang aslinya
                st.download_button(
                    label="📥 UNDUH PDF D3 SEKARANG", 
                    data=pdf_bytes, 
                    file_name=f"Format_D3_{desa}.pdf", 
                    mime="application/pdf", 
                    use_container_width=True
                )

        # ------------------------------------------
        # TOMBOL 2: BA PENJUALAN BERAS
        # ------------------------------------------
        with st.expander("📜 Berita Acara Penjualan Beras"):
            st.write("Berita acara konversi beras menjadi uang tunai.")
            if st.button("Siapkan Dokumen BA Beras", use_container_width=True):
                c.execute("SELECT nama_desa, nama_kecamatan, kabupaten, beras_dijual, harga_jual_beras, kepala_desa, ketua_upz, logo_path FROM pengaturan WHERE id=1")
                p_ba = c.fetchone()
                desa, kec, kab, beras_dijual, harga_jual, kades, ketua, logo_path = p_ba
                beras_dijual = beras_dijual or 0; harga_jual = harga_jual or 0
                total_uang = beras_dijual * harga_jual
                
                if beras_dijual <= 0:
                    st.error("Belum ada catatan penjualan beras di menu Pengaturan!")
                else:
                    pdf = FPDF(orientation="P", unit="mm", format="A4")
                    pdf.set_margins(10, 10, 10); pdf.add_page(); cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                    
                    pdf.set_font("Arial", "B", 14); pdf.cell(190, 8, "BERITA ACARA KONVERSI / PENJUALAN BERAS ZAKAT", ln=True, align="C"); pdf.ln(10)
                    pdf.set_font("Arial", "", 12); pdf.multi_cell(190, 6, f"Pada hari ini, {hari_ba} tanggal {tgl_ba}, telah dilakukan penjualan fisik beras zakat fitrah yang bersumber murni dari Hak UPZ Desa (6.5%). Penjualan ini dilakukan untuk mengkonversi beras menjadi uang tunai guna mempermudah penyaluran kepada Asnaf Sabilillah dan Amil Desa."); pdf.ln(8)
                    
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(10, 8, "", ln=0); pdf.cell(60, 8, "Jumlah Beras Dijual", ln=0); pdf.cell(120, 8, f": {beras_dijual:.2f} Kg", ln=True)
                    pdf.cell(10, 8, "", ln=0); pdf.cell(60, 8, "Harga Jual per Kg", ln=0); pdf.cell(120, 8, f": Rp {int(harga_jual):,}", ln=True)
                    pdf.cell(10, 8, "", ln=0); pdf.cell(60, 8, "Total Uang Diterima", ln=0); pdf.cell(120, 8, f": Rp {int(total_uang):,}", ln=True)
                    
                    pdf.ln(25); pdf.set_font("Arial", "", 12)
                    pdf.cell(95, 8, "Mengetahui / Saksi,", align="C"); pdf.cell(95, 8, f"{tempat_ba}, {tgl_ba}", align="C", ln=True)
                    pdf.cell(95, 8, "Bendahara UPZ Desa", align="C"); pdf.cell(95, 8, f"Ketua UPZ Desa {desa.capitalize()}", align="C", ln=True)
                    pdf.ln(20); pdf.set_font("Arial", "B", 12)
                    pdf.cell(95, 8, "(...................................)", align="C"); pdf.cell(95, 8, f"( {ketua} )", align="C", ln=True)
                    
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    st.success("✨ Dokumen BA Beras berhasil disiapkan!")
                    st.download_button(label="📥 UNDUH PDF BA BERAS SEKARANG", data=pdf_bytes, file_name=f"BA_Penjualan_Beras_{desa}.pdf", mime="application/pdf", use_container_width=True)
    # ------------------------------------------
        # TOMBOL 3: FORMAT D2 (Penerimaan & Infaq)
        # ------------------------------------------
        with st.expander("📄 Format D2 (Penerimaan & Infaq)"):
            st.write("Rekapitulasi penerimaan Zakat Fitrah dan Infaq dari seluruh DKM (Landscape).")
            
            if st.button("Siapkan Dokumen D2", use_container_width=True):
                c.execute("SELECT nama_desa, kepala_desa, nama_kecamatan, kabupaten, ketua_upz, sekretaris, logo_path, no_hp, total_jiwa, total_kk FROM pengaturan WHERE id=1")
                p_data = c.fetchone()
                desa, kades, kec, kab, ketua, sekretaris, logo_path, no_hp, total_jiwa, total_kk = p_data
                
                c.execute("SELECT * FROM setoran_dkm ORDER BY nama_dkm ASC, perwakilan ASC")
                dkm_rows_detail = c.fetchall()
                
                # Setup PDF (Landscape)
                pdf = FPDF(orientation="L", unit="mm", format="A4")
                pdf.set_margins(10, 10, 10); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
                
                pdf.set_font("Arial", "", 10); pdf.set_xy(257, 10); pdf.cell(30, 6, "Model : D2", border=1, align="C")
                cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path, is_landscape=True)
                
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 6, "REKAPITULASI PENGUMPULAN ZAKAT FITRAH DAN INFAQ/SEDEKAH TINGKAT DESA", ln=True, align="C")
                pdf.cell(0, 6, f"BULAN RAMADHAN TAHUN 1446 H / {datetime.datetime.now().year} M", ln=True, align="C"); pdf.ln(5)
                
                pdf.set_font("Arial", "B", 9)
                pdf.cell(25, 5, "Desa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(90, 5, f"{desa}", border=0)
                pdf.cell(30, 5, "Jumlah KK", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_kk} KK", border=0, ln=True)
                pdf.cell(25, 5, "Kecamatan", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(90, 5, f"{kec}", border=0)
                pdf.cell(30, 5, "Jumlah Jiwa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_jiwa} Jiwa", border=0, ln=True)
                pdf.cell(120, 5, "", border=0); pdf.cell(30, 5, "No. HP Pengumpul", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{no_hp}", border=0, ln=True)
                pdf.line(10, pdf.get_y() + 2, 287, pdf.get_y() + 2); pdf.ln(5)

                def draw_header_d2(pdf):
                    y_h = pdf.get_y(); pdf.set_font("Arial", "B", 8)
                    pdf.cell(8, 10, "NO", 1, 0, "C"); pdf.cell(45, 10, "NAMA UPZ DKM / WAKIL", 1, 0, "C")
                    x1 = pdf.get_x(); pdf.cell(15, 5, "JIWA", "LRT", 0, "C"); pdf.cell(65, 5, "PENGUMPULAN ZAKAT", 1, 0, "C")
                    x_alo = pdf.get_x(); pdf.cell(144, 5, "ALOKASI PENYALURAN 100% (B=Beras, U=Uang)", 1, 1, "C")
                    pdf.set_xy(x1, y_h + 5); pdf.cell(15, 5, "(B / U)", "LRB", 0, "C")
                    pdf.cell(18, 5, "Beras(Kg)", 1, 0, "C"); pdf.cell(25, 5, "Uang(Rp)", 1, 0, "C"); pdf.cell(22, 5, "Infaq(Rp)", 1, 0, "C")
                    pdf.set_xy(x_alo, y_h + 5)
                    pdf.cell(36, 5, "DKM (82.5%)", 1, 0, "C"); pdf.cell(36, 5, "Desa (6.5%)", 1, 0, "C")
                    pdf.cell(36, 5, "Kec (5%)", 1, 0, "C"); pdf.cell(36, 5, "Kab (6%)", 1, 1, "C")

                draw_header_d2(pdf); pdf.set_font("Arial", "", 8)
                
                t_jb=0; t_ju=0; t_sb=0; t_tb=0; t_su=0; t_tu=0; t_inf=0; t_db=0; t_dsb=0; t_kcb=0; t_kbb=0; t_du=0; t_dsu=0; t_kcu=0; t_kbu=0
                
                for i, r in enumerate(dkm_rows_detail):
                    if pdf.get_y() > 175:
                        pdf.add_page(); draw_header_d2(pdf); pdf.set_font("Arial", "", 8)
                        
                    jb=int(r[6]or 0); ju=int(r[7]or 0); sb=r[8]or 0; su=r[9]or 0; tot_b=r[10]or 0; tot_u=r[11]or 0; inf=r[12]or 0
                    dkm_b=tot_b*0.825; desa_b=tot_b*0.065; kec_b=tot_b*0.05; kab_b=tot_b*0.06
                    dkm_u=tot_u*0.825; desa_u=tot_u*0.065; kec_u=tot_u*0.05; kab_u=tot_u*0.06
                    
                    t_jb+=jb; t_ju+=ju; t_sb+=sb; t_tb+=tot_b; t_su+=su; t_tu+=tot_u; t_inf+=inf
                    t_db+=dkm_b; t_dsb+=desa_b; t_kcb+=kec_b; t_kbb+=kab_b; t_du+=dkm_u; t_dsu+=desa_u; t_kcu+=kec_u; t_kbu+=kab_u
                    
                    y_r = pdf.get_y(); nama_tampil = (str(r[1]) + (" - "+str(r[3]) if r[3] else ""))[:30]
                    pdf.cell(8, 10, str(i+1), 1, 0, "C"); pdf.cell(45, 10, nama_tampil, 1, 0, "L")
                    pdf.cell(15, 10, f"{jb}/{ju}", 1, 0, "C"); pdf.cell(18, 10, f"{tot_b:.2f}", 1, 0, "C")
                    pdf.cell(25, 10, f"{int(tot_u):,}", 1, 0, "R"); pdf.cell(22, 10, f"{int(inf):,}", 1, 0, "R")
                    
                    x_curr = pdf.get_x()
                    pdf.multi_cell(36, 5, f"B: {dkm_b:,.2f}\nU: {int(dkm_u):,}", 1, "L"); pdf.set_xy(x_curr + 36, y_r)
                    pdf.multi_cell(36, 5, f"B: {desa_b:,.2f}\nU: {int(desa_u):,}", 1, "L"); pdf.set_xy(x_curr + 72, y_r)
                    pdf.multi_cell(36, 5, f"B: {kec_b:,.2f}\nU: {int(kec_u):,}", 1, "L"); pdf.set_xy(x_curr + 108, y_r)
                    pdf.multi_cell(36, 5, f"B: {kab_b:,.2f}\nU: {int(kab_u):,}", 1, "L"); pdf.set_xy(10, y_r + 10)

                pdf.set_font("Arial", "B", 8); y_r = pdf.get_y()
                pdf.cell(53, 10, "TOTAL KESELURUHAN", 1, 0, "C"); pdf.cell(15, 10, f"{t_jb}/{t_ju}", 1, 0, "C") 
                pdf.cell(18, 10, f"{t_tb:,.2f}", 1, 0, "C"); pdf.cell(25, 10, f"{int(t_tu):,}", 1, 0, "R"); pdf.cell(22, 10, f"{int(t_inf):,}", 1, 0, "R")
                
                x_curr = pdf.get_x()
                pdf.multi_cell(36, 5, f"B: {t_db:,.2f}\nU: {int(t_du):,}", 1, "L"); pdf.set_xy(x_curr + 36, y_r)
                pdf.multi_cell(36, 5, f"B: {t_dsb:,.2f}\nU: {int(t_dsu):,}", 1, "L"); pdf.set_xy(x_curr + 72, y_r)
                pdf.multi_cell(36, 5, f"B: {t_kcb:,.2f}\nU: {int(t_kcu):,}", 1, "L"); pdf.set_xy(x_curr + 108, y_r)
                pdf.multi_cell(36, 5, f"B: {t_kbb:,.2f}\nU: {int(t_kbu):,}", 1, "L"); pdf.set_xy(10, y_r + 10)
                
                pdf.ln(5); pdf.set_font("Arial", "I", 8)
                pdf.multi_cell(0, 4, "* Keterangan Tabel:\n- Kolom 'Fisik' adalah wajib setor berupa fisik beras/uang tunai sebesar 17.5% dari Total Penghimpunan (Gabungan Hak Desa 6.5%, Kec 5%, dan Kab 6%).\n- Kolom 'Total 100%' adalah jumlah keseluruhan penghimpunan sebelum dibagi persentasenya.\n- Infaq Ramadhan dialokasikan sepenuhnya untuk Insentif Guru Ngaji/Diniyah di wilayah masing-masing.")
                
                pdf.ln(5); pdf.set_font("Arial", "", 10)
                pdf.cell(100, 5, "", border=0); pdf.cell(77, 5, "", border=0); pdf.cell(100, 5, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=True)
                pdf.cell(100, 5, "Mengetahui,", border=0, align="C"); pdf.cell(77, 5, "", border=0); pdf.cell(100, 5, "Panitia Pengumpul", border=0, align="C", ln=True)
                pdf.cell(100, 5, "Kepala Desa,", border=0, align="C"); pdf.cell(77, 5, "Ketua UPZ Desa,", border=0, align="C"); pdf.cell(100, 5, "Sekretaris UPZ Desa,", border=0, align="C", ln=True)
                
                pdf.ln(15); pdf.set_font("Arial", "B", 10)
                pdf.cell(100, 5, f"( {kades} )", border=0, align="C"); pdf.cell(77, 5, f"( {ketua} )", border=0, align="C")
                nama_sek = sekretaris if sekretaris and sekretaris.strip() != "" else "........................................"
                pdf.cell(100, 5, f"( {nama_sek} )", border=0, align="C", ln=True)

                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.success("✨ Dokumen D2 berhasil disiapkan!")
                st.download_button(label="📥 UNDUH PDF D2 SEKARANG", data=pdf_bytes, file_name=f"Format_D2_Penerimaan_{desa}.pdf", mime="application/pdf", use_container_width=True)

        # ------------------------------------------
        # TOMBOL 4: FORMAT D4 & D5 (Distribusi Sabilillah & Rekap Desa)
        # ------------------------------------------
        with st.expander("📄 Format D4 & D5 (Sabilillah & Rekap Desa)"):
            st.write("Daftar mustahik Sabilillah (D4) dan Rekapitulasi Alokasi Desa (D5).")
            
            if st.button("Siapkan Dokumen D4 & D5", use_container_width=True):
                c.execute("SELECT nama_desa, kepala_desa, nama_kecamatan, kabupaten, ketua_upz, sekretaris, logo_path, no_hp, total_jiwa, total_kk FROM pengaturan WHERE id=1")
                p_data = c.fetchone()
                desa, kades, kec, kab, ketua, sekretaris, logo_path, no_hp, total_jiwa, total_kk = p_data
                
                c.execute("SELECT * FROM sabilillah"); sab_rows = c.fetchall()
                c.execute("SELECT * FROM distribusi_ngaji ORDER BY nama ASC"); dist_ngaji_rows = c.fetchall()
                c.execute("SELECT * FROM setoran_dkm"); dkm_rows_detail = c.fetchall()
                
                pdf = FPDF(orientation="P", unit="mm", format="A4")
                pdf.set_margins(10, 10, 10); pdf.set_auto_page_break(auto=True, margin=15)
                
                # --- HALAMAN D4 ---
                pdf.add_page(); pdf.set_font("Arial", "", 10); pdf.set_xy(165, 10); pdf.cell(30, 6, "Model : D4", border=1, align="C")
                cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                
                pdf.set_font("Arial", "B", 11); pdf.cell(0, 6, "DAFTAR PENYALURAN ZAKAT FITRAH UNTUK SABILILLAH", ln=True, align="C")
                pdf.cell(0, 6, f"BULAN RAMADHAN TAHUN 1446 H / {datetime.datetime.now().year} M", ln=True, align="C"); pdf.ln(4)
                
                pdf.set_font("Arial", "B", 9)
                pdf.cell(25, 5, "Desa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(65, 5, f"{desa}", border=0)
                pdf.cell(30, 5, "Jumlah KK", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_kk} KK", border=0, ln=True)
                pdf.cell(25, 5, "Kecamatan", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(65, 5, f"{kec}", border=0)
                pdf.cell(30, 5, "Jumlah Jiwa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_jiwa} Jiwa", border=0, ln=True)
                pdf.cell(95, 5, "", border=0); pdf.cell(30, 5, "No. HP Pengumpul", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{no_hp}", border=0, ln=True)
                pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2); pdf.ln(5)
                
                pdf.set_font("Arial", "B", 10); pdf.cell(0, 5, "Berita Acara", ln=True, align="C"); pdf.cell(0, 5, "Penyaluran Zakat Fitrah Hak Asnaf Sabilillah", ln=True, align="C"); pdf.ln(3)
                pdf.set_font("Arial", "", 9); pdf.multi_cell(0, 5, f"Pada hari ini, {hari_ba} Tanggal {tgl_ba} telah dilaksanakan penyaluran Zakat Fitrah Hak Asnaf Sabilillah bertempat sebagaimana alamat tersebut di atas dengan daftar penerima sebagai berikut:"); pdf.ln(3)
                
                def draw_header_d4(pdf):
                    y_h = pdf.get_y(); pdf.set_font("Arial", "B", 9)
                    pdf.cell(10, 12, "No.", 1, 0, "C")
                    x1 = pdf.get_x(); pdf.cell(60, 6, "Nama Pimpinan/Lembaga", "LRT", 2, "C"); pdf.cell(60, 6, "Penerima (Mustahik)", "LRB", 0, "C"); pdf.set_xy(x1+60, y_h)
                    pdf.cell(45, 12, "Program", 1, 0, "C")
                    x2 = pdf.get_x(); pdf.cell(40, 6, "Jumlah Pembagian", 1, 2, "C")
                    pdf.cell(20, 6, "Beras (Kg)", 1, 0, "C"); pdf.cell(20, 6, "Uang (Rp)", 1, 0, "C"); pdf.set_xy(x2+40, y_h)
                    pdf.cell(35, 12, "Tanda Tangan", 1, 1, "C")

                draw_header_d4(pdf); pdf.set_font("Arial", "", 9)
                tot_b_sab = 0; tot_u_sab = 0
                for i, r in enumerate(sab_rows):
                    if pdf.get_y() > 240:
                        pdf.add_page(); draw_header_d4(pdf); pdf.set_font("Arial", "", 9)
                        
                    y_r = pdf.get_y(); pdf.rect(20, y_r, 60, 10); pdf.cell(10, 10, str(i+1), 1, 0, "C")
                    pdf.set_xy(20, y_r); pdf.cell(60, 5, str(r[2])[:35], 0, 2, "C"); pdf.cell(60, 5, str(r[1])[:35], 0, 0, "C")
                    pdf.set_xy(80, y_r); pdf.cell(45, 10, str(r[1])[:25], 1, 0, "C")
                    pdf.cell(20, 10, f"{r[3]:.2f}", 1, 0, "C"); pdf.cell(20, 10, f"{int(r[4]):,}", 1, 0, "R")
                    pdf.cell(35, 10, f"{i+1}.............", 1, 1, "L")
                    tot_b_sab += r[3]; tot_u_sab += r[4]
                    
                pdf.set_font("Arial", "B", 9)
                pdf.cell(115, 6, "JUMLAH ................................ :", 1, 0, "R")
                pdf.cell(20, 6, f"{tot_b_sab:.2f}", 1, 0, "C"); pdf.cell(20, 6, f"{int(tot_u_sab):,}", 1, 0, "R"); pdf.cell(35, 6, "", 1, 1, "C"); pdf.ln(5)
                
                pdf.set_font("Arial", "", 9); pdf.multi_cell(0, 5, "Demikian berita acara ini kami buat dengan sebenarnya dengan penuh tanggung jawab, agar yang berkepentingan memakluminya."); pdf.ln(5)
                
                pdf.cell(120, 5, "", border=0); pdf.cell(70, 5, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=True)
                pdf.cell(190, 5, "Panitia Pengumpul", border=0, align="C", ln=True)
                pdf.cell(95, 5, "Ketua UPZ Desa", border=0, align="C"); pdf.cell(95, 5, "Sekretaris UPZ Desa", border=0, align="C", ln=True)
                pdf.ln(15); pdf.set_font("Arial", "B", 10)
                pdf.cell(95, 5, f"( {ketua} )", border=0, align="C")
                nama_sek = sekretaris if sekretaris and sekretaris.strip() != "" else "........................................"
                pdf.cell(95, 5, f"( {nama_sek} )", border=0, align="C", ln=True)
                pdf.ln(5); pdf.set_font("Arial", "B", 8); pdf.cell(0, 4, "Keterangan :", ln=True)
                pdf.set_font("Arial", "", 8); pdf.cell(0, 4, "Dibuat rangkap 3:", ln=True); pdf.cell(0, 4, "- Satu untuk UPZ Desa/Kelurahan", ln=True); pdf.cell(0, 4, "- Satu untuk UPZ Kecamatan", ln=True); pdf.cell(0, 4, "- Satu untuk BAZNAS", ln=True)

                # --- HALAMAN D5 ---
                pdf.add_page(); pdf.set_font("Arial", "", 10); pdf.set_xy(165, 10); pdf.cell(30, 6, "Model : D5", border=1, align="C")
                cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                
                pdf.set_font("Arial", "B", 11); pdf.cell(0, 6, "REKAPITULASI PENDISTRIBUSIAN ZAKAT FITRAH ALOKASI UPZ DESA", ln=True, align="C")
                pdf.cell(0, 6, f"BULAN RAMADHAN TAHUN 1446 H / {datetime.datetime.now().year} M", ln=True, align="C")
                
                pdf.set_line_width(0.8); pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
                pdf.set_line_width(0.2); pdf.line(10, pdf.get_y() + 3, 200, pdf.get_y() + 3); pdf.ln(6)
                
                pdf.set_font("Arial", "B", 9)
                pdf.cell(35, 5, "Desa / Kelurahan", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(55, 5, f"{desa}", border=0)
                pdf.cell(30, 5, "Jumlah KK", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_kk} KK", border=0, ln=True)
                pdf.cell(35, 5, "Kecamatan", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(55, 5, f"{kec}", border=0)
                pdf.cell(30, 5, "Jumlah Jiwa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_jiwa} Jiwa", border=0, ln=True)
                pdf.cell(95, 5, "", border=0); pdf.cell(30, 5, "No. HP Pengumpul", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{no_hp}", border=0, ln=True)
                pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2); pdf.ln(5)

                pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, "1. Zakat Fitrah", ln=True)

                tot_b_global = sum((r[10] or 0) for r in dkm_rows_detail)
                tot_u_global = sum((r[11] or 0) for r in dkm_rows_detail)

                desa_b = tot_b_global * 0.065; desa_u = tot_u_global * 0.065
                salur_b = desa_b * 0.875; salur_u = desa_u * 0.875
                amil_b = desa_b * 0.125; amil_u = desa_u * 0.125

                pdf.set_font("Arial", "B", 9)
                pdf.cell(30, 8, "Penyaluran", 1, 0, 'C'); pdf.cell(50, 8, "Asnaf", 1, 0, 'C')
                pdf.cell(25, 8, "Jenis", 1, 0, 'C'); pdf.cell(40, 8, "Jumlah", 1, 0, 'C'); pdf.cell(45, 8, "Keterangan", 1, 1, 'C')

                pdf.set_font("Arial", "", 9)
                def draw_d5_row(pdf, label_peny, label_asnaf, val_b, val_u):
                    y_r = pdf.get_y()
                    pdf.rect(10, y_r, 30, 12); pdf.rect(40, y_r, 50, 12)
                    pdf.rect(90, y_r, 25, 6); pdf.rect(115, y_r, 40, 6); pdf.rect(155, y_r, 45, 12)
                    pdf.rect(90, y_r+6, 25, 6); pdf.rect(115, y_r+6, 40, 6)
                    pdf.set_xy(10, y_r); pdf.cell(30, 12, label_peny, 0, 0, "L"); pdf.cell(50, 12, label_asnaf, 0, 0, "C")
                    pdf.set_xy(90, y_r); pdf.cell(25, 6, "Beras", 0, 0, "C"); pdf.cell(40, 6, f"{val_b:,.2f} Kg", 0, 0, "C")
                    pdf.set_xy(155, y_r); pdf.cell(45, 12, "Tersalurkan", 0, 0, "C")
                    pdf.set_xy(90, y_r+6); pdf.cell(25, 6, "Uang", 0, 0, "C"); pdf.cell(40, 6, f"Rp {int(val_u):,}", 0, 1, "C")

                draw_d5_row(pdf, " a. Desa", "Hak Amil Desa (6.5%)", desa_b, desa_u)
                draw_d5_row(pdf, " b. Dana Salur", "Asnaf Sabilillah (87.5%)", salur_b, salur_u)
                draw_d5_row(pdf, " c. Hak Amil", "Asnaf Amilin (12.5%)", amil_b, amil_u)
                pdf.ln(5)

                pdf.set_font("Arial", "B", 9); y_start = pdf.get_y()
                pdf.cell(10, 10, "NO", border=1, align="C"); pdf.cell(60, 10, "ASNAF", border=1, align="C")
                x1 = pdf.get_x(); pdf.cell(40, 5, "JUMLAH BERAS", "LRT", 2, 'C'); pdf.cell(40, 5, "(KG)", "LRB", 0, 'C'); pdf.set_xy(x1+40, y_start)
                x2 = pdf.get_x(); pdf.cell(40, 5, "JUMLAH UANG", "LRT", 2, 'C'); pdf.cell(40, 5, "(RP)", "LRB", 0, 'C'); pdf.set_xy(x2+40, y_start)
                pdf.cell(40, 10, "KETERANGAN", border=1, align="C", ln=True)

                sab_dict = {}
                for r in sab_rows:
                    prog = r[1]
                    if prog not in sab_dict: sab_dict[prog] = {'b': 0.0, 'u': 0.0}
                    sab_dict[prog]['b'] += r[3]; sab_dict[prog]['u'] += r[4]
                
                pdf.set_font("Arial", "", 9)
                no = 1; sum_b = 0; sum_u = 0
                for prog, vals in sab_dict.items():
                    pdf.cell(10, 6, str(no), border=1, align="C"); pdf.cell(60, 6, f" {prog}"[:35], border=1)
                    pdf.cell(40, 6, f"{vals['b']:,.2f}", border=1, align="C"); pdf.cell(40, 6, f"{int(vals['u']):,}", border=1, align="C")
                    pdf.cell(40, 6, "Tersalurkan", border=1, align="C")
                    sum_b += vals['b']; sum_u += vals['u']; no += 1; pdf.ln()
                
                tot_ngaji_u = sum(r[6] or 0 for r in dist_ngaji_rows)
                if tot_ngaji_u > 0:
                    pdf.cell(10, 6, str(no), border=1, align="C"); pdf.cell(60, 6, " Insentif Guru Ngaji", border=1)
                    pdf.cell(40, 6, "0.00", border=1, align="C"); pdf.cell(40, 6, f"{int(tot_ngaji_u):,}", border=1, align="C")
                    pdf.cell(40, 6, "Tersalurkan", border=1, align="C")
                    sum_u += tot_ngaji_u; pdf.ln()

                pdf.set_font("Arial", "B", 9)
                pdf.cell(70, 6, "TOTAL", border=1, align="C"); pdf.cell(40, 6, f"{sum_b:,.2f}", border=1, align="C")
                pdf.cell(40, 6, f"{int(sum_u):,}", border=1, align="C"); pdf.cell(40, 6, "", border=1, align="C"); pdf.ln(10)

                pdf.set_font("Arial", "", 10)
                pdf.cell(120, 5, "", border=0); pdf.cell(70, 5, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=True)
                pdf.cell(190, 5, "Panitia Pengumpul", border=0, align="C", ln=True)
                pdf.cell(95, 5, "Ketua UPZ Desa", border=0, align="C"); pdf.cell(95, 5, "Sekretaris UPZ Desa", border=0, align="C", ln=True)
                pdf.ln(15); pdf.set_font("Arial", "B", 10)
                pdf.cell(95, 5, f"( {ketua} )", border=0, align="C"); pdf.cell(95, 5, f"( {nama_sek} )", border=0, align="C", ln=True)

                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.success("✨ Dokumen D4 & D5 berhasil disiapkan!")
                st.download_button(label="📥 UNDUH PDF D4 & D5 SEKARANG", data=pdf_bytes, file_name=f"Format_D4_D5_{desa}.pdf", mime="application/pdf", use_container_width=True)

        # ------------------------------------------
        # TOMBOL 5: FORMAT D6 (Asnaf Amilin)
        # ------------------------------------------
        with st.expander("📄 Format D6 (Asnaf Amilin)"):
            st.write("Daftar penyaluran hak amil untuk para pengurus UPZ Desa.")
            
            if st.button("Siapkan Dokumen D6", use_container_width=True):
                c.execute("SELECT nama_desa, kepala_desa, nama_kecamatan, kabupaten, ketua_upz, sekretaris, logo_path, no_hp, total_jiwa, total_kk FROM pengaturan WHERE id=1")
                p_data = c.fetchone()
                desa, kades, kec, kab, ketua, sekretaris, logo_path, no_hp, total_jiwa, total_kk = p_data
                
                c.execute("SELECT * FROM amilin"); amil_rows = c.fetchall()
                
                pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
                pdf.set_font("Arial", "", 10); pdf.set_xy(165, 10); pdf.cell(30, 6, "Model : D6", border=1, align="C")
                cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, "DAFTAR PENYALURAN ZAKAT FITRAH UNTUK AMILIN TINGKAT DESA", ln=True, align="C")
                pdf.cell(0, 6, f"BULAN RAMADHAN TAHUN 1446 H / {datetime.datetime.now().year} M", ln=True, align="C"); pdf.ln(4)
                
                pdf.set_font("Arial", "B", 9)
                pdf.cell(25, 5, "Desa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(65, 5, f"{desa}", border=0)
                pdf.cell(30, 5, "Jumlah KK", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_kk} KK", border=0, ln=True)
                pdf.cell(25, 5, "Kecamatan", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(65, 5, f"{kec}", border=0)
                pdf.cell(30, 5, "Jumlah Jiwa", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{total_jiwa} Jiwa", border=0, ln=True)
                pdf.cell(95, 5, "", border=0); pdf.cell(30, 5, "No. HP Pengumpul", border=0); pdf.cell(5, 5, ":", border=0); pdf.cell(0, 5, f"{no_hp}", border=0, ln=True)
                pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2); pdf.ln(5)
                
                def draw_header_d6(pdf):
                    y_h = pdf.get_y(); pdf.set_font("Arial", "B", 9)
                    pdf.cell(10, 12, "No.", 1, 0, "C")
                    x1 = pdf.get_x(); pdf.cell(50, 6, "Nama Pengurus", "LRT", 2, "C"); pdf.cell(50, 6, "Penerima (Amil)", "LRB", 0, "C"); pdf.set_xy(x1+50, y_h)
                    pdf.cell(45, 12, "Posisi Jabatan", 1, 0, "C")
                    x2 = pdf.get_x(); pdf.cell(50, 6, "Jumlah Pembagian", 1, 2, "C")
                    pdf.cell(20, 6, "Beras (Kg)", 1, 0, "C"); pdf.cell(30, 6, "Uang (Rp)", 1, 0, "C"); pdf.set_xy(x2+50, y_h)
                    pdf.cell(35, 12, "Tanda Tangan", 1, 1, "C")

                draw_header_d6(pdf); pdf.set_font("Arial", "", 9)
                tot_b = 0; tot_u = 0
                for i, r in enumerate(amil_rows):
                    if pdf.get_y() > 240:
                        pdf.add_page(); draw_header_d6(pdf); pdf.set_font("Arial", "", 9)
                    
                    y_r = pdf.get_y(); pdf.rect(20, y_r, 50, 10); pdf.cell(10, 10, str(i+1), 1, 0, "C")
                    pdf.set_xy(20, y_r); pdf.cell(50, 5, str(r[1])[:25], 0, 2, "C"); pdf.cell(50, 5, "Amilin Desa", 0, 0, "C")
                    pdf.set_xy(70, y_r); pdf.cell(45, 10, str(r[2])[:20], 1, 0, "C")
                    pdf.cell(20, 10, f"{r[3]:.2f}", 1, 0, "C"); pdf.cell(30, 10, f"{int(r[4]):,}", 1, 0, "R")
                    pdf.cell(35, 10, f"{i+1}.............", 1, 1, "L")
                    tot_b += r[3]; tot_u += r[4]
                    
                pdf.set_font("Arial", "B", 9)
                pdf.cell(105, 6, "JUMLAH ................................ :", 1, 0, "R")
                pdf.cell(20, 6, f"{tot_b:.2f}", 1, 0, "C"); pdf.cell(30, 6, f"{int(tot_u):,}", 1, 0, "R")
                pdf.cell(35, 6, "", 1, 1, "C"); pdf.ln(10)
                
                pdf.set_font("Arial", "", 10)
                pdf.cell(120, 5, "", border=0); pdf.cell(70, 5, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=True)
                pdf.cell(190, 5, "Panitia Pengumpul", border=0, align="C", ln=True)
                pdf.cell(95, 5, "Ketua UPZ Desa", border=0, align="C"); pdf.cell(95, 5, "Sekretaris UPZ Desa", border=0, align="C", ln=True)
                pdf.ln(15); pdf.set_font("Arial", "B", 10)
                pdf.cell(95, 5, f"( {ketua} )", border=0, align="C")
                nama_sek = sekretaris if sekretaris and sekretaris.strip() != "" else "........................................"
                pdf.cell(95, 5, f"( {nama_sek} )", border=0, align="C", ln=True)
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.success("✨ Dokumen D6 berhasil disiapkan!")
                st.download_button(label="📥 UNDUH PDF D6 SEKARANG", data=pdf_bytes, file_name=f"Format_D6_Amilin_{desa}.pdf", mime="application/pdf", use_container_width=True)
# ------------------------------------------
        # TOMBOL 6: FORMAT D1 (Surat Pengantar & BAST Kecamatan)
        # ------------------------------------------
        with st.expander("📜 Surat Pengantar & BAST ke Kecamatan (D1)"):
            st.write("Surat pengantar dokumen dan Berita Acara Serah Terima (BAST) 11% ke Kecamatan/BAZNAS Kabupaten.")
            
            if st.button("Siapkan Dokumen D1", use_container_width=True):
                c.execute("SELECT nama_desa, kepala_desa, nama_kecamatan, kabupaten, ketua_upz, logo_path FROM pengaturan WHERE id=1")
                p_data = c.fetchone()
                desa, kades, kec, kab, ketua, logo_path = p_data[0], p_data[1], p_data[2], p_data[3], p_data[4], p_data[5]
                
                c.execute("SELECT total_beras, total_uang FROM setoran_dkm")
                dkm_rows = c.fetchall()
                t_tb = sum(r[0] or 0 for r in dkm_rows)
                t_tu = sum(r[1] or 0 for r in dkm_rows)

                pdf = FPDF(orientation="P", unit="mm", format="A4")
                pdf.set_auto_page_break(auto=True, margin=15)
                
                # HALAMAN 1: SURAT PENGANTAR
                pdf.add_page(); cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                
                pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "PANITIA AMIL ZAKAT FITRAH TINGKAT DESA", ln=True, align="C")
                pdf.cell(0, 8, f"DESA {desa.upper()} KECAMATAN {kec.upper()}", ln=True, align="C"); pdf.ln(10)
                pdf.set_font("Arial", "", 12); pdf.cell(30, 8, "Nomor", border=0); pdf.cell(90, 8, f": {no_ba}", border=0); pdf.cell(0, 8, "Kepada Yth.", border=0, ln=True)
                pdf.cell(30, 8, "Lampiran", border=0); pdf.cell(90, 8, ": 1 (Satu) berkas dokumen", border=0); pdf.cell(0, 8, "Ketua UPZ Kecamatan", border=0, ln=True)
                pdf.cell(30, 8, "Perihal", border=0); pdf.cell(90, 8, ": Laporan Zakat Fitrah", border=0); pdf.cell(0, 8, "di- Tempat", border=0, ln=True); pdf.ln(10)
                pdf.cell(0, 8, "Assalamualaikum Wr. Wb.", ln=True); pdf.multi_cell(0, 8, f"Bersama surat ini, kami sampaikan berkas laporan administrasi pengumpulan dan penyaluran Zakat Fitrah serta Infaq Ramadhan Tahun {datetime.datetime.now().year} Masehi. Adapun kelengkapan dokumen terlampir adalah sebagai berikut:")
                pdf.ln(5)
                pdf.set_font("Arial", "B", 11); pdf.cell(15, 8, "NO", border=1, align="C"); pdf.cell(140, 8, "DAFTAR DOKUMEN", border=1, align="C"); pdf.cell(35, 8, "KETERANGAN", border=1, align="C", ln=True)
                pdf.set_font("Arial", "", 11); lampiran = ["Daftar Pengumpulan Zakat Fitrah dan Infaq Ramadhan (D2)", "Tabel Rekapitulasi Pembagian Zakat Fitrah (D3)", "Daftar Penyaluran Zakat Fitrah Asnaf Sabilillah (D4)", "Daftar Rekapitulasi Alokasi UPZ Desa (D5)", "Daftar Penyaluran Zakat Fitrah Asnaf Amilin (D6)", "Berita Acara Serah Terima Zakat Fitrah ke Kecamatan"]
                for i, teks in enumerate(lampiran): pdf.cell(15, 8, str(i+1), border=1, align="C"); pdf.cell(140, 8, f" {teks}", border=1); pdf.cell(35, 8, " [  v  ]", border=1, align="C", ln=True)
                pdf.ln(10); pdf.cell(0, 8, "Demikian surat pengantar laporan ini kami sampaikan untuk dapat dipergunakan sebagaimana mestinya.", ln=True); pdf.ln(15)
                pdf.cell(100, 8, "", border=0); pdf.cell(90, 8, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=True); pdf.cell(100, 8, "", border=0); pdf.cell(90, 8, "Ketua UPZ Desa,", border=0, align="C", ln=True); pdf.ln(25)
                pdf.set_font("Arial", "B", 12); pdf.cell(100, 8, "", border=0); pdf.cell(90, 8, f"( {ketua} )", border=0, align="C", ln=True)

                # HALAMAN 2: BAST KECAMATAN
                pdf.add_page(); cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                
                pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "BERITA ACARA SERAH TERIMA ZAKAT FITRAH TINGKAT KECAMATAN", ln=True, align="C"); pdf.ln(10)
                pdf.set_font("Arial", "", 12); pdf.multi_cell(0, 8, f"Pada hari ini, {hari_ba} tanggal {tgl_ba}, telah dilaksanakan penyerahan Zakat Fitrah dari UPZ Desa {desa} kepada UPZ Kecamatan {kec} sebesar 11% (Gabungan Hak Kecamatan 5% dan BAZNAS Kabupaten 6%) dari total penghimpunan Desa dengan rincian data sebagai berikut:")
                pdf.ln(5)
                
                kec_b = t_tb * 0.05; kec_u = t_tu * 0.05; kab_b = t_tb * 0.06; kab_u = t_tu * 0.06
                tot_b_11 = kec_b + kab_b; tot_u_11 = kec_u + kab_u
                
                pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "A. RINCIAN PENYERAHAN (11%)", ln=True)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(60, 8, "Tujuan Penyerahan", border=1, align="C"); pdf.cell(65, 8, "Beras (Kg)", border=1, align="C"); pdf.cell(65, 8, "Uang Tunai (Rp)", border=1, align="C", ln=True)
                pdf.set_font("Arial", "", 11)
                pdf.cell(60, 8, " 1. UPZ Kec. (5%)", border=1); pdf.cell(65, 8, f" {kec_b:.2f} Kg", border=1, align="C"); pdf.cell(65, 8, f" Rp {int(kec_u):,}", border=1, align="C", ln=True)
                pdf.cell(60, 8, " 2. BAZNAS Kab. (6%)", border=1); pdf.cell(65, 8, f" {kab_b:.2f} Kg", border=1, align="C"); pdf.cell(65, 8, f" Rp {int(kab_u):,}", border=1, align="C", ln=True)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(60, 8, " TOTAL DISERAHKAN", border=1); pdf.cell(65, 8, f" {tot_b_11:.2f} Kg", border=1, align="C"); pdf.cell(65, 8, f" Rp {int(tot_u_11):,}", border=1, align="C", ln=True); pdf.ln(10)
                
                pdf.set_font("Arial", "", 12); pdf.multi_cell(0, 8, "Demikian berita acara ini dibuat dengan sebenarnya dan penuh tanggung jawab untuk dapat dijadikan pedoman administrasi."); pdf.ln(20)
                pdf.cell(90, 8, "Pihak Penerima (UPZ Kecamatan),", border=0, align="C"); pdf.cell(100, 8, "Pihak Penyerah (UPZ Desa),", border=0, align="C", ln=True); pdf.ln(25)
                pdf.set_font("Arial", "B", 12); pdf.cell(90, 8, "( ............................................ )", border=0, align="C"); pdf.cell(100, 8, f"( {ketua} )", border=0, align="C", ln=True)

                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.success("✨ Dokumen D1 & BAST berhasil disiapkan!")
                st.download_button(label="📥 UNDUH PDF D1 & BAST SEKARANG", data=pdf_bytes, file_name=f"Format_D1_BAST_{desa}.pdf", mime="application/pdf", use_container_width=True)

        # ------------------------------------------
        # TOMBOL 7: BAST KUPON INFAQ (MULTIPAGE)
        # ------------------------------------------
        with st.expander("🎟️ BAST Kupon Infaq (Seluruh DKM)"):
            st.write("Berita acara serah terima sisa kupon dan uang infaq dari setiap UPZ DKM ke Desa.")
            
            if st.button("Siapkan Dokumen Kupon", use_container_width=True):
                c.execute("SELECT nama_desa, nama_kecamatan, kabupaten, ketua_upz, nominal_kupon, kepala_desa, logo_path FROM pengaturan WHERE id=1")
                p = c.fetchone()
                desa, kec, kab, ketua, nom_kupon, kades, logo_path = p[0], p[1], p[2], p[3], p[4], p[5], p[6]
                
                c.execute('''SELECT s.nama_dkm, s.kupon_diterima, s.kupon_terjual, s.kupon_kembali, s.infaq, m.ketua_dkm, m.alamat_dkm 
                             FROM setoran_dkm s LEFT JOIN master_dkm m ON s.nama_dkm = m.nama_dkm ORDER BY s.nama_dkm ASC''')
                rows = c.fetchall()
                
                if not rows:
                    st.error("Belum ada data penerimaan kupon dari DKM di tabel Penerimaan Zakat!")
                else:
                    pdf = FPDF(orientation="P", unit="mm", format="A4")
                    pdf.set_margins(10, 10, 10); pdf.set_auto_page_break(auto=True, margin=15)
                    
                    tot_diterima = 0; tot_terjual = 0; tot_kembali = 0; tot_uang = 0
                    
                    # LOOP HALAMAN BAST UNTUK TIAP DKM
                    for r in rows:
                        nama_dkm = r[0]; k_diterima = r[1] or 0; k_terjual = r[2] or 0; k_kembali = r[3] or 0; uang_infaq = r[4] or 0
                        ketua_dkm = r[5] if r[5] else "..................................................."
                        alamat_dkm = r[6] if r[6] else "......................................................................................."
                        
                        tot_diterima += k_diterima; tot_terjual += k_terjual; tot_kembali += k_kembali; tot_uang += uang_infaq
                        
                        pdf.add_page(); cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                        
                        pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "BERITA ACARA SERAH TERIMA BARANG", ln=True, align="C")
                        pdf.set_font("Arial", "", 12)
                        pdf.cell(0, 6, no_ba, ln=True, align="C"); pdf.ln(10)
                        
                        pdf.cell(0, 8, "Yang bertanda tangan di bawah ini:", ln=True)
                        pdf.cell(30, 8, "Nama", border=0); pdf.cell(5, 8, ":", border=0); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, f"{ketua.upper()}", border=0, ln=True); pdf.set_font("Arial", "", 12)
                        pdf.cell(30, 8, "Jabatan", border=0); pdf.cell(5, 8, ":", border=0); pdf.cell(0, 8, f"KETUA UPZ DESA {desa.upper()}", border=0, ln=True)
                        pdf.cell(0, 8, "selanjutnya disebut  Pihak Pertama (Pihak I)", ln=True); pdf.ln(5)
                        
                        pdf.cell(30, 8, "Nama Amil", border=0); pdf.cell(5, 8, ":", border=0); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, f"{ketua_dkm.upper()}", border=0, ln=True); pdf.set_font("Arial", "", 12)
                        pdf.cell(30, 8, "Jabatan", border=0); pdf.cell(5, 8, ":", border=0); pdf.cell(0, 8, f"KETUA UPZ DKM {nama_dkm.upper()}", border=0, ln=True)
                        pdf.cell(30, 8, "Alamat", border=0); pdf.cell(5, 8, ":", border=0); pdf.cell(0, 8, f"{alamat_dkm}", border=0, ln=True)
                        pdf.cell(0, 8, "Yang selanjutnya disebut  Pihak Kedua (Pihak II)", ln=True); pdf.ln(8)
                        
                        teks_isi = f"Bahwa pada hari ini {hari_ba} tanggal {tgl_ba} PIHAK PERTAMA telah menyerahkan Kupon Infaq Ramadhan kepada PIHAK KEDUA dengan jumlah awal {k_diterima} lembar, telah laku terjual sejumlah {k_terjual} lembar, dengan sisa pengembalian berjumlah {k_kembali} lembar. Hasil penjualan yang disetorkan ke UPZ Desa adalah senilai Rp {int(uang_infaq):,}."
                        pdf.multi_cell(0, 8, teks_isi); pdf.ln(5)
                        pdf.multi_cell(0, 8, "Demikian berita acara ini dibuat tanpa ada paksaan dikedua pihak dan dapat digunakan sebagaimana mestinya."); pdf.ln(15)
                        
                        pdf.cell(90, 6, "", border=0, align="C"); pdf.cell(100, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=True)
                        pdf.cell(90, 6, "Pihak Kedua,", border=0, align="C"); pdf.cell(100, 6, "Pihak Pertama,", border=0, align="C", ln=True); pdf.ln(25)
                        pdf.set_font("Arial", "B", 12); pdf.cell(90, 6, f"( {ketua_dkm.upper()} )", border=0, align="C"); pdf.cell(100, 6, f"( {ketua.upper()} )", border=0, align="C", ln=True)
                        
                    # HALAMAN TERAKHIR: REKAPITULASI KUPON
                    pdf.add_page()
                    cetak_kop_surat_resmi_web(pdf, desa, kec, kab, logo_path)
                    
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 8, "REKAPITULASI KUPON INFAQ RAMADHAN TINGKAT DESA", ln=True, align="C")
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 6, f"TAHUN {datetime.datetime.now().year} M", ln=True, align="C")
                    pdf.ln(10)
                    
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(10, 10, "No", 1, 0, "C")
                    pdf.cell(50, 10, "Nama UPZ DKM", 1, 0, "C")
                    pdf.cell(30, 10, "Awal Diterima", 1, 0, "C")
                    pdf.cell(30, 10, "Terjual (Laku)", 1, 0, "C")
                    pdf.cell(30, 10, "Sisa (Kembali)", 1, 0, "C")
                    pdf.cell(40, 10, "Nominal Uang", 1, 1, "C")
                    
                    pdf.set_font("Arial", "", 10)
                    for i, r in enumerate(rows):
                        pdf.cell(10, 8, str(i+1), 1, 0, "C")
                        pdf.cell(50, 8, str(r[0])[:25], 1, 0, "L")
                        pdf.cell(30, 8, f"{r[1] or 0} Lbr", 1, 0, "C")
                        pdf.cell(30, 8, f"{r[2] or 0} Lbr", 1, 0, "C")
                        pdf.cell(30, 8, f"{r[3] or 0} Lbr", 1, 0, "C")
                        pdf.cell(40, 8, f"Rp {int(r[4] or 0):,}", 1, 1, "R")
                        
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(60, 8, "TOTAL KESELURUHAN", 1, 0, "C")
                    pdf.cell(30, 8, f"{tot_diterima} Lbr", 1, 0, "C")
                    pdf.cell(30, 8, f"{tot_terjual} Lbr", 1, 0, "C")
                    pdf.cell(30, 8, f"{tot_kembali} Lbr", 1, 0, "C")
                    pdf.cell(40, 8, f"Rp {int(tot_uang):,}", 1, 1, "R")
                    
                    pdf.ln(15)
                    pdf.set_font("Arial", "", 11)
                    pdf.cell(90, 6, "", border=0, align="C")
                    pdf.cell(100, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=True)
                    pdf.cell(90, 6, "Mengetahui, Kepala Desa", border=0, align="C")
                    pdf.cell(100, 6, "Ketua UPZ Desa,", border=0, align="C", ln=True)
                    pdf.ln(25)
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(90, 6, f"( {kades} )", border=0, align="C")
                    pdf.cell(100, 6, f"( {ketua} )", border=0, align="C", ln=True)

                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    st.success("✨ Dokumen BAST Kupon Infaq berhasil disiapkan!")
                    st.download_button(label="📥 UNDUH PDF BAST KUPON SEKARANG", data=pdf_bytes, file_name=f"BAST_Kupon_Infaq_{desa}.pdf", mime="application/pdf", use_container_width=True)                    

    conn.close()
# ==========================================
# HALAMAN PENGATURAN PROFIL DESA
# ==========================================
elif pilihan_menu == "⚙️ Pengaturan":
    st.title("⚙️ Pengaturan Profil Desa")
    st.write("Silakan perbarui profil dan konfigurasi UPZ Desa di sini.")

    # Sambungkan ke Database
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Tambah kolom jika belum ada (opsional, menjaga agar tidak error)
    try:
        c.execute("ALTER TABLE pengaturan ADD COLUMN no_hp TEXT")
        c.execute("ALTER TABLE pengaturan ADD COLUMN total_jiwa INTEGER")
        c.execute("ALTER TABLE pengaturan ADD COLUMN total_kk INTEGER")
    except:
        pass

    # Ambil data saat ini dari database
    c.execute("SELECT * FROM pengaturan WHERE id=1")
    data = c.fetchone()
    
    if data:
        # Menampung nilai ke variabel agar form bisa diisi data lama
        desa = data[1] if data[1] else ""
        kades = data[2] if data[2] else ""
        kec = data[3] if data[3] else ""
        kab = data[4] if data[4] else ""
        ketua = data[5] if data[5] else ""
        sek = data[6] if data[6] else ""
        ben = data[7] if data[7] else ""
        tarif = int(data[9]) if data[9] else 0
        h_beras = int(data[10]) if data[10] else 0
        j_beras = data[11] if data[11] else 0.0
        
        # Ambil data tambahan
        try:
            c.execute("SELECT nominal_kupon, logo_path, no_hp, total_jiwa, total_kk FROM pengaturan WHERE id=1")
            res_tambahan = c.fetchone()
            nom_kupon = int(res_tambahan[0]) if res_tambahan and res_tambahan[0] else 0
            logo_path = res_tambahan[1] if res_tambahan and res_tambahan[1] else ""
            no_hp = res_tambahan[2] if res_tambahan and res_tambahan[2] else ""
            total_jiwa = int(res_tambahan[3]) if res_tambahan and res_tambahan[3] else 0
            total_kk = int(res_tambahan[4]) if res_tambahan and res_tambahan[4] else 0
        except:
            nom_kupon = 0; logo_path = ""; no_hp = ""; total_jiwa = 0; total_kk = 0

        # ==========================================
        # FORM PENGATURAN UTAMA
        # ==========================================
        with st.form("form_pengaturan"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Data Desa")
                in_desa = st.text_input("Nama Desa:", value=desa)
                in_kades = st.text_input("Kepala Desa:", value=kades)
                in_kec = st.text_input("Kecamatan:", value=kec)
                in_kab = st.text_input("Kabupaten:", value=kab)
                in_jiwa = st.number_input("Total Penduduk (Jiwa):", value=total_jiwa, min_value=0)
                in_kk = st.number_input("Total Kepala Keluarga (KK):", value=total_kk, min_value=0)
                
            with col2:
                st.subheader("Data Pengurus UPZ")
                in_ketua = st.text_input("Ketua UPZ:", value=ketua)
                in_hp = st.text_input("No. HP / WhatsApp:", value=no_hp)
                in_sek = st.text_input("Sekretaris:", value=sek)
                in_ben = st.text_input("Bendahara:", value=ben)
            
            st.markdown("---")
            st.subheader("Konfigurasi Tarif & Lainnya")
            col3, col4 = st.columns(2)
            with col3:
                in_tarif = st.number_input("Tarif Zakat Uang (Rp):", value=tarif, min_value=0)
                in_h_beras = st.number_input("Harga Jual Beras (Rp):", value=h_beras, min_value=0)
            with col4:
                in_j_beras = st.number_input("Beras Dijual (Kg):", value=float(j_beras), min_value=0.0)
                in_nom_kupon = st.number_input("Nominal Kupon Infaq (Rp):", value=nom_kupon, min_value=0)
                in_logo = st.text_input("Nama File Logo (Kop Surat):", value=logo_path)

            # Tombol Submit Form
            submitted = st.form_submit_button("💾 Simpan Pengaturan", use_container_width=True)
            
            if submitted:
                # Update data ke database
                c.execute('''UPDATE pengaturan SET 
                             nama_desa=?, kepala_desa=?, nama_kecamatan=?, kabupaten=?, 
                             ketua_upz=?, sekretaris=?, bendahara=?, tarif_uang=?, 
                             harga_jual_beras=?, beras_dijual=?, nominal_kupon=?, 
                             logo_path=?, no_hp=?, total_jiwa=?, total_kk=? 
                             WHERE id=1''',
                          (in_desa, in_kades, in_kec, in_kab, 
                           in_ketua, in_sek, in_ben, float(in_tarif), 
                           float(in_h_beras), in_j_beras, float(in_nom_kupon), 
                           in_logo, in_hp, in_jiwa, in_kk))
                conn.commit()
                st.success("Data pengaturan berhasil diperbarui!")
                st.rerun() # Refresh halaman agar data baru langsung tampil

        # ==========================================
        # ZONA BERBAHAYA (ARSIP DATA)
        # ==========================================
        st.markdown("---")
        with st.expander("📦 Arsipkan & Bersihkan Tahun Ini (Zona Berbahaya)"):
            st.warning("PENTING: Seluruh Data Zakat & Penyaluran tahun ini akan dipindahkan ke ARSIP dan tabel aktif akan dikosongkan.")
            
            # Gunakan form terpisah untuk proses arsip agar tidak bentrok
            with st.form("form_arsip"):
                tahun_arsip = st.text_input("Ketik Tahun untuk diarsipkan (Contoh: 2026):")
                submit_arsip = st.form_submit_button("Arsipkan Sekarang")
                
                if submit_arsip:
                    if tahun_arsip:
                        try:
                            # Memindahkan data ke arsip
                            c.execute("INSERT INTO arsip_setoran_dkm (tahun_arsip, nama_dkm, alamat_dkm, perwakilan, alamat_perwakilan, tipe_input, jiwa_beras, jiwa_uang, fisik_beras, fisik_uang, total_beras, total_uang, infaq, kupon_diterima, kupon_terjual, kupon_kembali) SELECT ?, nama_dkm, alamat_dkm, perwakilan, alamat_perwakilan, tipe_input, jiwa_beras, jiwa_uang, fisik_beras, fisik_uang, total_beras, total_uang, infaq, kupon_diterima, kupon_terjual, kupon_kembali FROM setoran_dkm", (tahun_arsip,))
                            c.execute("INSERT INTO arsip_sabilillah (tahun_arsip, program, penerima, beras, uang) SELECT ?, program, penerima, beras, uang FROM sabilillah", (tahun_arsip,))
                            c.execute("INSERT INTO arsip_amilin (tahun_arsip, nama, jabatan, beras, uang) SELECT ?, nama, jabatan, beras, uang FROM amilin", (tahun_arsip,))
                            c.execute("INSERT INTO arsip_distribusi_ngaji (tahun_arsip, nama, lembaga, dkm, alamat, bobot, uang) SELECT ?, nama, lembaga, dkm, alamat, bobot, uang FROM distribusi_ngaji", (tahun_arsip,))

                            # Membersihkan tabel aktif
                            c.execute("DELETE FROM setoran_dkm")
                            c.execute("DELETE FROM sabilillah")
                            c.execute("DELETE FROM amilin")
                            c.execute("DELETE FROM distribusi_ngaji")
                            
                            conn.commit()
                            st.success(f"Berhasil! Semua data telah diarsipkan pada tahun {tahun_arsip}. Tabel input sekarang kosong.")
                        except Exception as e:
                            st.error(f"Gagal mengarsipkan: {e}")
                    else:
                        st.error("Tahun wajib diisi!")
    else:
        st.error("Data pengaturan tidak ditemukan di database! Pastikan database tidak kosong.")

    conn.close()