import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
from database import (
    init_db, add_account, get_accounts, delete_account, add_transaction,
    get_transactions, delete_transaction, get_total_balance, add_bill,
    get_bills, update_bill, delete_bill, set_pin, get_pin_hash,
    verify_pin, clear_pin, export_all, import_transactions
)
from receipt_ocr import extract_receipt_text, suggest_amount

st.set_page_config(page_title="RuangUang", page_icon="💳", layout="wide", initial_sidebar_state="collapsed")
init_db()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.block-container { padding-top: 1.5rem; padding-bottom: 6rem; max-width: 1180px; }
h1,h2,h3 { font-family: 'Manrope', sans-serif; }
[data-testid="stMetric"] { background: #f5f7fb; border: 1px solid #e8edf4; padding: 16px; border-radius: 16px; }
div.stButton > button { border-radius: 12px; font-weight: 600; min-height: 42px; }
div[data-testid="stForm"] { border: 1px solid #e8edf4; border-radius: 16px; padding: 16px; }
.small-muted { color: #718096; font-size: .88rem; }
.hero { background: linear-gradient(120deg,#142b4a,#245b69); padding: 24px; border-radius: 20px; color: white; margin-bottom: 18px; }
.hero-label { color: #d4e5eb; font-size: .9rem; }
.hero-value { color: white; font-size: 2rem; font-weight: 800; margin-top: 5px; }
div[data-testid="stHorizontalBlock"] { gap: 0.8rem; }
</style>
""", unsafe_allow_html=True)

def rupiah(value):
    try:
        return "Rp " + f"{int(value):,}".replace(",", ".")
    except Exception:
        return "Rp 0"

def refresh():
    st.rerun()

# Optional app-level PIN gate. This is not a replacement for proper account authentication.
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False
pin_hash = get_pin_hash()
if pin_hash and not st.session_state.unlocked:
    st.title("🔐 RuangUang")
    st.write("Aplikasi dikunci dengan PIN.")
    entered = st.text_input("Masukkan PIN", type="password", max_chars=12)
    if st.button("Buka aplikasi", type="primary"):
        if verify_pin(entered, pin_hash):
            st.session_state.unlocked = True
            refresh()
        else:
            st.error("PIN tidak sesuai.")
    st.stop()

st.markdown("# RuangUang")
st.caption("Personal Finance Tracker · Catat, pantau, dan pahami arus keuanganmu.")

pages = ["🏠 Beranda", "💼 Keuangan Saya", "📷 Scan Struk", "📊 Analisis", "👤 Profil"]
if "page" not in st.session_state:
    st.session_state.page = pages[0]
st.radio("Navigasi", pages, horizontal=True, key="page", label_visibility="collapsed")
page = st.session_state.page

accounts = get_accounts()
account_names = [a["name"] for a in accounts]

def transaction_form(kind, key):
    with st.form(key, clear_on_submit=True):
        cols = st.columns(2)
        amount = cols[0].number_input("Nominal (Rp)", min_value=1, step=1000, value=10000)
        tx_date = cols[1].date_input("Tanggal", value=date.today())
        category_options = (
            ["Uang saku", "Gaji", "Bonus", "Transfer masuk", "Bunga", "Lainnya"]
            if kind == "Income" else
            ["Makanan", "Transportasi", "Belanja", "Pendidikan", "Tagihan", "Kesehatan", "Hiburan", "Lainnya"]
        )
        category = st.selectbox("Kategori", category_options)
        account = st.selectbox("Sumber rekening", account_names) if account_names else None
        note = st.text_input("Catatan (opsional)")
        submitted = st.form_submit_button("Simpan transaksi", type="primary", use_container_width=True)
        if submitted:
            if not account:
                st.error("Tambahkan rekening terlebih dahulu di halaman Keuangan Saya.")
            else:
                add_transaction(kind, amount, category, account, tx_date.isoformat(), note)
                st.success("Transaksi berhasil disimpan.")
                refresh()

if page == "🏠 Beranda":
    st.markdown('<div class="hero"><div class="hero-label">TOTAL SALDO SELURUH AKUN</div><div class="hero-value">{}</div><div class="hero-label">Saldo gabungan dari seluruh rekening dan e-wallet</div></div>'.format(rupiah(get_total_balance())), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.expander("＋ Tambah pemasukan", expanded=False):
            transaction_form("Income", "income_form")
    with c2:
        with st.expander("－ Tambah pengeluaran", expanded=False):
            transaction_form("Expense", "expense_form")

    c1, c2 = st.columns(2)
    df = get_transactions(limit=1000)
    if not df.empty:
        today_str = date.today().isoformat()
        today = df[df["tx_date"] == today_str]
        inc = today.loc[today["kind"] == "Income", "amount"].sum()
        exp = today.loc[today["kind"] == "Expense", "amount"].sum()
    else:
        inc = exp = 0
    c1.metric("Pemasukan hari ini", rupiah(inc))
    c2.metric("Pengeluaran hari ini", rupiah(exp))

    st.subheader("Transfer antar rekening sendiri")
    with st.expander("＋ Buat transfer internal"):
        if len(accounts) < 2:
            st.info("Tambahkan minimal dua akun untuk melakukan transfer internal.")
        else:
            with st.form("transfer_form", clear_on_submit=True):
                a, b = st.columns(2)
                source = a.selectbox("Dari rekening", account_names, key="transfer_source")
                target_options = [x for x in account_names if x != source]
                target = b.selectbox("Ke rekening", target_options, key="transfer_target")
                amount = st.number_input("Nominal transfer (Rp)", min_value=1, step=1000)
                tx_date = st.date_input("Tanggal transfer", value=date.today())
                note = st.text_input("Catatan", placeholder="Contoh: Top up DANA pribadi")
                if st.form_submit_button("Simpan transfer", type="primary"):
                    add_transaction("Transfer Out", amount, "Transfer internal", source, tx_date.isoformat(), f"Ke {target}. {note}", transfer_peer=target)
                    add_transaction("Transfer In", amount, "Transfer internal", target, tx_date.isoformat(), f"Dari {source}. {note}", transfer_peer=source)
                    st.success("Transfer internal tercatat. Total saldo gabungan tidak berubah.")
                    refresh()

    st.subheader("Transaksi terbaru")
    df = get_transactions(limit=12)
    if df.empty:
        st.info("Belum ada transaksi. Tambahkan pemasukan atau pengeluaran pertamamu.")
    else:
        view = df[["tx_date", "kind", "category", "account", "amount", "note"]].copy()
        view["amount"] = view.apply(lambda r: ("+" if r["kind"] in ["Income","Transfer In"] else "−") + rupiah(r["amount"]), axis=1)
        st.dataframe(view, use_container_width=True, hide_index=True)

elif page == "💼 Keuangan Saya":
    st.subheader("Sumber keuangan")
    st.caption("Kelola rekening bank, e-wallet, dan uang tunai milikmu.")
    if accounts:
        cols = st.columns(3)
        for i, acc in enumerate(accounts):
            with cols[i % 3]:
                st.metric(acc["name"], rupiah(acc["balance"]))
                st.caption(acc["kind"])
                if st.button("Hapus akun", key=f"del_acc_{acc['id']}"):
                    if acc["balance"] != 0:
                        st.error("Akun masih memiliki saldo. Pindahkan atau catat saldonya terlebih dahulu.")
                    else:
                        delete_account(acc["id"])
                        refresh()
    else:
        st.info("Belum ada akun. Tambahkan rekening pertamamu di bawah.")
    with st.expander("＋ Tambah sumber keuangan", expanded=not bool(accounts)):
        with st.form("add_account", clear_on_submit=True):
            name = st.text_input("Nama akun", placeholder="Contoh: BRI, SeaBank, DANA")
            kind = st.selectbox("Jenis akun", ["Bank", "E-wallet", "Uang tunai", "Lainnya"])
            opening = st.number_input("Saldo awal (Rp)", min_value=0, step=10000)
            if st.form_submit_button("Tambah akun", type="primary"):
                if not name.strip():
                    st.error("Nama akun wajib diisi.")
                else:
                    try:
                        add_account(name.strip(), kind, opening)
                        st.success("Akun ditambahkan.")
                        refresh()
                    except Exception:
                        st.error("Nama akun sudah digunakan.")

    st.subheader("Tagihan, cicilan, dan PayLater")
    with st.expander("＋ Tambah tagihan / cicilan"):
        with st.form("add_bill", clear_on_submit=True):
            title = st.text_input("Nama tagihan", placeholder="Contoh: ShopeePayLater")
            provider = st.text_input("Penyedia / untuk siapa", placeholder="Contoh: Shopee, teman, atau lainnya")
            amount = st.number_input("Total tagihan (Rp)", min_value=1, step=10000)
            due = st.date_input("Tanggal jatuh tempo", value=date.today())
            note = st.text_input("Catatan (opsional)")
            if st.form_submit_button("Simpan tagihan", type="primary"):
                if title.strip():
                    add_bill(title.strip(), provider.strip(), amount, due.isoformat(), note)
                    refresh()
                else:
                    st.error("Nama tagihan wajib diisi.")
    bills = get_bills()
    if bills:
        for bill in bills:
            with st.container(border=True):
                a, b, c = st.columns([3,2,1])
                a.markdown(f"**{bill['title']}**")
                a.caption(f"{bill['provider'] or 'Tanpa penyedia'} · Jatuh tempo {bill['due_date']}")
                b.write(rupiah(bill["amount"]))
                b.caption("Lunas" if bill["paid"] else "Belum lunas")
                if not bill["paid"] and c.button("Tandai lunas", key=f"paid_{bill['id']}"):
                    update_bill(bill["id"], True)
                    refresh()
                if c.button("Hapus", key=f"bill_del_{bill['id']}"):
                    delete_bill(bill["id"])
                    refresh()
    else:
        st.caption("Belum ada tagihan atau cicilan yang dicatat.")

elif page == "📷 Scan Struk":
    st.subheader("Scan pengeluaran dari struk")
    st.write("Unggah foto struk belanja. Sistem akan mencoba membaca teks dan nominalnya; periksa hasilnya sebelum disimpan.")
    uploaded = st.file_uploader("Upload foto struk", type=["png", "jpg", "jpeg"])
    if uploaded:
        st.image(uploaded, caption="Foto struk", use_container_width=True)
        if st.button("Baca struk", type="primary"):
            with st.spinner("Membaca teks dari struk..."):
                text = extract_receipt_text(uploaded)
            st.session_state.ocr_text = text
            st.session_state.ocr_amount = suggest_amount(text)
        if st.session_state.get("ocr_text"):
            st.text_area("Teks yang terdeteksi (bisa diedit)", key="ocr_text", height=160)
            detected = st.session_state.get("ocr_amount") or 0
            with st.form("save_receipt"):
                amount = st.number_input("Nominal pengeluaran (Rp)", min_value=1, value=max(1, int(detected)), step=1000)
                category = st.selectbox("Kategori", ["Makanan", "Belanja", "Kebutuhan rumah", "Transportasi", "Pendidikan", "Lainnya"])
                acc = st.selectbox("Bayar menggunakan", account_names) if account_names else None
                tx_date = st.date_input("Tanggal transaksi", value=date.today())
                note = st.text_input("Catatan", value="Dari scan struk")
                if st.form_submit_button("Simpan sebagai pengeluaran", type="primary"):
                    if acc:
                        add_transaction("Expense", amount, category, acc, tx_date.isoformat(), note)
                        st.session_state.ocr_text = ""
                        st.session_state.ocr_amount = None
                        st.success("Pengeluaran dari struk berhasil dicatat.")
                        refresh()
                    else:
                        st.error("Tambahkan akun terlebih dahulu.")
    st.info("Catatan: hasil OCR bisa keliru, terutama pada struk yang buram. Nominal wajib diperiksa sebelum disimpan.")

elif page == "📊 Analisis":
    st.subheader("Analisis keuangan")
    df = get_transactions(limit=10000)
    if df.empty:
        st.info("Analisis akan muncul setelah ada transaksi.")
    else:
        df["tx_date"] = pd.to_datetime(df["tx_date"])
        period = st.selectbox("Periode", ["Bulan ini", "30 hari terakhir", "Tahun ini", "Semua data"])
        now = pd.Timestamp.today().normalize()
        if period == "Bulan ini":
            filtered = df[(df["tx_date"].dt.month == now.month) & (df["tx_date"].dt.year == now.year)]
        elif period == "30 hari terakhir":
            filtered = df[df["tx_date"] >= now - pd.Timedelta(days=30)]
        elif period == "Tahun ini":
            filtered = df[df["tx_date"].dt.year == now.year]
        else:
            filtered = df.copy()
        regular = filtered[filtered["kind"].isin(["Income", "Expense"])]
        income = regular.loc[regular["kind"] == "Income", "amount"].sum()
        expense = regular.loc[regular["kind"] == "Expense", "amount"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Pemasukan", rupiah(income))
        c2.metric("Pengeluaran", rupiah(expense))
        c3.metric("Selisih", rupiah(income-expense))
        if not regular.empty:
            by_kind = regular.groupby("kind", as_index=False)["amount"].sum()
            st.plotly_chart(px.pie(by_kind, names="kind", values="amount", hole=.55, title="Komposisi pemasukan dan pengeluaran"), use_container_width=True)
            exp_df = regular[regular["kind"] == "Expense"].groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            if not exp_df.empty:
                st.plotly_chart(px.bar(exp_df, x="category", y="amount", title="Pengeluaran berdasarkan kategori", labels={"amount":"Nominal (Rp)", "category":"Kategori"}), use_container_width=True)
            daily = regular.groupby([regular["tx_date"].dt.date, "kind"], as_index=False)["amount"].sum()
            st.plotly_chart(px.line(daily, x="tx_date", y="amount", color="kind", markers=True, title="Tren transaksi"), use_container_width=True)
        st.subheader("Riwayat transaksi")
        st.dataframe(filtered.sort_values("tx_date", ascending=False), use_container_width=True, hide_index=True)
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Download CSV periode ini", csv, "rekap_keuangan.csv", "text/csv")

elif page == "👤 Profil":
    st.subheader("Profil dan keamanan")
    st.write("Pengaturan dasar aplikasi RuangUang.")
    st.warning("PIN ini hanya kunci sederhana di dalam aplikasi. PIN bukan sistem login multi-pengguna dan tidak melindungi database dari pemilik/developer aplikasi.")
    current_hash = get_pin_hash()
    if current_hash:
        st.success("PIN aplikasi sedang aktif.")
        if st.button("Nonaktifkan PIN"):
            clear_pin()
            st.session_state.unlocked = True
            refresh()
    else:
        st.info("PIN belum dipasang. Penggunaan PIN bersifat opsional.")
        with st.form("set_pin"):
            p1 = st.text_input("Buat PIN (4–12 karakter)", type="password", max_chars=12)
            p2 = st.text_input("Ulangi PIN", type="password", max_chars=12)
            set_now = st.form_submit_button("Aktifkan PIN")
            if set_now:
                if len(p1) < 4:
                    st.error("PIN minimal 4 karakter.")
                elif p1 != p2:
                    st.error("PIN tidak sama.")
                else:
                    set_pin(p1)
                    st.session_state.unlocked = True
                    st.success("PIN berhasil diaktifkan.")
                    refresh()
    st.divider()
    st.subheader("Backup data")
    backup = export_all()
    st.download_button("⬇️ Download backup JSON", backup, "ruanguang_backup.json", "application/json")
    restore = st.file_uploader("Pulihkan transaksi dari backup CSV", type=["csv"])
    if restore and st.button("Import transaksi dari CSV"):
        try:
            count = import_transactions(restore)
            st.success(f"{count} transaksi berhasil diimpor.")
            refresh()
        except Exception as e:
            st.error(f"Gagal mengimpor file: {e}")
    st.caption("Untuk keamanan, jangan masukkan PIN, password, atau OTP mobile banking ke aplikasi ini.")
    st.subheader("Hapus riwayat transaksi")
    if st.button("Hapus semua transaksi", type="secondary"):
        st.session_state.confirm_delete = True
    if st.session_state.get("confirm_delete"):
        st.error("Tindakan ini tidak bisa dibatalkan. Unduh backup terlebih dahulu.")
        if st.button("Saya yakin, hapus semua transaksi"):
            from database import delete_all_transactions
            delete_all_transactions()
            st.session_state.confirm_delete = False
            refresh()

st.markdown("---")
st.caption("RuangUang · Versi awal · Simpan backup secara berkala.")
