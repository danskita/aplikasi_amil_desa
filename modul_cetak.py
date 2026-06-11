import os
import sqlite3
import pandas as pd
from fpdf import FPDF

def format_rupiah(angka):
    if pd.isna(angka) or angka == "": return "Rp 0"
    return f"Rp {int(angka):,.0f}".replace(",", ".")

# ==========================================
# FUNGSI 1: KOP SURAT OTOMATIS
# ==========================================
def cetak_kop_surat(pdf, tingkat, nama_wilayah, kec, kab, logo_path="", is_landscape=False):
    page_width = 297 if is_landscape else 210
    margin_side = 10 
    pdf.set_y(10)
    
    if logo_path and os.path.exists(logo_path):
        try: pdf.image(logo_path, x=margin_side, y=10, w=22)
        except: pass
            
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 6, "BADAN AMIL ZAKAT NASIONAL (BAZNAS)", ln=1, align="C")
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 7, f"UNIT PENGUMPUL ZAKAT (UPZ) {str(tingkat).upper()} {str(nama_wilayah).upper()}", ln=1, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, f"KECAMATAN {str(kec).upper()} - KABUPATEN {str(kab).upper()}", ln=1, align="C")
    pdf.ln(5)
    
    y_garis = max(pdf.get_y(), 34)
    line_width = page_width - (margin_side * 2)
    pdf.set_line_width(0.8)
    pdf.line(margin_side, y_garis, margin_side + line_width, y_garis)
    pdf.set_line_width(0.2)
    pdf.line(margin_side, y_garis + 1, margin_side + line_width, y_garis + 1)
    pdf.set_y(y_garis + 5)

def get_data_kecamatan(db_name):
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT nama_kecamatan, kabupaten, ketua_upz, sekretaris, logo_path FROM pengaturan WHERE nama_desa='KECAMATAN'")
    p = c.fetchone(); conn.close()
    if p: return str(p[0] or "KECAMATAN"), str(p[1] or "KABUPATEN"), str(p[2] or "KETUA"), str(p[3] or "SEKRETARIS"), str(p[4] or "")
    return "KECAMATAN", "KABUPATEN", "KETUA", "SEKRETARIS", ""

def get_data_desa(db_name):
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT nama_kecamatan, kabupaten, kepala_desa, ketua_upz, bendahara, logo_path FROM pengaturan WHERE id=1")
    p = c.fetchone(); conn.close()
    if p: return str(p[0] or "KECAMATAN"), str(p[1] or "KABUPATEN"), str(p[2] or "Kepala Desa"), str(p[3] or "Ketua UPZ"), str(p[4] or "Bendahara"), str(p[5] or "")
    return "KECAMATAN", "KABUPATEN", "Kepala Desa", "Ketua UPZ", "Bendahara", ""

