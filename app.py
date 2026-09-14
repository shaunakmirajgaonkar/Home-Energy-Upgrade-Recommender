from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='Home Energy Upgrade Recommender', page_icon='🏡', layout='wide', initial_sidebar_state='expanded')
BASE=Path(__file__).resolve().parent; DATA=BASE/'data'

st.markdown('''<style>
.stApp{background:linear-gradient(135deg,#f7fbff 0%,#eef8f4 50%,#fff9ef 100%);color:#17324d}.block-container{max-width:1500px;padding-top:1.2rem}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid #dbe6ef}[data-testid="stSidebar"] *{color:#17324d!important}
.hero{background:linear-gradient(120deg,#fff,#edf7ff);border:1px solid #dbe6ef;border-radius:24px;padding:27px 30px;box-shadow:0 12px 35px rgba(27,61,90,.08);margin-bottom:18px}.hero h1{margin:0;color:#17324d;font-size:2.35rem}.hero p{color:#60758a;font-size:1rem;margin:.5rem 0 0}.badge{display:inline-block;background:#e7f3ff;color:#1769aa;border:1px solid #c7e4fb;border-radius:999px;padding:6px 12px;font-weight:800;font-size:.76rem;margin-bottom:9px}
.kpi{background:#fff;border:1px solid #dbe6ef;border-radius:18px;padding:16px;min-height:112px;box-shadow:0 8px 25px rgba(27,61,90,.06)}.kpi .l{color:#60758a;font-size:.78rem;font-weight:800;text-transform:uppercase}.kpi .v{color:#17324d;font-size:1.75rem;font-weight:850;margin-top:5px}.kpi .s{color:#71869a;font-size:.8rem}.stButton>button{border-radius:10px;font-weight:700;color:#17324d}.small{color:#60758a;font-size:.84rem}
h2,h3{color:#17324d!important}
</style>''',unsafe_allow_html=True)

def load_csv(upload,fallback,required,label):
    if upload is None:return pd.read_csv(fallback), 'Bundled sample'
    try:
        df=pd.read_csv(upload); miss=[c for c in required if c not in df.columns]
        if miss:
            st.sidebar.error(f'{label}: missing columns: {", ".join(miss)}'); return pd.read_csv(fallback),'Bundled sample (upload rejected)'
        return df,'Uploaded CSV'
    except Exception as e:
        st.sidebar.error(f'{label}: {e}'); return pd.read_csv(fallback),'Bundled sample (upload rejected)'

def cls(x): return 'Critical' if x>=75 else 'High' if x>=55 else 'Moderate' if x>=30 else 'Low'
def score(df):
    x=df.copy()
    nums=['annual_kwh','monthly_bill_avg','summer_bill_peak','winter_bill_avg','floor_area_m2','insulation_score','window_efficiency_score','hvac_efficiency_score','appliance_efficiency_score','ventilation_score','summer_heat_index','cooling_hours_month','humidity_index','occupants']
    for c in nums:x[c]=pd.to_numeric(x[c],errors='coerce').fillna(0)
    bill=x.monthly_bill_avg.rank(pct=True).fillna(.5)*100;kwh=x.annual_kwh.rank(pct=True).fillna(.5)*100
    envelope=100-(x.insulation_score*.6+x.window_efficiency_score*.4);hvac=100-x.hvac_efficiency_score;apps=100-x.appliance_efficiency_score;vent=100-x.ventilation_score
    climate=x.summer_heat_index*.45+x.cooling_hours_month.rank(pct=True).fillna(.5)*100*.35+x.humidity_index*.2
    x['upgrade_priority_score']=(bill*.22+kwh*.15+envelope*.20+hvac*.14+apps*.10+vent*.06+climate*.13).clip(0,100).round(1)
    x['priority_class']=x.upgrade_priority_score.apply(cls)
    x['energy_intensity_kwh_m2']=(x.annual_kwh/x.floor_area_m2.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).round(1)
    x['estimated_annual_savings_pct']=((100-x.insulation_score)*.11+(100-x.window_efficiency_score)*.07+(100-x.hvac_efficiency_score)*.14+(100-x.appliance_efficiency_score)*.08+(100-x.ventilation_score)*.05).clip(0,35).round(1)
    return x

