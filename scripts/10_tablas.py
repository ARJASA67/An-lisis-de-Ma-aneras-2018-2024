"""10 · Tablas de respuesta con evidencia (PRD §6.13, D17, U14). `make tablas`.

Entrada: data/mejor_modelo.json, ranking.csv, salida/entidades_enriquecidas.csv,
salida/cantidades_auxiliares.csv, data/pasajes.parquet, data/consultas.csv,
config/tablas_respuesta.yaml, config/excluir_tablas.yaml, gazetteers y, si existe,
anotaciones/valoraciones.yaml (solo lectura; la escribe el alumno).
Salidas: salida/respuestas.csv (16 columnas), salida/10_exclusiones.csv,
salida/10_frecuencias.csv, salida/10_tablas_hash.json y salida/tablas_respuesta/Q1.md … Q10.md
y todas.md.
"""
from __future__ import annotations

import json
import sys

import pandas as pd
import yaml

from mtx import config, consultas, respuestas

RANKING = config.RAIZ / "ranking.csv"
MEJOR = config.DIR_DATA / "mejor_modelo.json"
ENRIQUECIDAS = config.DIR_SALIDA / "entidades_enriquecidas.csv"
AUXILIARES = config.DIR_SALIDA / "cantidades_auxiliares.csv"
VALORACIONES = config.DIR_ANOTACIONES / "valoraciones.yaml"
DIR_TABLAS = config.DIR_SALIDA / "tablas_respuesta"
CSV = {"index": False, "lineterminator": "\n"}


def main() -> int:
    for ruta in (RANKING, MEJOR, ENRIQUECIDAS, AUXILIARES):
        if not ruta.exists():
            print(f"Falta {ruta.relative_to(config.RAIZ)}: corre antes los scripts 05 y 08.")
            return 1
    mejor = json.loads(MEJOR.read_text(encoding="utf-8"))["modelo"]
    mapa = config.cargar_yaml("tablas_respuesta.yaml")
    excl = config.cargar_yaml("excluir_tablas.yaml")["per_excluidas"]
    cons = consultas.cargar().set_index("query_id")
    faltan = set(cons.index) - set(mapa["consultas"])
    if faltan:
        print(f"config/tablas_respuesta.yaml no define {sorted(faltan)}: no se generan sus tablas.")
        return 1

    rk = pd.read_csv(RANKING, dtype={"passage_id": str, "doc_id": str})
    top = rk[rk["modelo"] == mejor]
    ids = list(top["passage_id"].unique())
    pas = pd.read_parquet(config.PASAJES_PARQUET, filters=[("passage_id", "in", ids)],
                          columns=["passage_id", "doc_id", "fecha", "texto", "inicio_cuerpo",
                                   "interlocutor", "es_reportero", "intervencion_id",
                                   "token_inicio", "token_fin"]).set_index("passage_id")

    ents = pd.read_csv(ENRIQUECIDAS, dtype={"passage_id": str, "doc_id": str})
    ents = ents.merge(top[["query_id", "passage_id"]], on=["query_id", "passage_id"])
    filtradas, conteos = respuestas.excluir(ents, excl)
    conteos.to_csv(config.DIR_SALIDA / "10_exclusiones.csv", **CSV)
    cand_e = respuestas.candidatos_entidades(filtradas)
    aux = pd.read_csv(AUXILIARES, dtype={"passage_id": str})
    aux = aux.merge(top[["query_id", "passage_id"]], on=["query_id", "passage_id"])
    cand_a = respuestas.candidatos_auxiliares(aux, pas["inicio_cuerpo"].to_dict())
    filtros = respuestas.filtros_gazetteer(
        pd.read_csv(config.DIR_CONFIG / "gazetteer_extendido.csv", dtype=str),
        pd.read_csv(config.DIR_CONFIG / "gazetteer_loc.csv", dtype=str))

    pasajes = {}
    for pid, f in pas.iterrows():
        orgs = [(int(e.inicio), int(e.fin), e.texto) for e in
                ents[(ents["passage_id"] == pid) & (ents["tipo"] == "ORG")]
                .drop_duplicates(["inicio", "fin"]).itertuples(index=False)]
        pasajes[pid] = respuestas.Pasaje(
            texto=f["texto"], doc_id=str(f["doc_id"]), fecha=str(f["fecha"])[:10],
            interlocutor=str(f["interlocutor"]), es_reportero=bool(f["es_reportero"]),
            intervencion_id=str(f["intervencion_id"]), token_inicio=int(f["token_inicio"]),
            token_fin=int(f["token_fin"]), orgs=orgs)

    valoraciones = {}
    if VALORACIONES.exists():
        valoraciones = yaml.safe_load(VALORACIONES.read_text(encoding="utf-8")) or {}

    filas, frecs, hashes, docs = [], [], {}, []
    DIR_TABLAS.mkdir(parents=True, exist_ok=True)
    ventana = int(mapa.get("ventana_contexto", 60))
    for qid in sorted(mapa["consultas"], key=lambda q: int(q[1:])):
        campos = mapa["consultas"][qid]
        e_q, a_q = cand_e[cand_e["query_id"] == qid], cand_a[cand_a["query_id"] == qid]
        resp_q, frec_q = [], []
        for campo in campos:
            c = respuestas._del_campo(campo, e_q, a_q, filtros)
            r, fr = respuestas.responder_campo(qid, campo, c, pasajes, ventana)
            resp_q += r
            frec_q.append(fr)
        resp_df = pd.DataFrame(resp_q, columns=respuestas.COLUMNAS)
        frec_df = pd.concat(frec_q, ignore_index=True) if any(len(x) for x in frec_q) \
            else pd.DataFrame(columns=["campo_respuesta"])
        exc = conteos[conteos["query_id"] == qid].set_index("motivo")["n"].to_dict()
        cuerpo = respuestas.tabla_markdown(qid, cons.loc[qid].to_dict(), campos, resp_df, frec_df,
                                           exc, mejor, int(mapa.get("max_valores_tabla", 8)))
        hashes[qid] = respuestas.sha256_texto(cuerpo)
        md = cuerpo + respuestas.bloque_valoracion(valoraciones.get(qid), hashes[qid])
        (DIR_TABLAS / f"{qid}.md").write_text(md, encoding="utf-8", newline="\n")
        docs.append(md)
        filas.append(resp_df)
        frecs.append(frec_df)

    resp = pd.concat(filas, ignore_index=True)
    textos = pas["texto"].to_dict()
    errores = respuestas.validar_respuestas(resp, textos)
    resp.to_csv(config.DIR_SALIDA / "respuestas.csv", **CSV)
    pd.concat(frecs, ignore_index=True).to_csv(config.DIR_SALIDA / "10_frecuencias.csv", **CSV)
    (DIR_TABLAS / "todas.md").write_text("\n\n".join(docs), encoding="utf-8", newline="\n")
    (config.DIR_SALIDA / "10_tablas_hash.json").write_text(
        json.dumps(hashes, indent=2) + "\n", encoding="utf-8", newline="\n")

    print("Exclusiones por consulta (marca / lista):")
    print(conteos.pivot(index="query_id", columns="motivo", values="n").to_string())
    print("\nFilas de respuestas.csv por estado:")
    print(resp.groupby(["query_id", "estado"]).size().unstack(fill_value=0).to_string())
    pend = respuestas.validar_valoraciones(valoraciones, hashes)
    print(f"\nValoraciones: {10 - len(pend)} de 10 al día. [VALIDAR] pendiente del alumno."
          if pend else "\nValoraciones: 10 de 10 al día.")
    for e in errores:
        print("ERROR:", e)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