# ==========================================
# FUNGSI 2: LAPORAN D3 (UNTUK DESA)
# ==========================================
def cetak_d3_desa(db_name, nama_desa, tempat_ba, tgl_ba, no_ba):
    kec, kab, kades, ketua, ben, logo = get_data_desa(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    
    # Ambil rincian data lengkap (Jiwa dan Nominal)
    c.execute("SELECT SUM(jiwa_beras), SUM(jiwa_uang), SUM(total_beras), SUM(total_uang), SUM(infaq) FROM setoran_dkm WHERE nama_desa COLLATE NOCASE = ?", (nama_desa,))
    tot = c.fetchone()
    t_jb = tot[0] or 0
    t_ju = tot[1] or 0
    t_tb = tot[2] or 0.0
    t_tu = tot[3] or 0.0
    t_infaq = tot[4] or 0.0
    conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    cetak_kop_surat(pdf, "DESA", nama_desa, kec, kab, logo)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "FORMAT D3 - REKAPITULASI PENERIMAAN (100%)", ln=1, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(30, 8, "Nomor", border=0); pdf.cell(0, 8, f": {no_ba}", ln=1)
    pdf.cell(30, 8, "Perihal", border=0); pdf.cell(0, 8, f": Laporan Rekapitulasi Zakat & Infaq 100%", ln=1)
    pdf.ln(5)
    
    teks_pembuka = f"Berdasarkan hasil penghimpunan dari seluruh UPZ DKM di wilayah Desa {nama_desa.capitalize()}, berikut adalah rincian rekapitulasi penerimaan Zakat Fitrah dan Infaq (100%):"
    pdf.multi_cell(0, 6, teks_pembuka)
    pdf.ln(5)
    
    # TABEL D3 YANG RESMI DAN RAPI
    pdf.set_font("Arial", "B", 11)
    pdf.cell(10, 8, "NO", border=1, align="C")
    pdf.cell(70, 8, "URAIAN PENERIMAAN", border=1, align="C")
    pdf.cell(40, 8, "JUMLAH MUZAKKI", border=1, align="C")
    pdf.cell(60, 8, "TOTAL TERKUMPUL", border=1, align="C", ln=1)
    
    pdf.set_font("Arial", "", 11)
    
    # Baris 1: Zakat Beras
    pdf.cell(10, 8, "1", border=1, align="C")
    pdf.cell(70, 8, " Zakat Fitrah (Beras)", border=1)
    pdf.cell(40, 8, f"{int(t_jb)} Jiwa", border=1, align="C")
    pdf.cell(60, 8, f"{t_tb:,.2f} Kg", border=1, align="C", ln=1)
    
    # Baris 2: Zakat Uang
    pdf.cell(10, 8, "2", border=1, align="C")
    pdf.cell(70, 8, " Zakat Fitrah (Uang)", border=1)
    pdf.cell(40, 8, f"{int(t_ju)} Jiwa", border=1, align="C")
    pdf.cell(60, 8, format_rupiah(t_tu), border=1, align="C", ln=1)
    
    # Baris 3: Infaq
    pdf.cell(10, 8, "3", border=1, align="C")
    pdf.cell(70, 8, " Infaq / Sedekah", border=1)
    pdf.cell(40, 8, "-", border=1, align="C")
    pdf.cell(60, 8, format_rupiah(t_infaq), border=1, align="C", ln=1)
    
    # Baris 4: Total Global Jiwa
    pdf.set_font("Arial", "B", 11)
    pdf.cell(80, 8, "TOTAL KESELURUHAN MUZAKKI", border=1, align="C")
    pdf.cell(40, 8, f"{int(t_jb + t_ju)} Jiwa", border=1, align="C")
    pdf.cell(60, 8, "", border=1, align="C", ln=1)
    
    pdf.ln(10)
    teks_penutup = "Demikian laporan rekapitulasi ini dibuat dengan sebenar-benarnya untuk dapat dipergunakan sebagaimana mestinya."
    pdf.multi_cell(0, 6, teks_penutup)
    
    pdf.ln(15)
    pdf.cell(90, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(90, 6, "Kepala Desa,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Desa,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 12)
    pdf.cell(90, 6, f"( {kades} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    
    return pdf.output(dest='S').encode('latin-1')

def cetak_d2_desa(db_name, nama_desa, tempat_ba, tgl_ba):
    kec, kab, kades, ketua, ben, logo = get_data_desa(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT nama_dkm, jiwa_beras, jiwa_uang, total_beras, total_uang, infaq FROM setoran_dkm WHERE nama_desa COLLATE NOCASE = ?", (nama_desa,))
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="L", unit="mm", format="A4"); pdf.set_margins(10, 10, 10); pdf.add_page()
    cetak_kop_surat(pdf, "DESA", nama_desa, kec, kab, logo, True)
    
    pdf.set_font("Arial", "B", 13); pdf.cell(0, 8, "FORMAT D2 - RINCIAN PENGHIMPUNAN ZAKAT FITRAH PER UPZ DKM", ln=1, align="C"); pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(10, 10, "NO", border=1, align="C"); pdf.cell(75, 10, "NAMA UPZ DKM / WAKIL", border=1, align="C")
    pdf.cell(25, 10, "MUZAKKI (Jb)", border=1, align="C"); pdf.cell(25, 10, "MUZAKKI (Ju)", border=1, align="C")
    pdf.cell(35, 10, "TOTAL BERAS (Kg)", border=1, align="C"); pdf.cell(40, 10, "TOTAL UANG ZAKAT", border=1, align="C")
    pdf.cell(35, 10, "TOTAL INFAQ (Rp)", border=1, align="C", ln=1)
    
    pdf.set_font("Arial", "", 9)
    t_jb, t_ju, t_b, t_u, t_i = 0, 0, 0.0, 0.0, 0.0
    for i, r in enumerate(rows):
        pdf.cell(10, 8, str(i+1), border=1, align="C"); pdf.cell(75, 8, str(r[0])[:35], border=1)
        pdf.cell(25, 8, str(int(r[1] or 0)), border=1, align="C"); pdf.cell(25, 8, str(int(r[2] or 0)), border=1, align="C")
        pdf.cell(35, 8, f"{r[3] or 0:,.2f}", border=1, align="C"); pdf.cell(40, 8, format_rupiah(r[4]), border=1, align="R")
        pdf.cell(35, 8, format_rupiah(r[5]), border=1, align="R", ln=1)
        t_jb += (r[1] or 0); t_ju += (r[2] or 0); t_b += (r[3] or 0.0); t_u += (r[4] or 0.0); t_i += (r[5] or 0.0)

    pdf.set_font("Arial", "B", 9)
    pdf.cell(85, 8, "TOTAL JUMLAH KESELURUHAN", border=1, align="C"); pdf.cell(25, 8, str(int(t_jb)), border=1, align="C")
    pdf.cell(25, 8, str(int(t_ju)), border=1, align="C"); pdf.cell(35, 8, f"{t_b:,.2f}", border=1, align="C")
    pdf.cell(40, 8, format_rupiah(t_u), border=1, align="R"); pdf.cell(35, 8, format_rupiah(t_i), border=1, align="R", ln=1)
    
    pdf.ln(10); pdf.set_font("Arial", "", 11)
    pdf.cell(140, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(140, 6, "Kepala Desa,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Desa,", border=0, align="C", ln=1)
    pdf.ln(15); pdf.set_font("Arial", "B", 11)
    pdf.cell(140, 6, f"( {kades} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_d45_desa(db_name, nama_desa, tempat_ba, tgl_ba):
    kec, kab, kades, ketua, ben, logo = get_data_desa(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT program, penerima, beras, uang FROM sabilillah WHERE nama_desa COLLATE NOCASE = ?", (nama_desa,))
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(10, 10, 10); pdf.add_page()
    cetak_kop_surat(pdf, "DESA", nama_desa, kec, kab, logo)
    
    pdf.set_font("Arial", "B", 13); pdf.cell(0, 8, "FORMAT D4 & D5 - DAFTAR DISTRIBUSI ASNAF SABILILLAH", ln=1, align="C"); pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(10, 10, "NO", border=1, align="C"); pdf.cell(65, 10, "NAMA PENERIMA / ASNAF", border=1, align="C")
    pdf.cell(50, 10, "KATEGORI PROGRAM", border=1, align="C"); pdf.cell(30, 10, "BERAS (Kg)", border=1, align="C"); pdf.cell(35, 10, "UANG (Rp)", border=1, align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    t_b, t_u = 0.0, 0.0
    for i, r in enumerate(rows):
        pdf.cell(10, 8, str(i+1), border=1, align="C"); pdf.cell(65, 8, str(r[1])[:30], border=1)
        pdf.cell(50, 8, str(r[0])[:25], border=1); pdf.cell(30, 8, f"{r[2] or 0:,.2f}", border=1, align="C")
        pdf.cell(35, 8, format_rupiah(r[3]), border=1, align="R", ln=1)
        t_b += (r[2] or 0.0); t_u += (r[3] or 0.0)
        
    pdf.set_font("Arial", "B", 10)
    pdf.cell(125, 8, "TOTAL REALISASI SABILILLAH DESA", border=1, align="C"); pdf.cell(30, 8, f"{t_b:,.2f}", border=1, align="C")
    pdf.cell(35, 8, format_rupiah(t_u), border=1, align="R", ln=1)
    
    pdf.ln(15); pdf.set_font("Arial", "", 11)
    pdf.cell(95, 6, "Mengetahui,", border=0, align="C"); pdf.cell(95, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(95, 6, "Kepala Desa,", border=0, align="C"); pdf.cell(95, 6, "Ketua UPZ Desa,", border=0, align="C", ln=1)
    pdf.ln(15); pdf.set_font("Arial", "B", 11)
    pdf.cell(95, 6, f"( {kades} )", border=0, align="C"); pdf.cell(95, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_d6_desa(db_name, nama_desa, tempat_ba, tgl_ba):
    kec, kab, kades, ketua, ben, logo = get_data_desa(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT nama, jabatan, beras, uang FROM amilin WHERE nama_desa COLLATE NOCASE = ?", (nama_desa,))
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(10, 10, 10); pdf.add_page()
    cetak_kop_surat(pdf, "DESA", nama_desa, kec, kab, logo)
    
    pdf.set_font("Arial", "B", 13); pdf.cell(0, 8, "FORMAT D6 - DAFTAR PENYALURAN HAK ASNAF AMILIN", ln=1, align="C"); pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(10, 10, "NO", border=1, align="C"); pdf.cell(70, 10, "NAMA PETUGAS AMIL", border=1, align="C")
    pdf.cell(50, 10, "JABATAN STRUKTUR", border=1, align="C"); pdf.cell(25, 10, "BERAS (Kg)", border=1, align="C"); pdf.cell(35, 10, "UANG (Rp)", border=1, align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    t_b, t_u = 0.0, 0.0
    for i, r in enumerate(rows):
        pdf.cell(10, 8, str(i+1), border=1, align="C"); pdf.cell(70, 8, str(r[0])[:30], border=1)
        pdf.cell(50, 8, str(r[1])[:25], border=1); pdf.cell(25, 8, f"{r[2] or 0:,.2f}", border=1, align="C")
        pdf.cell(35, 8, format_rupiah(r[3]), border=1, align="R", ln=1)
        t_b += (r[2] or 0.0); t_u += (r[3] or 0.0)
        
    pdf.set_font("Arial", "B", 10)
    pdf.cell(130, 8, "TOTAL PEMBAGIAN AMILIN DESA", border=1, align="C"); pdf.cell(25, 8, f"{t_b:,.2f}", border=1, align="C")
    pdf.cell(35, 8, format_rupiah(t_u), border=1, align="R", ln=1)
    
    pdf.ln(15); pdf.set_font("Arial", "", 11)
    pdf.cell(95, 6, "Mengetahui,", border=0, align="C"); pdf.cell(95, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(95, 6, "Kepala Desa,", border=0, align="C"); pdf.cell(95, 6, "Ketua UPZ Desa,", border=0, align="C", ln=1)
    pdf.ln(15); pdf.set_font("Arial", "B", 11)
    pdf.cell(95, 6, f"( {kades} )", border=0, align="C"); pdf.cell(95, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_kupon_desa(db_name, nama_desa, tempat_ba, tgl_ba):
    kec, kab, kades, ketua, ben, logo = get_data_desa(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT SUM(kupon_diterima), SUM(kupon_terjual), SUM(kupon_kembali) FROM setoran_dkm WHERE nama_desa COLLATE NOCASE = ?", (nama_desa,))
    row = c.fetchone(); conn.close()
    k_terima = row[0] or 0; k_jual = row[1] or 0; k_balik = row[2] or 0

    pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(15, 15, 15); pdf.add_page()
    cetak_kop_surat(pdf, "DESA", nama_desa, kec, kab, logo)
    
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "SURAT BERITA ACARA SERAH TERIMA KUPON INFAQ", ln=1, align="C"); pdf.ln(10)
    
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 6, f"Pada hari ini telah diserahterimakan hasil rekapitulasi penggunaan Kupon Infaq Ramadhan pada UPZ Desa {nama_desa.capitalize()} dengan rincian total sebagai berikut:")
    pdf.ln(5)
    
    pdf.cell(60, 8, "1. Total Kupon Diterima", border=0); pdf.cell(0, 8, f": {k_terima} Lembar", ln=1)
    pdf.cell(60, 8, "2. Total Kupon Terjual", border=0); pdf.cell(0, 8, f": {k_jual} Lembar", ln=1)
    pdf.cell(60, 8, "3. Total Kupon Dikembalikan", border=0); pdf.cell(0, 8, f": {k_balik} Lembar", ln=1)
    pdf.ln(5)
    pdf.multi_cell(0, 6, "Demikian berita acara ini dibuat dengan sebenar-benarnya untuk dipergunakan sebagaimana mestinya.")
    
    pdf.ln(20); pdf.cell(90, 6, "Yang Menyerahkan (Bendahara),", border=0, align="C"); pdf.cell(90, 6, "Yang Menerima (Ketua UPZ),", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 12)
    pdf.cell(90, 6, f"( {ben} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# SEMUA FUNGSI LAPORAN KECAMATAN (K1 - K4)
# ==========================================
def cetak_k1_kecamatan(db_name, tempat_ba, tgl_ba):
    kec, kab, ketua, sek, logo = get_data_kecamatan(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT SUM(total_beras), SUM(total_uang) FROM setoran_dkm")
    tot = c.fetchone()
    t_beras = tot[0] or 0.0; t_uang = tot[1] or 0.0
    conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(10, 10, 10); pdf.add_page()
    cetak_kop_surat(pdf, "KECAMATAN", kec, kec, kab, logo)
    
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "FORMAT K1 - REKAPITULASI PENERIMAAN ZAKAT (5% KECAMATAN)", ln=1, align="C"); pdf.ln(5)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, f"Berdasarkan hasil penghimpunan zakat fitrah dari seluruh UPZ Desa se-Kecamatan {kec}, berikut adalah rincian hak kelola UPZ Kecamatan (5%):")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(10, 8, "NO", border=1, align="C"); pdf.cell(90, 8, "URAIAN", border=1, align="C")
    pdf.cell(40, 8, "BERAS (Kg)", border=1, align="C"); pdf.cell(50, 8, "UANG TUNAI (Rp)", border=1, align="C", ln=1)
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(10, 8, "1", border=1, align="C"); pdf.cell(90, 8, "Total Penghimpunan (100%)", border=1)
    pdf.cell(40, 8, f"{t_beras:,.2f}", border=1, align="C"); pdf.cell(50, 8, format_rupiah(t_uang), border=1, align="R", ln=1)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(10, 8, "2", border=1, align="C"); pdf.cell(90, 8, "Hak UPZ Kecamatan (5%)", border=1)
    pdf.cell(40, 8, f"{t_beras*0.05:,.2f}", border=1, align="C"); pdf.cell(50, 8, format_rupiah(t_uang*0.05), border=1, align="R", ln=1)
    
    pdf.ln(20)
    pdf.cell(100, 8, "", border=0); pdf.cell(90, 8, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(100, 8, "Sekretaris UPZ,", border=0, align="C"); pdf.cell(90, 8, "Ketua UPZ Kecamatan,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.cell(100, 8, f"( {sek} )", border=0, align="C"); pdf.cell(90, 8, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_k2_sabilillah(db_name, tempat_ba, tgl_ba):
    kec, kab, ketua, sek, logo = get_data_kecamatan(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT program, penerima, beras, uang FROM distribusi_kec_program ORDER BY program ASC")
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(10, 10, 10); pdf.set_auto_page_break(True, margin=15); pdf.add_page()
    cetak_kop_surat(pdf, "KECAMATAN", kec, kec, kab, logo)
    
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 6, "FORMAT K2 - DAFTAR PENYALURAN ZAKAT FITRAH (SABILILLAH)", ln=1, align="C"); pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(10, 10, "NO", border=1, align="C"); pdf.cell(60, 10, "NAMA LEMBAGA/PENERIMA", border=1, align="C")
    pdf.cell(50, 10, "PROGRAM", border=1, align="C"); pdf.cell(25, 10, "BERAS (Kg)", border=1, align="C")
    pdf.cell(30, 10, "UANG (Rp)", border=1, align="C"); pdf.cell(15, 10, "TTD", border=1, align="C", ln=1)
    
    pdf.set_font("Arial", "", 9)
    t_b = 0.0; t_u = 0.0
    for i, r in enumerate(rows):
        pdf.cell(10, 8, str(i+1), border=1, align="C"); pdf.cell(60, 8, str(r[1])[:30], border=1)
        pdf.cell(50, 8, str(r[0])[:25], border=1); pdf.cell(25, 8, f"{r[2] or 0:,.2f}", border=1, align="C")
        pdf.cell(30, 8, f"{int(r[3] or 0):,}", border=1, align="R"); pdf.cell(15, 8, "", border=1, ln=1)
        t_b += (r[2] or 0.0); t_u += (r[3] or 0.0)
        
    pdf.set_font("Arial", "B", 9)
    pdf.cell(120, 8, "TOTAL KESELURUHAN", border=1, align="C"); pdf.cell(25, 8, f"{t_b:,.2f}", border=1, align="C")
    pdf.cell(30, 8, f"{int(t_u):,}", border=1, align="R"); pdf.cell(15, 8, "", border=1, ln=1)
    
    pdf.ln(15); pdf.set_font("Arial", "", 11)
    pdf.cell(100, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(100, 6, "Sekretaris UPZ,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Kecamatan,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 11)
    pdf.cell(100, 6, f"( {sek} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_k3_program(db_name, tempat_ba, tgl_ba):
    kec, kab, ketua, sek, logo = get_data_kecamatan(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT program, SUM(beras), SUM(uang) FROM distribusi_kec_program GROUP BY program")
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(10, 10, 10); pdf.add_page()
    cetak_kop_surat(pdf, "KECAMATAN", kec, kec, kab, logo)
    
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "FORMAT K3 - REKAPITULASI PENYALURAN PROGRAM (SABILILLAH)", ln=1, align="C"); pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(15, 10, "NO", border=1, align="C"); pdf.cell(85, 10, "NAMA PROGRAM SABILILLAH", border=1, align="C")
    pdf.cell(40, 10, "TOTAL BERAS (Kg)", border=1, align="C"); pdf.cell(50, 10, "TOTAL UANG (Rp)", border=1, align="C", ln=1)
    
    pdf.set_font("Arial", "", 11)
    t_b = 0.0; t_u = 0.0
    for i, r in enumerate(rows):
        pdf.cell(15, 8, str(i+1), border=1, align="C"); pdf.cell(85, 8, str(r[0]), border=1)
        pdf.cell(40, 8, f"{r[1] or 0:,.2f}", border=1, align="C"); pdf.cell(50, 8, f"{int(r[2] or 0):,}", border=1, align="R", ln=1)
        t_b += (r[1] or 0.0); t_u += (r[2] or 0.0)
        
    pdf.set_font("Arial", "B", 11)
    pdf.cell(100, 8, "TOTAL REALISASI PROGRAM", border=1, align="C"); pdf.cell(40, 8, f"{t_b:,.2f}", border=1, align="C")
    pdf.cell(50, 8, format_rupiah(t_u), border=1, align="R", ln=1)
    
    pdf.ln(20); pdf.cell(100, 8, "", border=0); pdf.cell(90, 8, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(100, 8, "Sekretaris UPZ,", border=0, align="C"); pdf.cell(90, 8, "Ketua UPZ Kecamatan,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.cell(100, 8, f"( {sek} )", border=0, align="C"); pdf.cell(90, 8, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_k4_amilin(db_name, tempat_ba, tgl_ba):
    kec, kab, ketua, sek, logo = get_data_kecamatan(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT nama, jabatan, beras, uang FROM distribusi_kec_amil")
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(10, 10, 10); pdf.add_page()
    cetak_kop_surat(pdf, "KECAMATAN", kec, kec, kab, logo)
    
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "FORMAT K4 - DAFTAR PENYALURAN HAK AMILIN KECAMATAN", ln=1, align="C"); pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(10, 10, "NO", border=1, align="C"); pdf.cell(60, 10, "NAMA AMIL", border=1, align="C")
    pdf.cell(50, 10, "JABATAN", border=1, align="C"); pdf.cell(25, 10, "BERAS (Kg)", border=1, align="C")
    pdf.cell(30, 10, "UANG (Rp)", border=1, align="C"); pdf.cell(15, 10, "TTD", border=1, align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    t_b = 0.0; t_u = 0.0
    for i, r in enumerate(rows):
        pdf.cell(10, 8, str(i+1), border=1, align="C"); pdf.cell(60, 8, str(r[0])[:30], border=1)
        pdf.cell(50, 8, str(r[1])[:25], border=1); pdf.cell(25, 8, f"{r[2] or 0:,.2f}", border=1, align="C")
        pdf.cell(30, 8, f"{int(r[3] or 0):,}", border=1, align="R"); pdf.cell(15, 8, "", border=1, ln=1)
        t_b += (r[2] or 0.0); t_u += (r[3] or 0.0)
        
    pdf.set_font("Arial", "B", 10)
    pdf.cell(120, 8, "TOTAL HAK AMIL KECAMATAN", border=1, align="C"); pdf.cell(25, 8, f"{t_b:,.2f}", border=1, align="C")
    pdf.cell(30, 8, f"{int(t_u):,}", border=1, align="R"); pdf.cell(15, 8, "", border=1, ln=1)
    
    pdf.ln(20); pdf.set_font("Arial", "", 11)
    pdf.cell(100, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(100, 6, "Mengetahui,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Kecamatan,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 11)
    pdf.cell(100, 6, "( ................................... )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_surat_6persen(db_name, tempat_ba, tgl_ba, no_surat):
    kec, kab, ketua, sek, logo = get_data_kecamatan(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT SUM(total_beras), SUM(total_uang) FROM setoran_dkm")
    tot = c.fetchone()
    t_beras = tot[0] or 0.0; t_uang = tot[1] or 0.0
    kab_b = t_beras * 0.06; kab_u = t_uang * 0.06
    conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4"); pdf.set_margins(15, 15, 15); pdf.add_page()
    cetak_kop_surat(pdf, "KECAMATAN", kec, kec, kab, logo)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(30, 6, "Nomor", border=0); pdf.cell(80, 6, f": {no_surat}", border=0); pdf.cell(0, 6, f"Kepada Yth.", border=0, ln=1)
    pdf.cell(30, 6, "Lampiran", border=0); pdf.cell(80, 6, f": 1 (Satu) berkas", border=0); pdf.cell(0, 6, f"Ketua BAZNAS Kab. {kab}", border=0, ln=1)
    pdf.cell(30, 6, "Perihal", border=0); pdf.cell(80, 6, f": Pengajuan Penyaluran 6%", border=0); pdf.cell(0, 6, f"di- Tempat", border=0, ln=1)
    
    pdf.ln(10); pdf.cell(0, 6, "Assalamu'alaikum Wr. Wb.", ln=1); pdf.ln(2)
    teks_pembuka = f"Bersama surat ini kami sampaikan bahwa UPZ Kecamatan {kec} telah menghimpun Zakat Fitrah dari seluruh UPZ Desa. Mengacu pada ketentuan Hak Kelola BAZNAS Kabupaten sebesar 6% dari total penghimpunan, berikut adalah rincian hak BAZNAS yang telah terkumpul:"
    pdf.multi_cell(0, 6, teks_pembuka); pdf.ln(5)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(20, 8, "", border=0)
    pdf.cell(70, 8, "Total Beras (6%)", border=1); pdf.cell(60, 8, f"{kab_b:,.2f} Kg", border=1, align="C", ln=1)
    pdf.cell(20, 8, "", border=0)
    pdf.cell(70, 8, "Total Uang (6%)", border=1); pdf.cell(60, 8, format_rupiah(kab_u), border=1, align="C", ln=1)
    
    pdf.ln(5); pdf.set_font("Arial", "", 12)
    teks_penutup = "Selanjutnya, kami memohon arahan serta persetujuan untuk pendistribusian dana tersebut sesuai dengan program yang telah direkomendasikan. Demikian surat ini kami sampaikan, atas perhatian dan kerjasamanya kami ucapkan terima kasih.\n\nWassalamu'alaikum Wr. Wb."
    pdf.multi_cell(0, 6, teks_penutup); pdf.ln(15)
    
    pdf.cell(90, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(90, 6, "Sekretaris UPZ,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Kecamatan,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 12)
    pdf.cell(90, 6, f"( {sek} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_kwitansi(nama_lembaga, nominal_rp, untuk_pembayaran, tempat_tgl):
    pdf = FPDF(orientation="L", unit="mm", format=(100, 210)); pdf.add_page(); pdf.set_margins(10, 10, 10)
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "K U I T A N S I   B A Z N A S", ln=1, align="C")
    pdf.set_line_width(0.5); pdf.line(10, 20, 200, 20); pdf.ln(10)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(45, 8, "Sudah terima dari", border=0); pdf.cell(0, 8, ": UPZ KECAMATAN", ln=1)
    pdf.cell(45, 8, "Banyaknya uang", border=0); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, f": {format_rupiah(nominal_rp)}", ln=1)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(45, 8, "Untuk pembayaran", border=0); pdf.multi_cell(0, 8, f": {untuk_pembayaran}"); pdf.ln(10)
    
    pdf.cell(100, 8, "", border=0); pdf.cell(90, 8, tempat_tgl, border=0, align="C", ln=1)
    pdf.cell(100, 8, "Yang Menerima,", border=0, align="C"); pdf.cell(90, 8, "Bendahara UPZ,", border=0, align="C", ln=1)
    pdf.ln(15); pdf.set_font("Arial", "B", 12)
    pdf.cell(100, 8, f"( {nama_lembaga} )", border=0, align="C"); pdf.cell(90, 8, "( .............................. )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')
# ==========================================
# FUNGSI CETAK QURBAN & MAJLIS (DESA)
# ==========================================
def cetak_qurban_desa(db_name, nama_desa, tempat_ba, tgl_ba):
    kec, kab, kades, ketua, ben, logo = get_data_desa(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT tahun, nama_dkm, jenis_hewan, jumlah_hewan, jumlah_mudhohi FROM qurban WHERE nama_desa COLLATE NOCASE = ? ORDER BY tahun DESC, nama_dkm ASC", (nama_desa,))
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15); pdf.add_page()
    cetak_kop_surat(pdf, "DESA", nama_desa, kec, kab, logo)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "LAPORAN DATA HEWAN QURBAN", ln=1, align="C"); pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(10, 8, "NO", border=1, align="C"); pdf.cell(20, 8, "TAHUN", border=1, align="C")
    pdf.cell(60, 8, "NAMA DKM / WILAYAH", border=1, align="C"); pdf.cell(30, 8, "JENIS HEWAN", border=1, align="C")
    pdf.cell(30, 8, "JUMLAH", border=1, align="C"); pdf.cell(30, 8, "MUDHOHI", border=1, align="C", ln=1)

    pdf.set_font("Arial", "", 10)
    t_hewan, t_mudhohi = 0, 0
    for i, r in enumerate(rows):
        pdf.cell(10, 8, str(i+1), border=1, align="C"); pdf.cell(20, 8, str(r[0]), border=1, align="C")
        pdf.cell(60, 8, str(r[1])[:30], border=1); pdf.cell(30, 8, str(r[2]), border=1, align="C")
        pdf.cell(30, 8, f"{r[3]} Ekor", border=1, align="C"); pdf.cell(30, 8, f"{r[4]} Orang", border=1, align="C", ln=1)
        t_hewan += r[3] or 0; t_mudhohi += r[4] or 0

    pdf.set_font("Arial", "B", 10)
    pdf.cell(120, 8, "TOTAL KESELURUHAN", border=1, align="C"); pdf.cell(30, 8, f"{t_hewan} Ekor", border=1, align="C")
    pdf.cell(30, 8, f"{t_mudhohi} Orang", border=1, align="C", ln=1)

    pdf.ln(15); pdf.set_font("Arial", "", 11)
    pdf.cell(90, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(90, 6, "Kepala Desa,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Desa,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 11)
    pdf.cell(90, 6, f"( {kades} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_majlis_desa(db_name, nama_desa, tempat_ba, tgl_ba):
    kec, kab, kades, ketua, ben, logo = get_data_desa(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT nama_majlis, pimpinan FROM majlis_talim WHERE nama_desa COLLATE NOCASE = ? ORDER BY nama_majlis ASC", (nama_desa,))
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15); pdf.add_page()
    cetak_kop_surat(pdf, "DESA", nama_desa, kec, kab, logo)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "LAPORAN DATA MAJLIS TA'LIM", ln=1, align="C"); pdf.ln(5)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(15, 8, "NO", border=1, align="C"); pdf.cell(85, 8, "NAMA MAJLIS TA'LIM", border=1, align="C")
    pdf.cell(80, 8, "NAMA PIMPINAN", border=1, align="C", ln=1)

    pdf.set_font("Arial", "", 11)
    for i, r in enumerate(rows):
        pdf.cell(15, 8, str(i+1), border=1, align="C"); pdf.cell(85, 8, str(r[0])[:40], border=1)
        pdf.cell(80, 8, str(r[1])[:35], border=1, ln=1)

    pdf.ln(15); pdf.set_font("Arial", "", 11)
    pdf.cell(90, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(90, 6, "Kepala Desa,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Desa,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 11)
    pdf.cell(90, 6, f"( {kades} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# FUNGSI CETAK QURBAN & MAJLIS (KECAMATAN)
# ==========================================
def cetak_rekap_qurban_kec(db_name, tempat_ba, tgl_ba):
    kec, kab, ketua, sek, logo = get_data_kecamatan(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT nama_desa, jenis_hewan, jumlah_hewan, jumlah_mudhohi FROM qurban ORDER BY nama_desa ASC")
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10); pdf.add_page()
    cetak_kop_surat(pdf, "KECAMATAN", kec, kec, kab, logo)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "REKAPITULASI HEWAN QURBAN TINGKAT KECAMATAN", ln=1, align="C"); pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(10, 8, "NO", border=1, align="C"); pdf.cell(50, 8, "ASAL DESA", border=1, align="C")
    pdf.cell(40, 8, "JENIS HEWAN", border=1, align="C"); pdf.cell(45, 8, "JUMLAH (Ekor)", border=1, align="C")
    pdf.cell(45, 8, "MUDHOHI (Orang)", border=1, align="C", ln=1)

    pdf.set_font("Arial", "", 10)
    t_hewan, t_mudhohi = 0, 0
    for i, r in enumerate(rows):
        pdf.cell(10, 8, str(i+1), border=1, align="C"); pdf.cell(50, 8, str(r[0])[:25], border=1)
        pdf.cell(40, 8, str(r[1]), border=1, align="C"); pdf.cell(45, 8, str(r[2]), border=1, align="C")
        pdf.cell(45, 8, str(r[3]), border=1, align="C", ln=1)
        t_hewan += r[2] or 0; t_mudhohi += r[3] or 0

    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 8, "TOTAL KESELURUHAN", border=1, align="C"); pdf.cell(45, 8, f"{t_hewan} Ekor", border=1, align="C")
    pdf.cell(45, 8, f"{t_mudhohi} Orang", border=1, align="C", ln=1)

    pdf.ln(15); pdf.set_font("Arial", "", 11)
    pdf.cell(100, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(100, 6, "Sekretaris UPZ,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Kecamatan,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 11)
    pdf.cell(100, 6, f"( {sek} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')

def cetak_rekap_majlis_kec(db_name, tempat_ba, tgl_ba):
    kec, kab, ketua, sek, logo = get_data_kecamatan(db_name)
    conn = sqlite3.connect(db_name); c = conn.cursor()
    c.execute("SELECT nama_desa, nama_majlis, pimpinan FROM majlis_talim ORDER BY nama_desa ASC, nama_majlis ASC")
    rows = c.fetchall(); conn.close()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10); pdf.add_page()
    cetak_kop_surat(pdf, "KECAMATAN", kec, kec, kab, logo)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "DATA REKAPITULASI MAJLIS TA'LIM", ln=1, align="C"); pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(10, 8, "NO", border=1, align="C"); pdf.cell(50, 8, "ASAL DESA", border=1, align="C")
    pdf.cell(70, 8, "NAMA MAJLIS TA'LIM", border=1, align="C"); pdf.cell(60, 8, "PIMPINAN", border=1, align="C", ln=1)

    pdf.set_font("Arial", "", 10)
    for i, r in enumerate(rows):
        pdf.cell(10, 8, str(i+1), border=1, align="C"); pdf.cell(50, 8, str(r[0])[:25], border=1)
        pdf.cell(70, 8, str(r[1])[:35], border=1); pdf.cell(60, 8, str(r[2])[:30], border=1, ln=1)

    pdf.ln(15); pdf.set_font("Arial", "", 11)
    pdf.cell(100, 6, "", border=0); pdf.cell(90, 6, f"{tempat_ba}, {tgl_ba}", border=0, align="C", ln=1)
    pdf.cell(100, 6, "Sekretaris UPZ,", border=0, align="C"); pdf.cell(90, 6, "Ketua UPZ Kecamatan,", border=0, align="C", ln=1)
    pdf.ln(20); pdf.set_font("Arial", "B", 11)
    pdf.cell(100, 6, f"( {sek} )", border=0, align="C"); pdf.cell(90, 6, f"( {ketua} )", border=0, align="C", ln=1)
    return pdf.output(dest='S').encode('latin-1')