def recs(r):
    out=[]
    checks=[('Insulation improvement',r.insulation_score,55,'High','Medium','Weak envelope insulation signal.'),('Window / glazing upgrade',r.window_efficiency_score,60,'Medium','Medium','Window efficiency opportunity.'),('HVAC efficiency upgrade',r.hvac_efficiency_score,60,'High','Medium','HVAC efficiency opportunity.'),('Efficient appliances',r.appliance_efficiency_score,60,'Medium','Low','Appliance efficiency opportunity.'),('Ventilation improvement',r.ventilation_score,55,'Medium','Medium','Ventilation opportunity.')]
    for name,val,limit,impact,effort,why in checks:
        if val<limit:out.append([name,why,impact,effort,f'{val:.0f}/100'])
    if r.summer_heat_index>=70:out.append(['Heat-management measures','Elevated summer heat can increase cooling pressure.','High','Low',f'{r.summer_heat_index:.0f}/100 heat index'])
    if not out:out.append(['Whole-home efficiency review','No single component is strongly flagged.','Low','Low','Balanced component profile'])
    return pd.DataFrame(out,columns=['Upgrade','Why flagged','Expected impact','Effort','Evidence'])

home_req=['home_id','home_name','zone','home_type','floor_area_m2','occupants','annual_kwh','monthly_bill_avg','summer_bill_peak','winter_bill_avg','home_age_years','insulation_score','window_efficiency_score','hvac_efficiency_score','appliance_efficiency_score','ventilation_score','summer_heat_index','cooling_hours_month','heating_hours_month','humidity_index','occupancy_index']
bill_req=['bill_id','home_id','bill_month','kwh_used','bill_amount','peak_demand_kw','billing_days','tariff_band']
climate_req=['zone','month','avg_temp_c','cooling_degree_days','heating_degree_days','humidity_pct','solar_exposure_index','heatwave_days']
st.sidebar.markdown('## 📥 Local Data Center');st.sidebar.caption('100% local processing • no external APIs')
hu=st.sidebar.file_uploader('Upload home energy CSV',type='csv');bu=st.sidebar.file_uploader('Upload utility bills CSV',type='csv');cu=st.sidebar.file_uploader('Upload climate conditions CSV',type='csv')
homes,hs=load_csv(hu,DATA/'sample_home_energy.csv',home_req,'Home CSV');bills,bs=load_csv(bu,DATA/'sample_utility_bills.csv',bill_req,'Bills CSV');climate,cs=load_csv(cu,DATA/'sample_climate_conditions.csv',climate_req,'Climate CSV')
homes=score(homes)
st.sidebar.markdown('---');st.sidebar.markdown('### 🎛️ Filters')
zone=st.sidebar.selectbox('Zone',['All']+sorted(homes.zone.astype(str).unique().tolist()));pc=st.sidebar.selectbox('Priority',['All','Critical','High','Moderate','Low']);q=st.sidebar.text_input('Search home',placeholder='Name or ID…')
view=homes.copy()
if zone!='All':view=view[view.zone.astype(str)==zone]
if pc!='All':view=view[view.priority_class==pc]
if q.strip():view=view[view.home_name.astype(str).str.contains(q,case=False,na=False)|view.home_id.astype(str).str.contains(q,case=False,na=False)]

