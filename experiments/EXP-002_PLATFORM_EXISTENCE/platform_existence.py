"""EXP-002 Platform Existence — каузальный детектор площадок + null-модели.

Гипотеза H-EXP-002: площадка — устойчивый объект рынка, отличается от случайного шума.
H0: площадки не отличаются от структур на перемешанных/бутстрап-рядах с похожей волатильностью.

Данные: ADA/USDT 4H, 2023 (read-only из Mongo backtester). НЕ ищем прибыль/стратегию. Без ZigZag/lookahead.

Определение площадки (ФИКСИРОВАНО ДО расчётов, каузально, close-based для честного сравнения с null):
  Работаем на лог-цене p=log(close). Волатильность vol_t = std(Δp) за VOLN закрытых баров (только прошлое).
  Кандидат-зона стартует на баре s: центр=p[s], полуширина band=K*vol[s] (ядро). Зона длится, пока close
  остаётся в ядре. Одиночные выходы (ложные) не завершают зону. Подтверждённый пробой = CONFIRM закрытий
  подряд за пределами band+BREAK*vol → зона заканчивается на последнем баре внутри ядра. Зона считается
  ПЛОЩАДКОЙ, если длина >= MINLEN. Всё каузально: площадка ПОДТВЕРЖДАЕТСЯ только через MINLEN баров (до этого
  live-состояние = UNKNOWN). Ретроспективная разметка и live-состояние считаются раздельно.
Параметры (фиксированы): VOLN=14, K=1.5, BREAK=0.5, CONFIRM=2, MINLEN=6 (=1 сутки на 4H).
Null: N1 shuffled Δp (ломает автокорр/кластеризацию vol), N2 block-bootstrap Δp (block=6, СОХРАНЯЕТ
кластеризацию vol). 200 реализаций каждой.
"""
from __future__ import annotations
import sys, json, csv
from datetime import datetime, timezone
import numpy as np, pymongo

OUT='/home/nnv/MSM-Research-Lab/experiments/EXP-002_PLATFORM_EXISTENCE'
ART=f'{OUT}/artifacts'
RNG=np.random.default_rng(2)
# --- зафиксированные параметры
VOLN=14; K=1.5; BREAK=0.5; CONFIRM=2; MINLEN=6
NSIM=200

def load_ada_4h_2023():
    c=pymongo.MongoClient("mongodb://localhost:27017/",serverSelectionTimeoutMS=5000)["backtester"]
    s=int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000)
    e=int(datetime(2023,12,31,23,59,tzinfo=timezone.utc).timestamp()*1000)
    docs=list(c.market_candles.find({"exchange":"bybit","category":"linear","symbol":"ADAUSDT",
        "interval":"240","open_time":{"$gte":s,"$lte":e}},{"_id":0,"open_time":1,"close":1}).sort("open_time",1))
    ot=np.array([int(d["open_time"]) for d in docs],dtype=np.int64)
    close=np.array([float(d["close"]) for d in docs])
    return ot,close

def rolling_vol(dp,n=VOLN):
    v=np.full(len(dp)+1,np.nan)  # v[t] = vol известная на баре t (по прошлым Δp)
    for t in range(1,len(dp)+1):
        w=dp[max(0,t-n):t]
        if len(w)>=3: v[t]=np.std(w)
    return v  # длина = len(price)

def detect(p):
    """Каузальная сегментация. Возвращает:
       platforms: список (s,e) подтверждённых площадок (ретроспективно);
       live_state: массив меток на КАЖДЫЙ бар в момент t: 'PLATFORM'/'FORMING(UNKNOWN)'/'TRANSITION'."""
    N=len(p); dp=np.diff(p); vol=rolling_vol(dp)
    platforms=[]; live=np.array(['TRANSITION']*N,dtype=object)
    i=0
    while i<N:
        if np.isnan(vol[i]) or vol[i]<=0:
            live[i]='FORMING'; i+=1; continue
        center=p[i]; band=K*vol[i]; s=i; last_in=i; brk=0; j=i+1
        while j<N:
            if abs(p[j]-center)<=band:
                last_in=j; brk=0
            else:
                if abs(p[j]-center) > band + BREAK*vol[i]:
                    brk+=1
                    if brk>=CONFIRM: break     # подтверждённый пробой
                else:
                    brk=0                       # ложный выход в буфере — зона продолжается
            j+=1
        e=last_in; length=e-s+1
        if length>=MINLEN:
            platforms.append((s,e))
            # live: первые MINLEN-1 баров зоны — ещё UNKNOWN (не подтверждена), далее PLATFORM
            for t in range(s,e+1):
                live[t]='PLATFORM' if (t-s)>=MINLEN-1 else 'FORMING'
        else:
            for t in range(s,e+1): live[t]='FORMING'   # короткая зона = неразрешённое/переход
        i=max(e+1,s+1)
    return platforms,live

def metrics(p):
    N=len(p); pf,live=detect(p)
    durs=[e-s+1 for s,e in pf]
    cov=sum(durs)/N if N else 0
    unk=float(np.mean(live=='FORMING'))
    return dict(n=len(pf),cov=cov,med_dur=float(np.median(durs)) if durs else 0,
               mean_dur=float(np.mean(durs)) if durs else 0,unk=unk,durs=durs)

def shuffled(dp): return RNG.permutation(dp)
def block_boot(dp,block=6):
    n=len(dp); out=[]
    while len(out)<n:
        st=RNG.integers(0,n-block); out.extend(dp[st:st+block])
    return np.array(out[:n])

