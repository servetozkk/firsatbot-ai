from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
DB_PATH=Path("data/products.db")
def _connect():
 c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row; return c
def _money(v):
 try:return f"{float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")+" TL"
 except:return "—"
def get_price_history(product_id:int,days:int=90)->dict[str,Any]:
 days=max(7,min(int(days),3650)); cutoff=(datetime.utcnow()-timedelta(days=days)).isoformat()
 with _connect() as c:
  rows=[dict(r) for r in c.execute("""SELECT store_code,total_price,price,shipping_price,recorded_at FROM global_offer_price_history WHERE global_product_id=? AND recorded_at>=? ORDER BY recorded_at""",(int(product_id),cutoff)).fetchall()]
  current=[dict(r) for r in c.execute("""SELECT store_code,current_price,shipping_price,updated_at FROM global_offers WHERE global_product_id=? AND is_active=1 AND is_hidden=0 AND current_price>0 ORDER BY current_price""",(int(product_id),)).fetchall()]
 points=[]
 for r in rows:
  value=float(r['total_price'] if r['total_price'] is not None else r['price'])
  points.append({'date':str(r['recorded_at']),'price':round(value,2),'store_code':r['store_code']})
 # Grafik boş kalmasın: güncel teklifleri son nokta olarak ekle.
 if not points:
  for r in current:
   value=float(r['current_price'])+float(r['shipping_price'] or 0)
   points.append({'date':str(r['updated_at'] or datetime.utcnow().isoformat()),'price':round(value,2),'store_code':r['store_code']})
 values=[p['price'] for p in points]
 current_best=min((float(r['current_price'])+float(r['shipping_price'] or 0) for r in current),default=None)
 low=min(values) if values else current_best; high=max(values) if values else current_best; avg=round(sum(values)/len(values),2) if values else current_best
 trend='stable'; change_percent=0.0
 if len(values)>=2 and values[0]:
  change_percent=round((values[-1]-values[0])/values[0]*100,2)
  trend='down' if change_percent<-0.5 else ('up' if change_percent>0.5 else 'stable')
 return {'engine_version':'14.8.0','product_id':int(product_id),'days':days,'points':points,'point_count':len(points),'summary':{'current_best':current_best,'current_best_text':_money(current_best),'lowest':low,'lowest_text':_money(low),'highest':high,'highest_text':_money(high),'average':avg,'average_text':_money(avg),'trend':trend,'change_percent':change_percent,'near_historical_low':bool(current_best and low and current_best<=low*1.05)}}
