"""07 · NER con modelo sobre los pasajes recuperados (PRD §6.8). `make ner`.

Ámbito: pasajes únicos del top-10 del mejor modelo de IR (`data/mejor_modelo.json`, D08), a lo
sumo 100. No lee juicios de entidades, gold ni conjunto de selección.

Uso:
    python scripts/07_ner.py --verificar        # P06: verificación técnica previa al gold
    python scripts/07_ner.py [--modelo SLUG] [--forzar]

Salidas (por modelo): data/cache_ner/{slug}@{rev}/*.json (crudo, versionado),
salida/entidades_{slug}.csv (8 columnas, metodo == modelo), salida/07_entidades_{slug}_sin_union.csv
(para medir el efecto de la unión interpalabra), salida/07_entidades_{slug}_detalle.csv (con
confianza), salida/07_uniones_spans.csv y salida/07_ner_resumen.json.

Modo ciego (D10): estas salidas contienen predicciones; el anotador del gold no las abre hasta
`anotaciones/cierre_gold.json`.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from collections import Counter

import pandas as pd

from mtx import config, ner_modelo
from mtx.sistema import rss_mb

RANKING = config.RAIZ / "ranking.csv"
MEJOR = config.DIR_DATA / "mejor_modelo.json"
COLS_ENT = ["query_id", "doc_id", "passage_id", "tipo", "texto", "inicio", "fin", "metodo"]
COLS_UNION = ["passage_id", "tipo", "inicio_1", "fin_1", "inicio_2", "fin_2", "inicio_union",
              "fin_union", "texto_union", "confianza_1", "confianza_2"]

# Ejemplos de desarrollo sintéticos (P06): redactados para la verificación, no salen del corpus
# ni de la muestra gold.
EJEMPLOS_DESARROLLO = [
    ("El presidente Andrés Manuel López Obrador se reunió con directivos de Pemex en Dos Bocas, "
    "Tabasco."),
    "La Secretaría de Salud y el IMSS informaron que Jorge Alcocer Varela visitará Oaxaca.",
    "SECRETARIO DE SALUD, JORGE ALCOCER VARELA: Buenos días. Hoy hablaremos de la vacuna.",
    "En Washington, el Banco Mundial y la Comisión Federal de Electricidad firmaron un acuerdo.",
]


def ambito() -> pd.DataFrame:
    """(query_id, passage_id, doc_id, texto) del top-10 del mejor modelo, en orden de ranking."""
    mejor = json.loads(MEJOR.read_text(encoding="utf-8"))["modelo"]
    rk = pd.read_csv(RANKING, dtype={"passage_id": str, "doc_id": str})
    top = rk[rk["modelo"] == mejor].sort_values(["query_id", "rango"])
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto"])
    pas = pas[pas["passage_id"].isin(set(top["passage_id"]))]
    out = top[["query_id", "passage_id", "doc_id"]].merge(pas, on="passage_id", how="left")
    if out["texto"].isna().any():
        raise SystemExit("Hay pasajes del ranking que no están en data/pasajes.parquet")
    return out


def verificar(cfg: dict, slug: str | None) -> int:
    """Lista P06: cabeza NER, id2label real, tokenizador rápido con offsets, memoria, ejemplos."""
    import torch
    import transformers

    modelo = ner_modelo.modelo_por_slug(cfg, slug)
    mem0 = rss_mb()
    t0 = time.perf_counter()
    pipe = ner_modelo.construir_pipeline(modelo, cfg)
    t_carga = time.perf_counter() - t0
    mem1 = rss_mb()
    tok, conf = pipe.tokenizer, pipe.model.config
    arquitectura = type(pipe.model).__name__
    cabeza_ner = arquitectura.endswith("ForTokenClassification")
    enc = tok("Prueba de offsets", add_special_tokens=False, return_offsets_mapping=True)
    con_offsets = "offset_mapping" in enc and len(enc["offset_mapping"]) > 0
    limite = ner_modelo.limite_subtokens(pipe, int(cfg["fragmentacion"]["margen"]))
    etiquetas = ner_modelo.etiquetas_del_modelo(conf.id2label)

    # Ejemplo largo sintético para ejercitar ventanas con el tokenizador real.
    largo = " ".join(EJEMPLOS_DESARROLLO * 40)
    textos = [*EJEMPLOS_DESARROLLO, largo]
    crudas = ner_modelo.inferir([(f"dev_{i}", t) for i, t in enumerate(textos)], pipe, cfg)
    filas, invariante_ok = [], True
    for i, t in enumerate(textos):
        ents, uniones, desc = ner_modelo.posprocesar(t, crudas[f"dev_{i}"]["crudas"], cfg,
                                                     etiquetas)
        invariante_ok &= all(t[e.inicio:e.fin] == e.texto for e in ents)
        if i < len(EJEMPLOS_DESARROLLO):
            filas.append((t, ents, uniones, desc))
    n_vent_largo = crudas[f"dev_{len(textos) - 1}"]["ventanas"]

    checks = {
        "Pesos con cabeza de clasificación de tokens": (cabeza_ner, arquitectura),
        "Tokenizador rápido (`is_fast`)": (bool(tok.is_fast), type(tok).__name__),
        "Devuelve `offset_mapping`": (con_offsets, ""),
        "Invariante `texto[inicio:fin] == texto_entidad` en ejemplos": (invariante_ok, ""),
        "Texto largo fragmentado en varias ventanas": (n_vent_largo > 1,
                                                       f"{n_vent_largo} ventanas"),
    }
    ok = all(v for v, _ in checks.values())
    lineas = [
        f"# Verificación técnica del NER (P06) · `{modelo['repo_id']}`", "",
        (f"Fecha: {time.strftime('%Y-%m-%d %H:%M')}. Revisión fija: `{modelo['revision']}`. "
        "Sin gold: ejemplos de desarrollo sintéticos."), "",
        "| Comprobación | Resultado | Detalle |", "|---|---|---|",
        *[f"| {k} | {'sí' if v else '**NO**'} | {d} |" for k, (v, d) in checks.items()], "",
        f"- `id2label`: {json.dumps(conf.id2label, ensure_ascii=False)}",
        (f"- Etiquetas base: {', '.join(sorted(etiquetas))}. Mapeadas: "
        f"{', '.join(sorted(e for e in etiquetas if e in cfg['mapa_etiquetas']))}; "
        f"descartadas y contadas: {', '.join(sorted(e for e in etiquetas if e in cfg['descartadas']))}."),
        (f"- `max_position_embeddings` = {conf.max_position_embeddings}; tokens especiales = "
        f"{tok.num_special_tokens_to_add()}; límite por ventana con margen = {limite} subtokens; "
        f"solapamiento = {cfg['fragmentacion']['solapamiento']}."),
        (f"- Entorno: Python {platform.python_version()}, transformers {transformers.__version__}, "
        f"torch {torch.__version__}, {platform.system()} {platform.machine()}, solo CPU."),
        (f"- Carga del pipeline: {t_carga:.1f} s; memoria pico {mem0:.0f} → {mem1:.0f} MB "
        f"(+{mem1 - mem0:.0f} MB)."), "",
        "## Ejemplos de desarrollo (sintéticos)", "",
    ]
    for t, ents, uniones, desc in filas:
        lineas += [f"> {t}", "",
                   "- " + ("; ".join(f"{e.tipo} «{e.texto}» ({e.confianza:.2f})" for e in ents)
                           or "sin entidades"),
                   f"- Uniones interpalabra: {len(uniones)}; descartes: {dict(desc) or 0}", ""]
    lineas.append(f"**Resultado: {'APTO' if ok else 'NO APTO'}** como NER del proyecto.")
    ruta = config.DIR_SALIDA / f"07_verificacion_ner_{modelo['slug']}.md"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lineas))
    return 0 if ok else 1


def correr(cfg: dict, modelo: dict, forzar: bool) -> dict:
    amb = ambito()
    unicos = amb.drop_duplicates("passage_id")
    pasajes = list(zip(unicos["passage_id"], unicos["texto"], strict=True))
    t0 = time.perf_counter()
    res = ner_modelo.ejecutar(pasajes, modelo, cfg, forzar=forzar)
    etiquetas = set(res.etiquetas_modelo) if res.etiquetas_modelo else None
    texto_de = dict(pasajes)
    ents_con, ents_sin, detalle, uniones = {}, {}, [], []
    descartes: Counter = Counter()
    for pid, texto in pasajes:
        con, uni, desc = ner_modelo.posprocesar(texto, res.crudas[pid], cfg, etiquetas)
        sin, _, _ = ner_modelo.posprocesar(texto, res.crudas[pid], cfg, etiquetas,
                                           unir_interpalabra=False)
        ents_con[pid], ents_sin[pid] = con, sin
        descartes.update(desc)
        uniones += [{"passage_id": pid, **u} for u in uni]
        detalle += [{"passage_id": pid, "tipo": e.tipo, "texto": e.texto, "inicio": e.inicio,
                     "fin": e.fin, "confianza": round(e.confianza, 6), "unida": e.unida}
                    for e in con]

    def filas(por_pasaje: dict) -> pd.DataFrame:
        out = []
        for q, pid, doc in zip(amb["query_id"], amb["passage_id"], amb["doc_id"], strict=True):
            for e in por_pasaje[pid]:
                assert texto_de[pid][e.inicio:e.fin] == e.texto
                out.append({"query_id": q, "doc_id": doc, "passage_id": pid, "tipo": e.tipo,
                            "texto": e.texto, "inicio": e.inicio, "fin": e.fin,
                            "metodo": "modelo"})
        df = pd.DataFrame(out, columns=COLS_ENT)
        assert not df.duplicated(["query_id", "passage_id", "tipo", "inicio", "fin"]).any()
        return df

    slug = modelo["slug"]
    kw = {"index": False, "lineterminator": "\n", "encoding": "utf-8"}
    con_df = filas(ents_con)
    con_df.to_csv(config.DIR_SALIDA / f"entidades_{slug}.csv", **kw)
    filas(ents_sin).to_csv(config.DIR_SALIDA / f"07_entidades_{slug}_sin_union.csv", **kw)
    pd.DataFrame(detalle).to_csv(config.DIR_SALIDA / f"07_entidades_{slug}_detalle.csv", **kw)
    pd.DataFrame(uniones, columns=COLS_UNION).to_csv(config.DIR_SALIDA / "07_uniones_spans.csv",
                                                      **kw)
    import transformers

    return {
        "modelo": slug, "repo_id": modelo["repo_id"], "revision": modelo["revision"],
        "version_posproceso": cfg["version_posproceso"],
        "parametros_cache": ner_modelo.parametros_cache(modelo, cfg),
        "ambito": {"filas_query_pasaje": len(amb), "pasajes_unicos": len(pasajes),
                   "mejor_modelo_ir": json.loads(MEJOR.read_text(encoding="utf-8"))["modelo"]},
        "pasajes_inferidos": res.inferidos, "pasajes_cacheados": res.cacheados,
        "segundos_carga_modelo": res.segundos_carga,
        "segundos_inferencia": res.segundos_inferencia,
        "segundos_total": round(time.perf_counter() - t0, 3),
        "entidades_por_tipo": con_df["tipo"].value_counts().sort_index().to_dict(),
        "entidades_unicas_por_pasaje": sum(len(v) for v in ents_con.values()),
        "uniones_interpalabra": len(uniones), "descartes": dict(sorted(descartes.items())),
        "versiones": {"python": platform.python_version(),
                      "transformers": transformers.__version__},
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modelo", help="slug de config/ner.yaml (por defecto, todos)")
    ap.add_argument("--forzar", action="store_true", help="reinferir aunque haya caché vigente")
    ap.add_argument("--verificar", action="store_true", help="verificación técnica P06")
    args = ap.parse_args()
    config.DIR_SALIDA.mkdir(exist_ok=True)
    cfg = ner_modelo.cargar_config()
    if args.verificar:
        return verificar(cfg, args.modelo)
    modelos = [ner_modelo.modelo_por_slug(cfg, args.modelo)] if args.modelo else cfg["modelos"]
    resumen = {m["slug"]: correr(cfg, m, args.forzar) for m in modelos}
    ruta = config.DIR_SALIDA / "07_ner_resumen.json"
    previo = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    previo.update(resumen)
    ruta.write_text(json.dumps(previo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                    newline="\n")
    for slug, r in resumen.items():
        print(f"{slug}: {r['ambito']['pasajes_unicos']} pasajes ({r['pasajes_inferidos']} "
              f"inferidos, {r['pasajes_cacheados']} de caché) en {r['segundos_total']} s; "
              f"entidades {r['entidades_por_tipo']}; uniones {r['uniones_interpalabra']}; "
              f"descartes {r['descartes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
