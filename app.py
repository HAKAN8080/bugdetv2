import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from budget_forecast import BudgetForecaster
import numpy as np
import tempfile
import os

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="2026 Satış Bütçe Tahmini",
    page_icon="📊",
    layout="wide"
)

# CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">📊 2026 Satış Bütçe Tahmini Sistemi</p>', unsafe_allow_html=True)

# Sidebar - Sadeleştirilmiş
st.sidebar.header("⚙️ Temel Parametreler")

# 1. FILE UPLOAD
st.sidebar.subheader("📂 Veri Yükleme")
uploaded_file = st.sidebar.file_uploader(
    "Excel Dosyası Yükle",
    type=['xlsx'],
    help="2024-2025 verilerini içeren Excel dosyası"
)

# Veri yükleme
@st.cache_data
def load_data(file_path):
    return BudgetForecaster(file_path)

forecaster = None
if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    with st.spinner('Veri yükleniyor...'):
        forecaster = load_data(tmp_path)
    
    os.unlink(tmp_path)

# Eğer dosya yüklenmemişse bilgi göster ve dur
if forecaster is None:
    st.info("👆 Lütfen soldaki menüden Excel dosyanızı yükleyin.")
    st.markdown("""
    ### 📋 Nasıl Kullanılır?
    1. Sol taraftaki **"📂 Veri Yükleme"** bölümünden Excel dosyanızı yükleyin
    2. **"Parametre Ayarları"** sekmesinden hedeflerinizi belirleyin:
       - Ay bazında büyüme hedefleri
       - Ana grup bazında hedefler
       - Alınan dersleri (tecrübelerinizi) girin
    3. **"Tahmin Sonuçları"** sekmesinde sonuçları görün
    """)
    st.stop()

# Dosya yüklendiyse ana grupları al
main_groups = sorted(forecaster.data['MainGroup'].unique().tolist())

# Sidebar - Genel parametreler
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Genel Büyüme Hedefi")
general_growth = st.sidebar.slider(
    "Varsayılan Büyüme (%)",
    min_value=-20.0,
    max_value=50.0,
    value=15.0,
    step=1.0,
    help="Özel hedef girilmemiş ay/gruplara uygulanır"
) / 100

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Karlılık Hedefi")
margin_improvement = st.sidebar.slider(
    "Brüt Marj İyileşme (puan)",
    min_value=-5.0,
    max_value=10.0,
    value=2.0,
    step=0.5,
    help="Mevcut brüt marj üzerine eklenecek puan"
) / 100

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Stok Hedefi")
stock_param_type = st.sidebar.radio(
    "Stok Parametresi",
    ["Stok/SMM Oranı", "Stok Tutar Değişimi"],
    index=0,
    help="Stok hedefini oran veya tutar bazında belirle"
)

if stock_param_type == "Stok/SMM Oranı":
    stock_ratio_target = st.sidebar.slider(
        "Hedef Stok/SMM Oranı",
        min_value=0.3,
        max_value=2.0,
        value=0.8,
        step=0.1,
        help="Stok tutarı / Satılan Malın Maliyeti oranı"
    )
    stock_change_pct = None
else:
    stock_change_pct = st.sidebar.slider(
        "Stok Tutar Değişimi (%)",
        min_value=-50.0,
        max_value=100.0,
        value=0.0,
        step=5.0,
        help="2025'e göre stok tutarında % artış veya azalış"
    ) / 100
    stock_ratio_target = None

# Session state'de tabloları sakla
if 'monthly_targets' not in st.session_state:
    st.session_state.monthly_targets = pd.DataFrame({
        'Ay': list(range(1, 13)),
        'Ay Adı': ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                   'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'],
        'Hedef (%)': [15.0] * 12
    })

if 'maingroup_targets' not in st.session_state:
    st.session_state.maingroup_targets = pd.DataFrame({
        'Ana Grup': main_groups,
        'Hedef (%)': [15.0] * len(main_groups)
    })

if 'lessons_learned' not in st.session_state:
    # Ay × Ana Grup matrisi - default 0
    lessons_data = {'Ana Grup': main_groups}
    for month in range(1, 13):
        lessons_data[str(month)] = [0] * len(main_groups)
    st.session_state.lessons_learned = pd.DataFrame(lessons_data)

# Geçici düzenleme dataları (kaydedilmemiş değişiklikler)
if 'monthly_targets_temp' not in st.session_state:
    st.session_state.monthly_targets_temp = st.session_state.monthly_targets.copy()

if 'maingroup_targets_temp' not in st.session_state:
    st.session_state.maingroup_targets_temp = st.session_state.maingroup_targets.copy()

if 'lessons_learned_temp' not in st.session_state:
    st.session_state.lessons_learned_temp = st.session_state.lessons_learned.copy()

# ANA SEKMELER
main_tabs = st.tabs(["⚙️ Parametre Ayarları", "📊 Tahmin Sonuçları", "📋 Detay Veriler"])