st.markdown('<div class="hero"><span class="badge">LOCAL-FIRST • HOME ENERGY INTELLIGENCE</span><h1>🏡 Home Energy Upgrade Recommender</h1><p>Turn bills, climate pressure, building conditions and equipment signals into an explainable upgrade-priority pathway.</p></div>',unsafe_allow_html=True)
hero_img=BASE/'assets'/'energy_home_hero.svg'
if hero_img.exists(): st.image(str(hero_img),use_container_width=True)
tabs=st.tabs(['Command Center','Upgrade Studio','Bill Intelligence','Home Profiles','Scenario Lab','Data & Export'])
with tabs[0]:
    metrics=[('Upgrade priority',f'{view.upgrade_priority_score.mean() if len(view) else 0:.1f}/100','Average screening score'),('Review queue',str(int((view.upgrade_priority_score>=55).sum())),'High + Critical homes'),('Savings opportunity',f'{view.estimated_annual_savings_pct.mean() if len(view) else 0:.1f}%','Indicative opportunity'),('Avg. monthly bill',f'₹{view.monthly_bill_avg.mean() if len(view) else 0:,.0f}','Filtered homes')]
    cols=st.columns(4)
    for c,(l,v,s) in zip(cols,metrics):c.markdown(f'<div class="kpi"><div class="l">{l}</div><div class="v">{v}</div><div class="s">{s}</div></div>',unsafe_allow_html=True)
    st.write('');a,b=st.columns([1.15,.85])
    with a:
        d=view.priority_class.value_counts().reindex(['Critical','High','Moderate','Low'],fill_value=0).reset_index();d.columns=['Priority','Homes'];fig=px.bar(d,x='Priority',y='Homes',text='Homes',title='Upgrade priority distribution');fig.update_traces(textposition='outside');st.plotly_chart(fig,use_container_width=True)
    with b:
        st.markdown('#### 🔎 Highest-priority homes');st.dataframe(view.nlargest(8,'upgrade_priority_score')[['home_name','zone','upgrade_priority_score','priority_class']],use_container_width=True,hide_index=True)
    fig=px.scatter(view,x='insulation_score',y='hvac_efficiency_score',size='annual_kwh',color='priority_class',hover_name='home_name',hover_data=['zone','monthly_bill_avg'],title='Envelope vs HVAC opportunity');st.plotly_chart(fig,use_container_width=True)
with tabs[1]:
    pathway=BASE/'assets'/'upgrade_pathway.svg'
    if pathway.exists(): st.image(str(pathway),use_container_width=True)
    if len(view):
        name=st.selectbox('Select a home',view.home_name.tolist());r=view[view.home_name==name].iloc[0];a,b,c=st.columns(3);a.metric('Priority',f'{r.upgrade_priority_score:.1f}/100',r.priority_class);b.metric('Annual energy',f'{r.annual_kwh:,.0f} kWh');c.metric('Indicative savings',f'{r.estimated_annual_savings_pct:.1f}%')
        l,rr=st.columns([.9,1.1])
        with l:
            fig=go.Figure(go.Scatterpolar(r=[r.insulation_score,r.window_efficiency_score,r.hvac_efficiency_score,r.appliance_efficiency_score,r.ventilation_score],theta=['Insulation','Windows','HVAC','Appliances','Ventilation'],fill='toself'));fig.update_layout(title='Home performance profile',polar=dict(radialaxis=dict(range=[0,100])));st.plotly_chart(fig,use_container_width=True)
        with rr:st.markdown('#### Recommended upgrade pathway');st.dataframe(recs(r),use_container_width=True,hide_index=True);st.info('Screening recommendations are not engineering designs or guaranteed savings.')
    else:st.warning('No homes match the filters.')
