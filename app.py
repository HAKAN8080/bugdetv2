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
    2. **"Parametre Ayarları"** sekmesinden hedeflerinizi belirleyin
    3. **"📊 Hesapla"** butonuna basın
    4. **"Tahmin Sonuçları"** sekmesinde sonuçları görün
    """)
    st.stop()

# Dosya yüklendiyse ana grupları al
main_groups = sorted(forecaster.data['MainGroup'].unique().tolist())

# Sidebar - Genel parametreler
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
stock_change_pct = st.sidebar.slider(
    "Stok Tutar Değişimi (%)",
    min_value=-50.0,
    max_value=100.0,
    value=0.0,
    step=5.0,
    help="2025'e göre stok tutarında % artış veya azalış. Her grup kendi stok/SMM oranını korur."
) / 100

# Session state - veri tabloları
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
    lessons_data = {'Ana Grup': main_groups}
    for month in range(1, 13):
        lessons_data[str(month)] = [0] * len(main_groups)
    st.session_state.lessons_learned = pd.DataFrame(lessons_data)

# Hesaplanmış tahmin sonuçları
if 'forecast_result' not in st.session_state:
    st.session_state.forecast_result = None

# ANA SEKMELER
main_tabs = st.tabs(["⚙️ Parametre Ayarları", "📊 Tahmin Sonuçları", "📋 Detay Veriler"])

# ==================== PARAMETRE AYARLARI TAB ====================
with main_tabs[0]:
    st.markdown("## ⚙️ Tahmin Parametrelerini Ayarlayın")
    st.info("💡 Parametreleri serbestçe düzenleyin. '📊 Hesapla' butonuna bastığınızda tahmin güncellenir.")
    
    param_tabs = st.tabs(["📅 Ay Bazında Hedefler", "🏪 Ana Grup Hedefleri", "📚 Alınan Dersler"])
    
    # --- AY BAZINDA HEDEFLER ---
    with param_tabs[0]:
        st.markdown("### 📅 Ay Bazında Büyüme Hedefleri")
        st.caption("Her ay için büyüme hedefini ayarlayın. Bu hedef tüm ana gruplar için uygulanır.")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            edited_monthly = st.data_editor(
                st.session_state.monthly_targets,
                use_container_width=True,
                hide_index=True,
                disabled=False,
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
            st.session_state.monthly_targets = edited_monthly
        
        with col2:
            st.markdown("#### 🔧 Hızlı İşlemler")
            
            if st.button("↺ Varsayılana Dön", key='reset_monthly'):
                st.session_state.monthly_targets['Hedef (%)'] = 15.0
                st.rerun()
            
            if st.button("⊕ Tümünü +5%", key='inc_monthly'):
                st.session_state.monthly_targets['Hedef (%)'] = st.session_state.monthly_targets['Hedef (%)'] + 5
                st.rerun()
            
            if st.button("⊖ Tümünü -5%", key='dec_monthly'):
                st.session_state.monthly_targets['Hedef (%)'] = st.session_state.monthly_targets['Hedef (%)'] - 5
                st.rerun()
            
            # Canlı istatistikler
            avg_monthly = st.session_state.monthly_targets['Hedef (%)'].mean()
            st.metric("📊 Ortalama", f"%{avg_monthly:.1f}")
            
            min_monthly = st.session_state.monthly_targets['Hedef (%)'].min()
            max_monthly = st.session_state.monthly_targets['Hedef (%)'].max()
            st.caption(f"Min: %{min_monthly:.1f} | Max: %{max_monthly:.1f}")
    
    # --- ANA GRUP HEDEFLERİ ---
    with param_tabs[1]:
        st.markdown("### 🏪 Ana Grup Bazında Büyüme Hedefleri")
        st.caption("Her ana grup için büyüme hedefini ayarlayın. Bu hedef tüm aylar için uygulanır.")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            edited_maingroup = st.data_editor(
                st.session_state.maingroup_targets,
                use_container_width=True,
                hide_index=True,
                disabled=False,
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
            st.session_state.maingroup_targets = edited_maingroup
        
        with col2:
            st.markdown("#### 🔧 Hızlı İşlemler")
            
            if st.button("↺ Varsayılana Dön", key='reset_maingroup'):
                st.session_state.maingroup_targets['Hedef (%)'] = 15.0
                st.rerun()
            
            if st.button("⊕ Tümünü +5%", key='inc_maingroup'):
                st.session_state.maingroup_targets['Hedef (%)'] = st.session_state.maingroup_targets['Hedef (%)'] + 5
                st.rerun()
            
            if st.button("⊖ Tümünü -5%", key='dec_maingroup'):
                st.session_state.maingroup_targets['Hedef (%)'] = st.session_state.maingroup_targets['Hedef (%)'] - 5
                st.rerun()
            
            # Canlı istatistikler
            avg_maingroup = st.session_state.maingroup_targets['Hedef (%)'].mean()
            st.metric("📊 Ortalama", f"%{avg_maingroup:.1f}")
            
            min_maingroup = st.session_state.maingroup_targets['Hedef (%)'].min()
            max_maingroup = st.session_state.maingroup_targets['Hedef (%)'].max()
            st.caption(f"Min: %{min_maingroup:.1f} | Max: %{max_maingroup:.1f}")
    
    # --- ALINAN DERSLER ---
    with param_tabs[2]:
        st.markdown("### 📚 Alınan Dersler (Tecrübe Matrisi)")
        st.caption("Geçmiş deneyimlerinizi -10 ile +10 arası puan vererek girin. Her puan ~%2 etki yapar (max ±%20).")
        
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
                st.session_state.lessons_learned,
                use_container_width=True,
                hide_index=True,
                disabled=False,
                height=400,
                column_config=column_config,
                key='lessons_editor'
            )
            st.session_state.lessons_learned = edited_lessons
        
        with col2:
            st.markdown("#### 🔧 Hızlı İşlemler")
            
            if st.button("↺ Tümünü Sıfırla", key='reset_lessons'):
                for month in range(1, 13):
                    st.session_state.lessons_learned[str(month)] = 0
                st.rerun()
            
            # Canlı istatistikler
            total_adjustments = 0
            for month in range(1, 13):
                total_adjustments += st.session_state.lessons_learned[str(month)].abs().sum()
            
            st.metric("📊 Toplam Düzeltme", f"{total_adjustments:.0f}")
            
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
    
    # --- BÜYÜK HESAPLA BUTONU ---
    st.markdown("---")
    st.markdown("### 🚀 Tahmini Hesapla")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("📊 Hesapla ve Sonuçları Göster", type='primary', use_container_width=True, key='calculate_forecast'):
            with st.spinner('Tahmin hesaplanıyor...'):
                # Parametreleri hazırla
                monthly_growth_targets = {}
                for _, row in st.session_state.monthly_targets.iterrows():
                    monthly_growth_targets[int(row['Ay'])] = row['Hedef (%)'] / 100
                
                maingroup_growth_targets = {}
                for _, row in st.session_state.maingroup_targets.iterrows():
                    maingroup_growth_targets[row['Ana Grup']] = row['Hedef (%)'] / 100
                
                # Alınan dersleri dict formatına çevir
                lessons_learned_dict = {}
                for _, row in st.session_state.lessons_learned.iterrows():
                    main_group = row['Ana Grup']
                    for month in range(1, 13):
                        lessons_learned_dict[(main_group, month)] = row[str(month)]
                
                # Genel büyüme parametresi - ay ve grup hedeflerinin ortalaması
                general_growth = (
                    st.session_state.monthly_targets['Hedef (%)'].mean() +
                    st.session_state.maingroup_targets['Hedef (%)'].mean()
                ) / 200  # İki ortalamayı birleştir ve yüzdeye çevir
                
                # Tahmin yap
                full_data = forecaster.get_full_data_with_forecast(
                    growth_param=general_growth,
                    margin_improvement=margin_improvement,
                    stock_change_pct=stock_change_pct,
                    monthly_growth_targets=monthly_growth_targets,
                    maingroup_growth_targets=maingroup_growth_targets,
                    lessons_learned=lessons_learned_dict
                )
                
                summary = forecaster.get_summary_stats(full_data)
                quality_metrics = forecaster.get_forecast_quality_metrics(full_data)
                
                # Sonuçları session state'e kaydet
                st.session_state.forecast_result = {
                    'full_data': full_data,
                    'summary': summary,
                    'quality_metrics': quality_metrics
                }
                
                st.success("✅ Tahmin başarıyla hesaplandı! 'Tahmin Sonuçları' sekmesine geçin.")

# ==================== TAHMİN SONUÇLARI TAB ====================
with main_tabs[1]:
    if st.session_state.forecast_result is None:
        st.warning("⚠️ Henüz tahmin hesaplanmadı. Lütfen 'Parametre Ayarları' sekmesinden parametreleri ayarlayıp '📊 Hesapla' butonuna basın.")
    else:
        full_data = st.session_state.forecast_result['full_data']
        summary = st.session_state.forecast_result['summary']
        quality_metrics = st.session_state.forecast_result['quality_metrics']
        
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
            # Stok metrikleri - artık sadece tutar bazlı
            stock_2026 = summary[2026]['Avg_Stock']
            stock_2025 = summary[2025]['Avg_Stock']
            stock_change = ((stock_2026 - stock_2025) / stock_2025 * 100) if stock_2025 > 0 else 0
            
            st.metric(
                label="2026 Ort. Stok",
                value=f"₺{stock_2026:,.0f}",
                delta=f"%{stock_change:+.1f} vs 2025"
            )
            
            # Haftalık oran da göster
            stock_weekly_2026 = summary[2026]['Avg_Stock_COGS_Weekly']
            st.caption(f"Stok/SMM: {stock_weekly_2026:.2f} hafta")
        
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
        
        # TABLAR
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
    if st.session_state.forecast_result is None:
        st.warning("⚠️ Önce tahmini hesaplayın.")
    else:
        full_data = st.session_state.forecast_result['full_data']
        
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
        
        # TOPLU CSV İNDİR - TÜM AYLAR VE GRUPLAR
        st.markdown("---")
        st.subheader("📊 Toplu Veri İndirme - Tüm Aylar")
        st.caption("2024, 2025 ve 2026 verilerinin tamamını ay ve ana grup detayında indirin")
        
        if st.button("🔄 Toplu CSV Hazırla", type="primary"):
            with st.spinner("CSV dosyası hazırlanıyor..."):
                # Tüm aylar için veri hazırla
                all_data = []
                
                for month in range(1, 13):
                    month_data_2024 = full_data[(full_data['Year'] == 2024) & (full_data['Month'] == month)].copy()
                    month_data_2025 = full_data[(full_data['Year'] == 2025) & (full_data['Month'] == month)].copy()
                    month_data_2026 = full_data[(full_data['Year'] == 2026) & (full_data['Month'] == month)].copy()
                    
                    # Birleştir
                    month_comparison = month_data_2024[['MainGroup', 'Sales', 'GrossProfit', 'GrossMargin%', 'Stock', 'COGS']].rename(
                        columns={
                            'Sales': 'Satis_2024',
                            'GrossProfit': 'BrutKar_2024',
                            'GrossMargin%': 'BrutMarj_2024',
                            'Stock': 'Stok_2024',
                            'COGS': 'SMM_2024'
                        }
                    )
                    
                    month_comparison = month_comparison.merge(
                        month_data_2025[['MainGroup', 'Sales', 'GrossProfit', 'GrossMargin%', 'Stock', 'COGS']].rename(
                            columns={
                                'Sales': 'Satis_2025',
                                'GrossProfit': 'BrutKar_2025',
                                'GrossMargin%': 'BrutMarj_2025',
                                'Stock': 'Stok_2025',
                                'COGS': 'SMM_2025'
                            }
                        ),
                        on='MainGroup',
                        how='outer'
                    )
                    
                    month_comparison = month_comparison.merge(
                        month_data_2026[['MainGroup', 'Sales', 'GrossProfit', 'GrossMargin%', 'Stock', 'COGS']].rename(
                            columns={
                                'Sales': 'Satis_2026',
                                'GrossProfit': 'BrutKar_2026',
                                'GrossMargin%': 'BrutMarj_2026',
                                'Stock': 'Stok_2026',
                                'COGS': 'SMM_2026'
                            }
                        ),
                        on='MainGroup',
                        how='outer'
                    )
                    
                    month_comparison = month_comparison.fillna(0)
                    month_comparison.insert(0, 'Ay', month)
                    
                    all_data.append(month_comparison)
                
                # Tüm ayları birleştir
                full_comparison = pd.concat(all_data, ignore_index=True)
                
                # Sütun sırası düzenle
                column_order = ['Ay', 'MainGroup',
                               'Satis_2024', 'Satis_2025', 'Satis_2026',
                               'BrutKar_2024', 'BrutKar_2025', 'BrutKar_2026',
                               'BrutMarj_2024', 'BrutMarj_2025', 'BrutMarj_2026',
                               'Stok_2024', 'Stok_2025', 'Stok_2026',
                               'SMM_2024', 'SMM_2025', 'SMM_2026']
                
                full_comparison = full_comparison[column_order]
                
                # CSV'ye çevir - encoding ile Türkçe karakter sorunu çözülür
                csv_data = full_comparison.to_csv(index=False, encoding='utf-8-sig', sep=';')
                
                st.download_button(
                    label="📥 Toplu CSV İndir (Tüm Aylar ve Gruplar)",
                    data=csv_data.encode('utf-8-sig'),
                    file_name='butce_2024_2025_2026_tam_veri.csv',
                    mime='text/csv',
                    type='primary'
                )
                
                st.success(f"✅ CSV hazır! Toplam {len(full_comparison)} satır veri")
                st.caption("💡 Excel'de açarken: Veri > Metin/CSV'den > Ayırıcı: Noktalı virgül (;)")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>2026 Satış Bütçe Tahmin Sistemi | Ay + Ana Grup + Alınan Dersler</p>
    </div>
""", unsafe_allow_html=True)