# ==================== PARAMETRE AYARLARI TAB ====================
with main_tabs[0]:
    st.markdown("## ⚙️ Tahmin Parametrelerini Ayarlayın")
    
    # Genel kaydedilmemiş değişiklik kontrolü
    has_unsaved_monthly = not st.session_state.monthly_targets.equals(st.session_state.monthly_targets_temp)
    has_unsaved_maingroup = not st.session_state.maingroup_targets.equals(st.session_state.maingroup_targets_temp)
    has_unsaved_lessons = not st.session_state.lessons_learned.equals(st.session_state.lessons_learned_temp)
    
    total_unsaved = sum([has_unsaved_monthly, has_unsaved_maingroup, has_unsaved_lessons])
    
    if total_unsaved > 0:
        st.error(f"⚠️ **{total_unsaved} tabloda kaydedilmemiş değişiklikler var!** Lütfen değişikliklerinizi kaydedin veya iptal edin.")
    
    param_tabs = st.tabs(["📅 Ay Bazında Hedefler", "🏪 Ana Grup Hedefleri", "📚 Alınan Dersler"])
    
    # --- AY BAZINDA HEDEFLER ---
    with param_tabs[0]:
        st.markdown("### 📅 Ay Bazında Büyüme Hedefleri")
        st.caption("Her ay için büyüme hedefini ayarlayın. Bu hedef tüm ana gruplar için uygulanır.")
        
        # Değişiklik kontrolü
        has_changes_monthly = not st.session_state.monthly_targets.equals(st.session_state.monthly_targets_temp)
        
        if has_changes_monthly:
            st.warning("⚠️ Kaydedilmemiş değişiklikler var!")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            edited_monthly = st.data_editor(
                st.session_state.monthly_targets_temp,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Ay': st.column_config.NumberColumn('Ay', disabled=True),
                    'Ay Adı': st.column_config.TextColumn('Ay Adı', disabled=True),
                    'Hedef (%)': st.column_config.NumberColumn(
                        'Hedef (%)',
                        min_value=-20.0,
                        max_value=50.0,
                        step=1.0,
                        format="%.1f"
                    )
                },
                key='monthly_editor'
            )
            st.session_state.monthly_targets_temp = edited_monthly
            
            # Kaydet/İptal butonları
            col_save, col_cancel = st.columns(2)
            
            with col_save:
                if st.button("💾 Kaydet", key='save_monthly', type='primary', disabled=not has_changes_monthly, use_container_width=True):
                    st.session_state.monthly_targets = st.session_state.monthly_targets_temp.copy()
                    st.success("✅ Ay bazında hedefler kaydedildi!")
                    st.rerun()
            
            with col_cancel:
                if st.button("↺ İptal Et", key='cancel_monthly', disabled=not has_changes_monthly, use_container_width=True):
                    st.session_state.monthly_targets_temp = st.session_state.monthly_targets.copy()
                    st.info("🔄 Değişiklikler iptal edildi")
                    st.rerun()
        
        with col2:
            st.markdown("#### 🔧 Hızlı İşlemler")
            
            if st.button("↺ Varsayılana Dön", key='reset_monthly'):
                st.session_state.monthly_targets_temp['Hedef (%)'] = general_growth * 100
                st.rerun()
            
            if st.button("⊕ Tümünü +5%", key='inc_monthly'):
                st.session_state.monthly_targets_temp['Hedef (%)'] = st.session_state.monthly_targets_temp['Hedef (%)'] + 5
                st.rerun()
            
            if st.button("⊖ Tümünü -5%", key='dec_monthly'):
                st.session_state.monthly_targets_temp['Hedef (%)'] = st.session_state.monthly_targets_temp['Hedef (%)'] - 5
                st.rerun()
            
            avg_monthly = st.session_state.monthly_targets_temp['Hedef (%)'].mean()
            st.metric("Ortalama", f"%{avg_monthly:.1f}")
    
    # --- ANA GRUP HEDEFLERİ ---
    with param_tabs[1]:
        st.markdown("### 🏪 Ana Grup Bazında Büyüme Hedefleri")
        st.caption("Her ana grup için büyüme hedefini ayarlayın. Bu hedef tüm aylar için uygulanır.")
        
        # Değişiklik kontrolü
        has_changes_maingroup = not st.session_state.maingroup_targets.equals(st.session_state.maingroup_targets_temp)
        
        if has_changes_maingroup:
            st.warning("⚠️ Kaydedilmemiş değişiklikler var!")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            edited_maingroup = st.data_editor(
                st.session_state.maingroup_targets_temp,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    'Ana Grup': st.column_config.TextColumn('Ana Grup', disabled=True),
                    'Hedef (%)': st.column_config.NumberColumn(
                        'Hedef (%)',
                        min_value=-20.0,
                        max_value=50.0,
                        step=1.0,
                        format="%.1f"
                    )
                },
                key='maingroup_editor'
            )
            st.session_state.maingroup_targets_temp = edited_maingroup
            
            # Kaydet/İptal butonları
            col_save, col_cancel = st.columns(2)
            
            with col_save:
                if st.button("💾 Kaydet", key='save_maingroup', type='primary', disabled=not has_changes_maingroup, use_container_width=True):
                    st.session_state.maingroup_targets = st.session_state.maingroup_targets_temp.copy()
                    st.success("✅ Ana grup hedefleri kaydedildi!")
                    st.rerun()
            
            with col_cancel:
                if st.button("↺ İptal Et", key='cancel_maingroup', disabled=not has_changes_maingroup, use_container_width=True):
                    st.session_state.maingroup_targets_temp = st.session_state.maingroup_targets.copy()
                    st.info("🔄 Değişiklikler iptal edildi")
                    st.rerun()
        
        with col2:
            st.markdown("#### 🔧 Hızlı İşlemler")
            
            if st.button("↺ Varsayılana Dön", key='reset_maingroup'):
                st.session_state.maingroup_targets_temp['Hedef (%)'] = general_growth * 100
                st.rerun()
            
            if st.button("⊕ Tümünü +5%", key='inc_maingroup'):
                st.session_state.maingroup_targets_temp['Hedef (%)'] = st.session_state.maingroup_targets_temp['Hedef (%)'] + 5
                st.rerun()
            
            if st.button("⊖ Tümünü -5%", key='dec_maingroup'):
                st.session_state.maingroup_targets_temp['Hedef (%)'] = st.session_state.maingroup_targets_temp['Hedef (%)'] - 5
                st.rerun()
            
            avg_maingroup = st.session_state.maingroup_targets_temp['Hedef (%)'].mean()
            st.metric("Ortalama", f"%{avg_maingroup:.1f}")
    
    # --- ALINAN DERSLER ---
    with param_tabs[2]:
        st.markdown("### 📚 Alınan Dersler (Tecrübe Matrisi)")
        st.caption("Geçmiş deneyimlerinizi -10 ile +10 arası puan vererek girin. Her puan ~%2 etki yapar (max ±%20).")
        
        # Değişiklik kontrolü
        has_changes_lessons = not st.session_state.lessons_learned.equals(st.session_state.lessons_learned_temp)
        
        if has_changes_lessons:
            st.warning("⚠️ Kaydedilmemiş değişiklikler var!")
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Ay isimleri için sütun config
            month_names = {1: 'Oca', 2: 'Şub', 3: 'Mar', 4: 'Nis', 5: 'May', 6: 'Haz',
                          7: 'Tem', 8: 'Ağu', 9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'}
            
            column_config = {
                'Ana Grup': st.column_config.TextColumn('Ana Grup', disabled=True, width='medium')
            }
            
            for month in range(1, 13):
                column_config[str(month)] = st.column_config.NumberColumn(
                    month_names[month],
                    min_value=-10,
                    max_value=10,
                    step=1,
                    format="%d",
                    width='small'
                )
            
            edited_lessons = st.data_editor(
                st.session_state.lessons_learned_temp,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config=column_config,
                key='lessons_editor'
            )
            st.session_state.lessons_learned_temp = edited_lessons
            
            # Kaydet/İptal butonları
            col_save, col_cancel = st.columns(2)
            
            with col_save:
                if st.button("💾 Kaydet", key='save_lessons', type='primary', disabled=not has_changes_lessons, use_container_width=True):
                    st.session_state.lessons_learned = st.session_state.lessons_learned_temp.copy()
                    st.success("✅ Alınan dersler kaydedildi!")
                    st.rerun()
            
            with col_cancel:
                if st.button("↺ İptal Et", key='cancel_lessons', disabled=not has_changes_lessons, use_container_width=True):
                    st.session_state.lessons_learned_temp = st.session_state.lessons_learned.copy()
                    st.info("🔄 Değişiklikler iptal edildi")
                    st.rerun()
        
        with col2:
            st.markdown("#### 🔧 Hızlı İşlemler")
            
            if st.button("↺ Tümünü Sıfırla", key='reset_lessons'):
                for month in range(1, 13):
                    st.session_state.lessons_learned_temp[str(month)] = 0
                st.rerun()
            
            # İstatistikler - kaydedilmiş veriden
            total_adjustments = 0
            for month in range(1, 13):
                total_adjustments += st.session_state.lessons_learned[str(month)].abs().sum()
            
            st.metric("Toplam Düzeltme", f"{total_adjustments:.0f}")
            
            positive_count = 0
            negative_count = 0
            for month in range(1, 13):
                positive_count += (st.session_state.lessons_learned[str(month)] > 0).sum()
                negative_count += (st.session_state.lessons_learned[str(month)] < 0).sum()
            
            st.metric("Pozitif (+)", f"{positive_count}")
            st.metric("Negatif (-)", f"{negative_count}")
        
        # Açıklayıcı örnekler
        st.markdown("---")
        st.markdown("#### 💡 Örnek Kullanım Senaryoları")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success("**+5 puan** → ~%10 artış")
            st.caption("Örnek: Ocak/Çaydanlık'ta stok yetersizdi, talep karşılanamadı")
        
        with col2:
            st.error("**-3 puan** → ~%6 azalış")
            st.caption("Örnek: Şubat/Kozmetik'te çok indirimle satıldı, marj düştü")
        
        with col3:
            st.info("**0 puan** → Değişiklik yok")
            st.caption("Normal seyir, özel bir durum olmadı")

# ==================== TAHMİN HESAPLAMA ====================
# Kaydedilmemiş değişiklik kontrolü
has_unsaved_changes = (
    not st.session_state.monthly_targets.equals(st.session_state.monthly_targets_temp) or
    not st.session_state.maingroup_targets.equals(st.session_state.maingroup_targets_temp) or
    not st.session_state.lessons_learned.equals(st.session_state.lessons_learned_temp)
)

if has_unsaved_changes:
    st.warning("⚠️ **Parametrelerde kaydedilmemiş değişiklikler var!** Tahmin kaydedilmiş parametreler ile yapılacak. Yeni değişiklikleri görmek için lütfen kaydedin.")

# Parametreleri hazırla (KAYDEDİLMİŞ verilerden)
monthly_growth_targets = {}
for _, row in st.session_state.monthly_targets.iterrows():
    monthly_growth_targets[int(row['Ay'])] = row['Hedef (%)'] / 100

maingroup_growth_targets = {}
for _, row in st.session_state.maingroup_targets.iterrows():
    maingroup_growth_targets[row['Ana Grup']] = row['Hedef (%)'] / 100

# Alınan dersleri dict formatına çevir (KAYDEDİLMİŞ veriden)
lessons_learned_dict = {}
for _, row in st.session_state.lessons_learned.iterrows():
    main_group = row['Ana Grup']
    for month in range(1, 13):
        lessons_learned_dict[(main_group, month)] = row[str(month)]

# Tahmin yap
with st.spinner('Tahmin hesaplanıyor...'):
    full_data = forecaster.get_full_data_with_forecast(
        growth_param=general_growth,
        margin_improvement=margin_improvement,
        stock_ratio_target=stock_ratio_target,
        stock_change_pct=stock_change_pct,
        monthly_growth_targets=monthly_growth_targets,
        maingroup_growth_targets=maingroup_growth_targets,
        lessons_learned=lessons_learned_dict
    )
    
    summary = forecaster.get_summary_stats(full_data)
    quality_metrics = forecaster.get_forecast_quality_metrics(full_data)

# ==================== TAHMİN SONUÇLARI TAB ====================
with main_tabs[1]:
    st.markdown("## 📈 Özet Metrikler")
    
    # İLK SATIR - Ana Metrikler
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sales_2026 = summary[2026]['Total_Sales']
        sales_2025 = summary[2025]['Total_Sales']
        sales_growth = ((sales_2026 - sales_2025) / sales_2025 * 100) if sales_2025 > 0 else 0
        
        st.metric(
            label="2026 Toplam Satış",
            value=f"₺{sales_2026:,.0f}",
            delta=f"%{sales_growth:.1f} vs 2025"
        )
    
    with col2:
        margin_2026 = summary[2026]['Avg_GrossMargin%']
        margin_2025 = summary[2025]['Avg_GrossMargin%']
        margin_change = margin_2026 - margin_2025
        
        st.metric(
            label="2026 Brüt Marj",
            value=f"%{margin_2026:.1f}",
            delta=f"{margin_change:+.1f} puan"
        )
    
    with col3:
        gp_2026 = summary[2026]['Total_GrossProfit']
        gp_2025 = summary[2025]['Total_GrossProfit']
        gp_growth = ((gp_2026 - gp_2025) / gp_2025 * 100) if gp_2025 > 0 else 0
        
        st.metric(
            label="2026 Brüt Kar",
            value=f"₺{gp_2026:,.0f}",
            delta=f"%{gp_growth:.1f} vs 2025"
        )
    
    with col4:
        if stock_change_pct is not None:
            stock_2026 = summary[2026]['Avg_Stock']
            stock_2025 = summary[2025]['Avg_Stock']
            stock_change = ((stock_2026 - stock_2025) / stock_2025 * 100) if stock_2025 > 0 else 0
            
            st.metric(
                label="2026 Ort. Stok",
                value=f"₺{stock_2026:,.0f}",
                delta=f"%{stock_change:+.1f} vs 2025"
            )
        else:
            stock_weekly_2026 = summary[2026]['Avg_Stock_COGS_Weekly']
            stock_weekly_2025 = summary[2025]['Avg_Stock_COGS_Weekly']
            weekly_change = stock_weekly_2026 - stock_weekly_2025
            
            st.metric(
                label="2026 Stok/SMM (Haftalık)",
                value=f"{stock_weekly_2026:.2f} hafta",
                delta=f"{weekly_change:+.2f} hafta vs 2025"
            )
            st.caption("Stok / (Aylık SMM ÷ gün × 7)")
    
    # İKİNCİ SATIR - Tahmin Kalite Metrikleri
    st.markdown("### 🎯 Tahmin Güvenilirlik Göstergeleri")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if quality_metrics['r2_score'] is not None:
            r2_pct = quality_metrics['r2_score'] * 100
            
            if r2_pct > 80:
                indicator = "🟢 Çok İyi"
            elif r2_pct > 60:
                indicator = "🟡 İyi"
            elif r2_pct > 40:
                indicator = "🟠 Orta"
            else:
                indicator = "🔴 Zayıf"
            
            st.metric(
                label="Model Uyumu",
                value=indicator,
                help="2024-2025 trend tutarlılığı"
            )
        else:
            st.metric(label="Model Uyumu", value="⚪ Hesaplanamadı")
    
    with col2:
        if quality_metrics['trend_consistency'] is not None:
            consistency_pct = quality_metrics['trend_consistency'] * 100
            
            if consistency_pct > 80:
                indicator = "🟢 Çok İstikrarlı"
            elif consistency_pct > 60:
                indicator = "🟡 İstikrarlı"
            elif consistency_pct > 40:
                indicator = "🟠 Değişken"
            else:
                indicator = "🔴 Çok Değişken"
            
            st.metric(
                label="Trend İstikrarı",
                value=indicator,
                help="Aylık büyüme oranlarının tutarlılığı"
            )
        else:
            st.metric(label="Trend İstikrarı", value="⚪ Hesaplanamadı")
    
    with col3:
        if quality_metrics['mape'] is not None:
            mape = quality_metrics['mape']
            
            if mape < 15:
                indicator = "🟢 Düşük Hata"
            elif mape < 25:
                indicator = "🟡 Kabul Edilebilir"
            elif mape < 35:
                indicator = "🟠 Yüksek Hata"
            else:
                indicator = "🔴 Çok Yüksek Hata"
            
            st.metric(
                label="Tahmin Hatası",
                value=indicator,
                help="Ortalama sapma oranı"
            )
        else:
            st.metric(label="Tahmin Hatası", value="⚪ Hesaplanamadı")
    
    with col4:
        confidence = quality_metrics['confidence_level']
        
        if confidence == 'Yüksek':
            overall = "🟢 Güvenilir"
        elif confidence == 'Orta':
            overall = "🟡 Makul"
        else:
            overall = "🟠 Dikkatli Kullan"
        
        st.metric(
            label="Genel Değerlendirme",
            value=overall,
            help="Tüm metriklerin ortalaması"
        )
        
        if quality_metrics['avg_growth_2024_2025']:
            st.caption(f"📈 2024→2025 Büyüme: %{quality_metrics['avg_growth_2024_2025']:.1f}")
    
    st.markdown("---")
    
    # GRAFIKLER
    result_tabs = st.tabs(["📊 Aylık Trend", "🎯 Ana Grup Analizi", "📅 Yıllık Karşılaştırma"])
    
    with result_tabs[0]:
        st.subheader("Aylık Satış Trendi (2024-2026)")
        
        monthly_sales = full_data.groupby(['Year', 'Month'])['Sales'].sum().reset_index()
        
        fig = go.Figure()
        
        for year in [2024, 2025, 2026]:
            year_data = monthly_sales[monthly_sales['Year'] == year]
            
            line_style = 'solid' if year < 2026 else 'dash'
            line_width = 2 if year < 2026 else 3
            
            fig.add_trace(go.Scatter(
                x=year_data['Month'],
                y=year_data['Sales'],
                mode='lines+markers',
                name=f'{year}' + (' (Tahmin)' if year == 2026 else ''),
                line=dict(dash=line_style, width=line_width),
                marker=dict(size=8)
            ))
        
        fig.update_layout(
            title="Aylık Satış Karşılaştırması",
            xaxis_title="Ay",
            yaxis_title="Satış (TRY)",
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Brüt Marj Trendi
        st.subheader("Aylık Brüt Marj % Trendi")
        
        monthly_margin = full_data.groupby(['Year', 'Month']).apply(
            lambda x: (x['GrossProfit'].sum() / x['Sales'].sum() * 100) if x['Sales'].sum() > 0 else 0
        ).reset_index(name='Margin%')
        
        fig2 = go.Figure()
        
        for year in [2024, 2025, 2026]:
            year_data = monthly_margin[monthly_margin['Year'] == year]
            
            line_style = 'solid' if year < 2026 else 'dash'
            
            fig2.add_trace(go.Scatter(
                x=year_data['Month'],
                y=year_data['Margin%'],
                mode='lines+markers',
                name=f'{year}' + (' (Tahmin)' if year == 2026 else ''),
                line=dict(dash=line_style),
                marker=dict(size=8)
            ))
        
        fig2.update_layout(
            title="Aylık Brüt Marj % Karşılaştırması",
            xaxis_title="Ay",
            yaxis_title="Brüt Marj %",
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    with result_tabs[1]:
        st.subheader("Ana Grup Bazında Performans")
        
        group_sales = full_data.groupby(['Year', 'MainGroup'])['Sales'].sum().reset_index()
        
        top_groups_2026 = group_sales[group_sales['Year'] == 2026].nlargest(10, 'Sales')['MainGroup'].tolist()
        
        group_sales_filtered = group_sales[group_sales['MainGroup'].isin(top_groups_2026)]
        
        fig3 = px.bar(
            group_sales_filtered,
            x='MainGroup',
            y='Sales',
            color='Year',
            barmode='group',
            title='Top 10 Ana Grup - Yıllık Satış Karşılaştırması'
        )
        
        fig3.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)
        
        # Büyüme analizi
        st.subheader("Ana Grup Büyüme Analizi (2025 → 2026)")
        
        sales_2025 = group_sales[group_sales['Year'] == 2025][['MainGroup', 'Sales']]
        sales_2025.columns = ['MainGroup', 'Sales_2025']
        
        sales_2026_grp = group_sales[group_sales['Year'] == 2026][['MainGroup', 'Sales']]
        sales_2026_grp.columns = ['MainGroup', 'Sales_2026']
        
        growth_analysis = sales_2025.merge(sales_2026_grp, on='MainGroup')
        growth_analysis['Growth%'] = ((growth_analysis['Sales_2026'] - growth_analysis['Sales_2025']) / 
                                       growth_analysis['Sales_2025'] * 100)
        growth_analysis = growth_analysis.sort_values('Growth%', ascending=False)
        
        fig4 = px.bar(
            growth_analysis.head(15),
            x='MainGroup',
            y='Growth%',
            title='Top 15 Ana Grup - Büyüme Oranı',
            color='Growth%',
            color_continuous_scale='RdYlGn'
        )
        
        fig4.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig4, use_container_width=True)
    
    with result_tabs[2]:
        st.subheader("Yıllık Toplam Karşılaştırma")
        
        col1, col2 = st.columns(2)
        
        with col1:
            yearly_summary = pd.DataFrame({
                'Yıl': [2024, 2025, 2026],
                'Satış': [summary[2024]['Total_Sales'], 
                         summary[2025]['Total_Sales'],
                         summary[2026]['Total_Sales']],
                'Brüt Kar': [summary[2024]['Total_GrossProfit'],
                            summary[2025]['Total_GrossProfit'],
                            summary[2026]['Total_GrossProfit']]
            })
            
            fig5 = go.Figure()
            fig5.add_trace(go.Bar(name='Satış', x=yearly_summary['Yıl'], y=yearly_summary['Satış']))
            fig5.add_trace(go.Bar(name='Brüt Kar', x=yearly_summary['Yıl'], y=yearly_summary['Brüt Kar']))
            
            fig5.update_layout(
                title='Yıllık Satış ve Brüt Kar',
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig5, use_container_width=True)
        
        with col2:
            yearly_margin = pd.DataFrame({
                'Yıl': [2024, 2025, 2026],
                'Brüt Marj %': [summary[2024]['Avg_GrossMargin%'],
                               summary[2025]['Avg_GrossMargin%'],
                               summary[2026]['Avg_GrossMargin%']]
            })
            
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(
                x=yearly_margin['Yıl'],
                y=yearly_margin['Brüt Marj %'],
                mode='lines+markers',
                line=dict(width=3),
                marker=dict(size=12)
            ))
            
            fig6.update_layout(
                title='Yıllık Brüt Marj %',
                height=400,
                yaxis_title='Brüt Marj %'
            )
            
            st.plotly_chart(fig6, use_container_width=True)
        
        st.subheader("Yıllık Özet Tablo")
        
        summary_table = pd.DataFrame({
            'Metrik': ['Toplam Satış (TRY)', 'Toplam Brüt Kar (TRY)', 
                      'Brüt Marj %', 'Ort. Stok (TRY)', 'Stok/SMM Oranı'],
            '2024': [
                f"₺{summary[2024]['Total_Sales']:,.0f}",
                f"₺{summary[2024]['Total_GrossProfit']:,.0f}",
                f"%{summary[2024]['Avg_GrossMargin%']:.2f}",
                f"₺{summary[2024]['Avg_Stock']:,.0f}",
                f"{summary[2024]['Avg_Stock_COGS_Ratio']:.2f}"
            ],
            '2025': [
                f"₺{summary[2025]['Total_Sales']:,.0f}",
                f"₺{summary[2025]['Total_GrossProfit']:,.0f}",
                f"%{summary[2025]['Avg_GrossMargin%']:.2f}",
                f"₺{summary[2025]['Avg_Stock']:,.0f}",
                f"{summary[2025]['Avg_Stock_COGS_Ratio']:.2f}"
            ],
            '2026 (Tahmin)': [
                f"₺{summary[2026]['Total_Sales']:,.0f}",
                f"₺{summary[2026]['Total_GrossProfit']:,.0f}",
                f"%{summary[2026]['Avg_GrossMargin%']:.2f}",
                f"₺{summary[2026]['Avg_Stock']:,.0f}",
                f"{summary[2026]['Avg_Stock_COGS_Ratio']:.2f}"
            ]
        })
        
        st.dataframe(summary_table, use_container_width=True, hide_index=True)

