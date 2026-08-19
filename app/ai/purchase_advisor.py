from __future__ import annotations


def build_decision(score: int, record_count: int, increase_risk: int) -> dict:
    if record_count < 2:
        return {"code":"watch", "label":"Biraz daha veri bekle", "action":"Alarm kur", "wait_days":None}
    if score >= 85:
        return {"code":"buy", "label":"Şimdi satın al", "action":"En iyi teklife git", "wait_days":None}
    if score >= 70:
        return {"code":"consider", "label":"Satın almaya değer", "action":"Mağazaları karşılaştır", "wait_days":None}
    if score >= 50:
        return {"code":"watch", "label":"Kısa süre takip et", "action":"Alarm kur", "wait_days":7 if increase_risk < 70 else 3}
    return {"code":"wait", "label":"Beklemek daha mantıklı", "action":"Hedef fiyat belirle", "wait_days":10}
