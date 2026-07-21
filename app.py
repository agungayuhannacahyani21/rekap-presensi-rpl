import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ---------------------------------------------------------
# 1. KONEKSI KE SUPABASE
# ---------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["SUPABASE_URL"]
    key = st.secrets["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Gagal terhubung ke Supabase: {e}")
    st.stop()

# ---------------------------------------------------------
# 2. KONFIGURASI HALAMAN & NAVIGASI
# ---------------------------------------------------------
st.set_page_config(page_title="Rekap Presensi Mingguan", layout="wide")
st.title("📋 Sistem Rekap Presensi Mingguan Siswa")

menu = st.sidebar.selectbox("Pilih Menu", ["Input Presensi Mingguan", "Rekap & Laporan", "Kelola Data Siswa"])

# ---------------------------------------------------------
# MENU 1: INPUT PRESENSI MINGGUAN
# ---------------------------------------------------------
if menu == "Input Presensi Mingguan":
    st.subheader("📝 Form Input Ketidakhadiran Mingguan")
    
    # Ambil Daftar Kelas
    data_kelas = supabase.table("siswa").select("kelas").execute()
    list_kelas = sorted(list(set([item['kelas'] for item in data_kelas.data]))) if data_kelas.data else []
    
    if not list_kelas:
        st.warning("Belum ada data siswa/kelas. Silakan tambahkan data siswa di menu 'Kelola Data Siswa' terlebih dahulu.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            pilih_kelas = st.selectbox("Pilih Kelas", list_kelas)
        with col2:
            tahun = st.number_input("Tahun", min_value=2024, max_value=2030, value=2026)
        with col3:
            minggu_ke = st.number_input("Minggu Ke-", min_value=1, max_value=52, value=1)
            
        rentang_tgl = st.text_input("Rentang Tanggal (Opsional)", placeholder="Contoh: 20 Jul - 24 Jul 2026")

        # Ambil Siswa berdasarkan Kelas
        res_siswa = supabase.table("siswa").select("*").eq("kelas", pilih_kelas).order("nama").execute()
        daftar_siswa = res_siswa.data

        if daftar_siswa:
            st.divider()
            st.caption("💡 *Isi jumlah hari ketidakhadiran (Sakit, Izin, Alfa). Biarkan 0 jika siswa hadir penuh.*")
            
            with st.form("form_presensi_mingguan"):
                presensi_input = []
                
                # Header Form
                h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 3])
                h1.write("**Nama Siswa**")
                h2.write("**Sakit**")
                h3.write("**Izin**")
                h4.write("**Alfa**")
                h5.write("**Keterangan**")
                st.divider()

                for siswa in daftar_siswa:
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 3])
                    c1.write(f"👤 **{siswa['nama']}**")
                    
                    sakit = c2.number_input("S", min_value=0, max_value=7, value=0, key=f"s_{siswa['id']}", label_visibility="collapsed")
                    izin = c3.number_input("I", min_value=0, max_value=7, value=0, key=f"i_{siswa['id']}", label_visibility="collapsed")
                    alfa = c4.number_input("A", min_value=0, max_value=7, value=0, key=f"a_{siswa['id']}", label_visibility="collapsed")
                    ket = c5.text_input("Ket", placeholder="Catatan opsional...", key=f"ket_{siswa['id']}", label_visibility="collapsed")
                    
                    presensi_input.append({
                        "tahun": tahun,
                        "minggu_ke": minggu_ke,
                        "rentang_tanggal": rentang_tgl,
                        "siswa_id": siswa['id'],
                        "kelas": pilih_kelas,
                        "sakit": sakit,
                        "izin": izin,
                        "alfa": alfa,
                        "keterangan": ket
                    })
                
                simpan = st.form_submit_button("💾 Simpan Rekap Mingguan", use_container_width=True)
                
                if simpan:
                    # Hapus data lama jika minggu & kelas yang sama di-input ulang
                    for data in presensi_input:
                        supabase.table("presensi_mingguan") \
                            .delete() \
                            .eq("tahun", data['tahun']) \
                            .eq("minggu_ke", data['minggu_ke']) \
                            .eq("siswa_id", data['siswa_id']) \
                            .execute()
                    
                    # Insert data baru
                    supabase.table("presensi_mingguan").insert(presensi_input).execute()
                    st.success(f"Rekap presensi kelas {pilih_kelas} Minggu ke-{minggu_ke} berhasil disimpan!")

# ---------------------------------------------------------
# MENU 2: REKAP & LAPORAN
# ---------------------------------------------------------
elif menu == "Rekap & Laporan":
    st.subheader("📊 Laporan Rekapitulasi Presensi Mingguan")
    
    res_rekap = supabase.table("presensi_mingguan").select("*, siswa(nama)").execute()
    
    if res_rekap.data:
        df = pd.DataFrame(res_rekap.data)
        df['nama'] = df['siswa'].apply(lambda x: x['nama'] if isinstance(x, dict) else '')
        
        # Filter Kelas & Minggu
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            kelas_list = sorted(df['kelas'].unique())
            pilih_k = st.selectbox("Filter Kelas", ["Semua Kelas"] + list(kelas_list))
        with col_f2:
            minggu_list = sorted(df['minggu_ke'].unique())
            pilih_m = st.selectbox("Filter Minggu", ["Semua Minggu"] + list(minggu_list))
        
        if pilih_k != "Semua Kelas":
            df = df[df['kelas'] == pilih_k]
        if pilih_m != "Semua Minggu":
            df = df[df['minggu_ke'] == pilih_m]

        # Rapikan Susunan Kolom
        tabel_view = df[['tahun', 'minggu_ke', 'rentang_tanggal', 'kelas', 'nama', 'sakit', 'izin', 'alfa', 'keterangan']]
        tabel_view.columns = ['Tahun', 'Minggu Ke', 'Rentang Tanggal', 'Kelas', 'Nama Siswa', 'Sakit (S)', 'Izin (I)', 'Alfa (A)', 'Keterangan']
        
        st.dataframe(tabel_view, use_container_width=True)
        
        # Download Excel/CSV
        st.download_button(
            label="📥 Download Laporan (CSV/Excel)",
            data=tabel_view.to_csv(index=False).encode('utf-8'),
            file_name=f"rekap_mingguan_{pilih_k}_minggu_{pilih_m}.csv",
            mime="text/csv"
        )
    else:
        st.info("Belum ada data rekap presensi yang tersimpan.")

# ---------------------------------------------------------
# MENU 3: KELOLA DATA SISWA
# ---------------------------------------------------------
elif menu == "Kelola Data Siswa":
    st.subheader("➕ Tambah Data Siswa Manual")
    
    with st.form("form_siswa"):
        nama = st.text_input("Nama Lengkap Siswa")
        kelas = st.text_input("Kelas (contoh: X RPL 1)")
        submit_siswa = st.form_submit_button("Tambah Siswa")
        
        if submit_siswa:
            if nama and kelas:
                try:
                    supabase.table("siswa").insert({"nama": nama, "kelas": kelas}).execute()
                    st.success(f"Siswa {nama} berhasil ditambahkan ke kelas {kelas}!")
                except Exception as err:
                    st.error(f"Gagal menambah siswa: {err}")
            else:
                st.warning("Nama dan Kelas wajib diisi!")

    st.divider()
    st.subheader("📜 Daftar Siswa Terdaftar")
    res_siswa = supabase.table("siswa").select("*").order("kelas").execute()
    if res_siswa.data:
        st.dataframe(pd.DataFrame(res_siswa.data), use_container_width=True)