# ==================== DETAY VERİLER TAB ====================
with main_tabs[2]:
    st.subheader("Detaylı Veri Tablosu - Yan Yana Karşılaştırma")
    
    selected_month = st.selectbox("Ay Seçin", list(range(1, 13)), format_func=lambda x: f"{x}. Ay")
    
    data_2024 = full_data[(full_data['Year'] == 2024) & (full_data['Month'] == selected_month)].copy()
    data_2025 = full_data[(full_data['Year'] == 2025) & (full_data['Month'] == selected_month)].copy()
    data_2026 = full_data[(full_data['Year'] == 2026) & (full_data['Month'] == selected_month)].copy()
    
    days_in_month = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                     7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    days = days_in_month[selected_month]
    
    comparison = data_2024[['MainGroup', 'Sales', 'GrossMargin%', 'Stock', 'COGS']].rename(
        columns={
            'Sales': 'Satış_2024',
            'GrossMargin%': 'BM%_2024',
            'Stock': 'Stok_2024',
            'COGS': 'SMM_2024'
        }
    )
    
    comparison = comparison.merge(
        data_2025[['MainGroup', 'Sales', 'GrossMargin%', 'Stock', 'COGS']].rename(
            columns={
                'Sales': 'Satış_2025',
                'GrossMargin%': 'BM%_2025',
                'Stock': 'Stok_2025',
                'COGS': 'SMM_2025'
            }
        ),
        on='MainGroup',
        how='outer'
    )
    
    comparison = comparison.merge(
        data_2026[['MainGroup', 'Sales', 'GrossMargin%', 'Stock', 'COGS']].rename(
            columns={
                'Sales': 'Satış_2026',
                'GrossMargin%': 'BM%_2026',
                'Stock': 'Stok_2026',
                'COGS': 'SMM_2026'
            }
        ),
        on='MainGroup',
        how='outer'
    )
    
    comparison = comparison.fillna(0)
    
    comparison['Stok/SMM_Haftalık_2024'] = np.where(
        comparison['SMM_2024'] > 0,
        comparison['Stok_2024'] / ((comparison['SMM_2024'] / days) * 7),
        0
    )
    comparison['Stok/SMM_Haftalık_2025'] = np.where(
        comparison['SMM_2025'] > 0,
        comparison['Stok_2025'] / ((comparison['SMM_2025'] / days) * 7),
        0
    )
    comparison['Stok/SMM_Haftalık_2026'] = np.where(
        comparison['SMM_2026'] > 0,
        comparison['Stok_2026'] / ((comparison['SMM_2026'] / days) * 7),
        0
    )
    
    display_df = comparison.copy()
    
    for col in ['Satış_2024', 'Stok_2024', 'SMM_2024', 'Satış_2025', 'Stok_2025', 'SMM_2025', 
                'Satış_2026', 'Stok_2026', 'SMM_2026']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"₺{x:,.0f}" if x > 0 else "-")
    
    for col in ['BM%_2024', 'BM%_2025', 'BM%_2026']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"%{x*100:.1f}" if x > 0 else "-")
    
    for col in ['Stok/SMM_Haftalık_2024', 'Stok/SMM_Haftalık_2025', 'Stok/SMM_Haftalık_2026']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if x > 0 else "-")
    
    display_df = display_df[[
        'MainGroup',
        'Satış_2024', 'Satış_2025', 'Satış_2026',
        'BM%_2024', 'BM%_2025', 'BM%_2026',
        'Stok_2024', 'Stok_2025', 'Stok_2026',
        'SMM_2024', 'SMM_2025', 'SMM_2026',
        'Stok/SMM_Haftalık_2024', 'Stok/SMM_Haftalık_2025', 'Stok/SMM_Haftalık_2026'
    ]]
    
    display_df.columns = [
        'Ana Grup',
        'Satış 2024', 'Satış 2025', 'Satış 2026',
        'BM% 2024', 'BM% 2025', 'BM% 2026',
        'Stok 2024', 'Stok 2025', 'Stok 2026',
        'SMM 2024', 'SMM 2025', 'SMM 2026',
        'Stok/SMM Hft. 2024', 'Stok/SMM Hft. 2025', 'Stok/SMM Hft. 2026'
    ]
    
    st.info(f"📅 {selected_month}. Ay ({days} gün) - Stok/SMM haftalık: (Stok / (SMM/{days})*7)")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    st.download_button(
        label="📥 CSV İndir (Sadece Bu Ay)",
        data=comparison.to_csv(index=False).encode('utf-8'),
        file_name=f'budget_comparison_month_{selected_month}.csv',
        mime='text/csv'
    )
    
    st.markdown("---")
    st.subheader("📊 Tam Bütçe Dosyası İndir")
    st.caption("Orijinal Excel + 2025 Aralık Tahmini + 2026 Tahmini")
    
    if st.button("🔄 Excel Dosyası Oluştur (Tüm Veriler)", type="primary"):
        with st.spinner("Excel dosyası hazırlanıyor..."):
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            from openpyxl.utils.dataframe import dataframe_to_rows
            from io import BytesIO
            
            data_2025_full = forecaster.data[forecaster.data['Year'] == 2025].copy()
            
            november_data = data_2025_full[data_2025_full['Month'] == 11].copy()
            december_estimate = november_data.copy()
            december_estimate['Month'] = 12
            december_estimate['Sales'] = december_estimate['Sales'] * 1.12
            december_estimate['GrossProfit'] = december_estimate['GrossProfit'] * 1.12
            december_estimate['COGS'] = december_estimate['COGS'] * 1.12
            december_estimate['Stock'] = december_estimate['Stock'] * 1.05
            
            data_2025_complete = pd.concat([data_2025_full[data_2025_full['Month'] != 12], december_estimate], ignore_index=True)
            data_2025_complete = data_2025_complete.sort_values(['Month', 'MainGroup'])
            
            data_2026 = full_data[full_data['Year'] == 2026].copy()
            
            wb = openpyxl.Workbook()
            wb.remove(wb.active)
            
            ws_2024 = wb.create_sheet("2024")
            data_2024 = forecaster.data[forecaster.data['Year'] == 2024].copy()
            
            ws_2025 = wb.create_sheet("2025")
            ws_2026 = wb.create_sheet("2026_Tahmin")
            
            for ws, data, year_name in [(ws_2024, data_2024, "2024"), 
                                         (ws_2025, data_2025_complete, "2025"), 
                                         (ws_2026, data_2026, "2026")]:
                
                excel_data = pd.DataFrame()
                
                for month in range(1, 13):
                    month_data = data[data['Month'] == month].copy()
                    
                    if len(month_data) > 0:
                        total_row = pd.DataFrame({
                            'Ay': [f'Toplam {month}'],
                            'Ana Grup': [''],
                            'Satış': [month_data['Sales'].sum()],
                            'Brüt Kar': [month_data['GrossProfit'].sum()],
                            'Brüt Marj %': [month_data['GrossProfit'].sum() / month_data['Sales'].sum() if month_data['Sales'].sum() > 0 else 0],
                            'Stok': [month_data['Stock'].mean()],
                            'SMM': [month_data['COGS'].sum()]
                        })
                        
                        month_formatted = month_data[['Month', 'MainGroup', 'Sales', 'GrossProfit', 'GrossMargin%', 'Stock', 'COGS']].copy()
                        month_formatted.columns = ['Ay', 'Ana Grup', 'Satış', 'Brüt Kar', 'Brüt Marj %', 'Stok', 'SMM']
                        
                        month_data_with_total = pd.concat([month_formatted, total_row], ignore_index=True)
                        excel_data = pd.concat([excel_data, month_data_with_total], ignore_index=True)
                
                for r_idx, row in enumerate(dataframe_to_rows(excel_data, index=False, header=True), 1):
                    for c_idx, value in enumerate(row, 1):
                        cell = ws.cell(row=r_idx, column=c_idx, value=value)
                        
                        if r_idx == 1:
                            cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
                            cell.font = Font(color="FFFFFF", bold=True)
                            cell.alignment = Alignment(horizontal='center')
                        
                        if isinstance(value, str) and value.startswith('Toplam'):
                            cell.font = Font(bold=True)
                            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
                        
                        if r_idx > 1:
                            if c_idx in [3, 4, 6, 7]:
                                cell.number_format = '#,##0'
                            elif c_idx == 5:
                                cell.number_format = '0.00%'
                
                ws.column_dimensions['A'].width = 12
                ws.column_dimensions['B'].width = 25
                ws.column_dimensions['C'].width = 18
                ws.column_dimensions['D'].width = 18
                ws.column_dimensions['E'].width = 15
                ws.column_dimensions['F'].width = 18
                ws.column_dimensions['G'].width = 18
                
                if year_name == "2025":
                    ws.insert_rows(1)
                    ws['A1'] = f'{year_name} (Aralık Tahmini İçerir)'
                    ws['A1'].font = Font(size=14, bold=True, color="FF6B35")
                    ws.merge_cells('A1:G1')
                elif year_name == "2026":
                    ws.insert_rows(1)
                    ws['A1'] = f'{year_name} Tahmin'
                    ws['A1'].font = Font(size=14, bold=True, color="1E88E5")
                    ws.merge_cells('A1:G1')
            
            output = BytesIO()
            wb.save(output)
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Bütçe Dosyası İndir (3 Yıl - Excel)",
                data=excel_data,
                file_name="butce_2024_2025_2026_tam.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
            st.success("✅ Excel dosyası hazır! (2024 + 2025 Tamamlanmış + 2026 Tahmin)")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>2026 Satış Bütçe Tahmin Sistemi | Ay + Ana Grup + Alınan Dersler</p>
    </div>
""", unsafe_allow_html=True)
