"""08 · Extracción fusionada reglas + modelo (PRD §6.9 y §6.10). `make extraer`.

Ámbito: pasajes únicos del top-10 del mejor modelo de IR. Reglas congeladas (`reglas-congeladas`)
y NER fijado en `data/modelo_ner.json`, leído desde su caché (no requiere red). No lee el gold.

Salidas: entidades.csv (raíz y salida/, 8 columnas), salida/entidades_unicas.csv,
salida/entidades_enriquecidas.csv, salida/08_solapes_parciales.csv y salida/08_resumen.json.

Modo ciego (D10): son predicciones; el anotador del gold no las abre hasta cerrar el gold.
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from mtx import config, fusion, ner_modelo, normalizacion, reglas

RANKING = config.RAIZ / "ranking.csv"
MEJOR = config.DIR_DATA / "mejor_modelo.json"
MODELO_NER = config.DIR_DATA / "modelo_ner.json"
VERSION_EXTRACTOR = "1"


def main() -> int:
    mejor = json.loads(MEJOR.read_text(encoding="utf-8"))["modelo"]
    fijado = json.loads(MODELO_NER.read_text(encoding="utf-8"))
    cfg = ner_modelo.cargar_config()
    modelo = ner_modelo.modelo_por_slug(cfg, fijado["slug"])
    if modelo["revision"] != fijado["revision"]:
        raise SystemExit("La revisión de config/ner.yaml no coincide con data/modelo_ner.json")

    rk = pd.read_csv(RANKING, dtype={"passage_id": str, "doc_id": str})
    ambito = rk[rk["modelo"] == mejor].sort_values(["query_id", "rango"])[
        ["query_id", "passage_id", "doc_id"]]
    ids = list(ambito["passage_id"].unique())
    pas = pd.read_parquet(config.PASAJES_PARQUET,
                          columns=["passage_id", "texto", "inicio_cuerpo", "fecha"],
                          filters=[("passage_id", "in", ids)]).set_index("passage_id")
    textos = pas["texto"].to_dict()

    # Modelo: solo desde la caché vigente; si falta un pasaje, se pide correr 07 (no hay red aquí).
    res = ner_modelo.ejecutar([(p, textos[p]) for p in ids], modelo, cfg,
                              construir=_sin_red)
    etiquetas = set(res.etiquetas_modelo or [])
    gaz = reglas.cargar_gazetteer()

    unicas, solapes = [], []
    for pid in ids:
        texto, ic = textos[pid], int(pas.at[pid, "inicio_cuerpo"])
        de_reglas = [vars(e) for e in reglas.extraer_reglas(texto, ic, gaz)]
        ents, _, _ = ner_modelo.posprocesar(texto, res.crudas[pid], cfg, etiquetas or None)
        de_modelo = [{"tipo": e.tipo, "texto": e.texto, "inicio": e.inicio, "fin": e.fin,
                      "confianza": e.confianza} for e in ents]
        filas, sol = fusion.fusionar_pasaje(pid, de_reglas, de_modelo, ic)
        solapes += sol
        enriquecidas = []
        for f in filas:
            d = {"passage_id": pid, "tipo": f.tipo, "texto": f.texto, "inicio": f.inicio,
                 "fin": f.fin, "metodo": f.metodo, "fuentes": f.fuentes, "en_marca": f.en_marca,
                 "modelo_id": modelo["repo_id"] if f.puntaje_modelo is not None else "",
                 "modelo_revision": modelo["revision"] if f.puntaje_modelo is not None else "",
                 "puntaje_modelo": "" if f.puntaje_modelo is None else round(f.puntaje_modelo, 6),
                 "version_extractor": VERSION_EXTRACTOR,
                 **normalizacion.normalizar_identidad(f.tipo, f.texto),
                 **dict.fromkeys(normalizacion.CAMPOS_FECHA, ""),
                 **dict.fromkeys(normalizacion.CAMPOS_MONTO, "")}
            if f.tipo == "FECHA":
                d.update(normalizacion.normalizar_fecha(f.texto, pas.at[pid, "fecha"]))
            elif f.tipo == "MONTO":
                d.update(normalizacion.normalizar_monto(f.texto))
            enriquecidas.append(d)
        normalizacion.vincular_personas([d for d in enriquecidas if d["tipo"] == "PER"])
        unicas += enriquecidas

    uni = pd.DataFrame(unicas)
    assert all(textos[p][i:f] == t for p, t, i, f in
               zip(uni["passage_id"], uni["texto"], uni["inicio"], uni["fin"], strict=True))
    enr = fusion.a_consultas(uni, ambito)
    ent = enr[fusion.COLUMNAS_ENTIDADES]
    errores = fusion.validar_entidades(ent, textos)
    if errores:
        print("ERROR en entidades.csv: " + "; ".join(errores))
        return 1

    kw = {"index": False, "lineterminator": "\n", "encoding": "utf-8"}
    ent.to_csv(config.DIR_SALIDA / "entidades.csv", **kw)
    ent.to_csv(config.RAIZ / "entidades.csv", **kw)
    uni[["passage_id", "tipo", "texto", "inicio", "fin", "metodo", "fuentes", "en_marca"]].to_csv(
        config.DIR_SALIDA / "entidades_unicas.csv", **kw)
    enr.to_csv(config.DIR_SALIDA / "entidades_enriquecidas.csv", **kw)
    pd.DataFrame(solapes, columns=fusion.COLUMNAS_SOLAPES).to_csv(
        config.DIR_SALIDA / "08_solapes_parciales.csv", **kw)

    resumen = {
        "mejor_modelo_ir": mejor, "modelo_ner": fijado["slug"], "revision_ner": fijado["revision"],
        "version_extractor": VERSION_EXTRACTOR, "pasajes": len(ids), "filas_entidades": len(ent),
        "entidades_unicas": len(uni),
        "por_tipo_y_metodo": {f"{t}|{m}": int(n) for (t, m), n in
                              uni.groupby(["tipo", "metodo"]).size().items()},
        "solapes": {k: int(v) for k, v in pd.Series(
            [s["clase"] for s in solapes], dtype=str).value_counts().items()},
        "estado_fecha": uni.loc[uni["tipo"] == "FECHA", "estado_fecha"].value_counts().to_dict(),
        "estado_monto": uni.loc[uni["tipo"] == "MONTO", "estado_monto"].value_counts().to_dict(),
    }
    (config.DIR_SALIDA / "08_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


def _sin_red(modelo, cfg):
    raise SystemExit("Faltan pasajes en data/cache_ner/: corre primero scripts/07_ner.py")


if __name__ == "__main__":
    sys.exit(main())