def null_dist(dp0,kind,nsim=NSIM):
    res={'n':[],'cov':[],'med_dur':[]}
    for _ in range(nsim):
        dp = shuffled(dp0) if kind=='shuffle' else block_boot(dp0)
        p = np.concatenate([[0.0],np.cumsum(dp)])
        m=metrics(p)
        res['n'].append(m['n']); res['cov'].append(m['cov']); res['med_dur'].append(m['med_dur'])
    return {k:np.array(v) for k,v in res.items()}

def pctile_of(real,nulls):  # доля null >= real (односторонний p)
    return float(np.mean(nulls>=real))

def main():
    ot,close=load_ada_4h_2023()
    p=np.log(close); N=len(p)
    d0=datetime.utcfromtimestamp(ot[0]/1000).date(); d1=datetime.utcfromtimestamp(ot[-1]/1000).date()
    print(f"ADA 4H 2023: {N} баров, {d0}..{d1}  (⚠ 4H данные с {d0} — полный 2023 недоступен, это H2 2023)")

    real=metrics(p)
    print(f"\nРЕАЛ ADA: площадок={real['n']} coverage={real['cov']:.2f} med_dur={real['med_dur']:.0f} "
          f"mean_dur={real['mean_dur']:.1f} UNKNOWN(live)={real['unk']:.2f}")

    dp0=np.diff(p)
    n1=null_dist(dp0,'shuffle'); n2=null_dist(dp0,'block')
    def cmp(name,nd):
        print(f"  vs {name:14}: n={nd['n'].mean():.0f}±{nd['n'].std():.0f} (real p={pctile_of(real['n'],nd['n']):.3f}) | "
              f"cov={nd['cov'].mean():.2f}±{nd['cov'].std():.2f} (real p={pctile_of(real['cov'],nd['cov']):.3f}) | "
              f"med_dur={nd['med_dur'].mean():.1f} (real p={pctile_of(real['med_dur'],nd['med_dur']):.3f})")
    print("NULL-сравнение (p = доля null-реализаций ≥ реала; малое p = реал ВЫШЕ null):")
    cmp('N1 shuffle',n1); cmp('N2 block-boot',n2)

    # параметрическая устойчивость: маски in-platform по сетке (K,MINLEN)
    def mask(p,Kx,Mx):
        global K,MINLEN; K0,M0=K,MINLEN; K,MINLEN=Kx,Mx
        pf,_=detect(p); m=np.zeros(len(p),bool)
        for s,e in pf: m[s:e+1]=True
        K,MINLEN=K0,M0; return m
    grid=[(kk,mm) for kk in (1.2,1.5,2.0) for mm in (5,6,8)]
    masks=[mask(p,kk,mm) for kk,mm in grid]
    ious=[]
    for a in range(len(masks)):
        for b in range(a+1,len(masks)):
            u=(masks[a]|masks[b]).sum(); ious.append(((masks[a]&masks[b]).sum()/u) if u else 1.0)
    stab=float(np.mean(ious))
    covs=[m.mean() for m in masks]
    print(f"\nПараметрическая устойчивость сегментации: mean pairwise IoU={stab:.2f} "
          f"(coverage по сетке {min(covs):.2f}..{max(covs):.2f})")

    # артефакты
    with open(f'{ART}/platforms_real.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(['start_iso','end_iso','duration_bars'])
        pf,_=detect(p)
        for s,e in pf:
            iso=lambda i:datetime.utcfromtimestamp(ot[i]/1000).strftime('%Y-%m-%d %H:%M')
            w.writerow([iso(s),iso(e),e-s+1])
    with open(f'{ART}/null_comparison.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(['series','n_platforms','coverage','med_duration','p_n','p_cov','p_meddur'])
        w.writerow(['ADA_real',real['n'],round(real['cov'],3),real['med_dur'],'','',''])
        for nm,nd in (('N1_shuffle',n1),('N2_block_boot',n2)):
            w.writerow([nm,round(nd['n'].mean(),1),round(nd['cov'].mean(),3),round(nd['med_dur'].mean(),1),
                        round(pctile_of(real['n'],nd['n']),3),round(pctile_of(real['cov'],nd['cov']),3),
                        round(pctile_of(real['med_dur'],nd['med_dur']),3)])
    with open(f'{ART}/param_stability.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(['K','MINLEN','coverage','n_platforms'])
        for (kk,mm),m in zip(grid,masks):
            global K,MINLEN; K0,M0=K,MINLEN; K,MINLEN=kk,mm; pf,_=detect(p); K,MINLEN=K0,M0
            w.writerow([kk,mm,round(m.mean(),3),len(pf)])
    res=dict(N=N,coverage_start=str(d0),coverage_end=str(d1),real=real,
             n1={k:[float(nd['n'].mean()),float(pctile_of(real['n'],n1['n']))] for k in ['x']},
             stab=stab,
             p_n1_cov=pctile_of(real['cov'],n1['cov']),p_n2_cov=pctile_of(real['cov'],n2['cov']),
             p_n1_n=pctile_of(real['n'],n1['n']),p_n2_n=pctile_of(real['n'],n2['n']),
             p_n1_dur=pctile_of(real['med_dur'],n1['med_dur']),p_n2_dur=pctile_of(real['med_dur'],n2['med_dur']))
    json.dump(res,open(f'{ART}/summary.json','w'),indent=1,default=str)
    print("\nартефакты записаны в artifacts/")

if __name__=='__main__': main()