with tabs[2]:
    bv=bills[bills.home_id.isin(view.home_id)].copy();
    if len(bv):
        bv.bill_month=pd.to_datetime(bv.bill_month);m=bv.groupby('bill_month',as_index=False).agg(kwh_used=('kwh_used','sum'),bill_amount=('bill_amount','sum'));fig=px.line(m,x='bill_month',y='bill_amount',markers=True,title='Filtered utility cost trend');st.plotly_chart(fig,use_container_width=True);a,b,c=st.columns(3);a.metric('Total billed',f'₹{bv.bill_amount.sum():,.0f}');b.metric('Energy used',f'{bv.kwh_used.sum():,.0f} kWh');c.metric('Peak demand',f'{bv.peak_demand_kw.max():.1f} kW');fig=px.scatter(bv,x='kwh_used',y='bill_amount',color='tariff_band',hover_data=['home_id','bill_month'],title='Usage vs bill amount');st.plotly_chart(fig,use_container_width=True)
    else:st.info('No bill records for the filtered homes.')
with tabs[3]:
    cols=['home_name','zone','home_type','floor_area_m2','occupants','annual_kwh','monthly_bill_avg','insulation_score','window_efficiency_score','hvac_efficiency_score','appliance_efficiency_score','ventilation_score','upgrade_priority_score','priority_class'];st.dataframe(view[cols].sort_values('upgrade_priority_score',ascending=False),use_container_width=True,hide_index=True)
    z=view.groupby('zone',as_index=False).agg(homes=('home_id','count'),avg_priority=('upgrade_priority_score','mean'),avg_bill=('monthly_bill_avg','mean'),avg_kwh=('annual_kwh','mean'));z.avg_priority=z.avg_priority.round(1);st.markdown('#### Zone benchmark');st.dataframe(z.sort_values('avg_priority',ascending=False),use_container_width=True,hide_index=True)
with tabs[4]:
    if len(view):
        name=st.selectbox('Scenario home',view.home_name.tolist(),key='sc');base=view[view.home_name==name].iloc[0];a,b,c,d=st.columns(4);bill_red=a.slider('Bill reduction %',0,40,10);ins=b.slider('Insulation gain',0,40,15);hv=b.slider('HVAC gain',0,40,15);app=d.slider('Appliance gain',0,40,10);s=base.copy();s.monthly_bill_avg=base.monthly_bill_avg*(1-bill_red/100);s.insulation_score=min(100,base.insulation_score+ins);s.hvac_efficiency_score=min(100,base.hvac_efficiency_score+hv);s.appliance_efficiency_score=min(100,base.appliance_efficiency_score+app);sr=score(pd.DataFrame([s])).iloc[0];a,b,c=st.columns(3);a.metric('Current priority',f'{base.upgrade_priority_score:.1f}',base.priority_class);b.metric('Scenario priority',f'{sr.upgrade_priority_score:.1f}',sr.priority_class);c.metric('Improvement',f'{base.upgrade_priority_score-sr.upgrade_priority_score:.1f} pts');st.dataframe(pd.DataFrame({'Metric':['Monthly bill','Insulation','HVAC','Appliances','Priority score'],'Current':[base.monthly_bill_avg,base.insulation_score,base.hvac_efficiency_score,base.appliance_efficiency_score,base.upgrade_priority_score],'Scenario':[s.monthly_bill_avg,s.insulation_score,s.hvac_efficiency_score,s.appliance_efficiency_score,sr.upgrade_priority_score]}).round(1),use_container_width=True,hide_index=True)
    else:st.info('No homes match the filters.')
with tabs[5]:
    st.write(f'Home data: **{hs}** • Bills: **{bs}** • Climate: **{cs}**');st.dataframe(view,use_container_width=True,hide_index=True);st.download_button('⬇️ Download filtered home analytics CSV',view.to_csv(index=False).encode(), 'home_energy_upgrade_analysis.csv','text/csv');a,b,c=st.columns(3);a.metric('Homes',len(homes));b.metric('Bills',len(bills));c.metric('Climate rows',len(climate));st.caption('All calculations occur locally in the Streamlit process. Uploaded data is session-scoped.')
st.markdown('---');st.caption('Decision-support screening only. Validate building, electrical, HVAC, ventilation, code and safety requirements with qualified professionals.')
