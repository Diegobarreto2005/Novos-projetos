from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

import enviar_whatsapp as envio

app = Flask(__name__, static_folder="static", template_folder="templates")
envio_lock = Lock()


def _carregar_mensagem(payload: dict[str, Any]) -> str:
    mensagem = (payload.get("mensagem") or "").strip()
    if mensagem:
        return mensagem

    mensagem_arquivo = payload.get("mensagem_arquivo")
    caminho = Path(mensagem_arquivo) if mensagem_arquivo else None
    return envio.carregar_mensagem_base(caminho)


def _ajustar_temporizadores(payload: dict[str, Any]) -> tuple[int, int] | None:
    espera = payload.get("espera")
    intervalo = payload.get("intervalo")
    if espera is None and intervalo is None:
        return None

    espera_atual = envio.WAIT_TIME
    intervalo_atual = envio.DELAY_ENTRE_MENSAGENS
    if espera is not None:
        envio.WAIT_TIME = max(5, int(espera))
    if intervalo is not None:
        envio.DELAY_ENTRE_MENSAGENS = max(3, int(intervalo))
    return espera_atual, intervalo_atual


def _normalizar_lista(numeros: list[Any]) -> tuple[list[envio.Cliente], list[str]]:
    clientes: list[envio.Cliente] = []
    invalidos: list[str] = []
    vistos: set[str] = set()

    for bruto in numeros:
        numero = envio.normalizar_numero(str(bruto))
        if not numero or not envio.numero_valido(numero):
            invalidos.append(str(bruto))
            continue
        if numero in vistos:
            continue
        vistos.add(numero)
        clientes.append(envio.Cliente(numero=numero))
    return clientes, invalidos


@app.get("/")
def index() -> Any:
    return send_from_directory(app.template_folder, "index.html")


@app.get("/api/defaults")
def defaults() -> Any:
    erro_mensagem = None
    mensagem_padrao = ""
    try:
        mensagem_padrao = envio.carregar_mensagem_base(None)
    except Exception as exc:  # noqa: BLE001 - apenas retornamos para o front
        erro_mensagem = str(exc)

    return jsonify(
        {
            "espera": envio.WAIT_TIME,
            "intervalo": envio.DELAY_ENTRE_MENSAGENS,
            "mensagem_padrao": mensagem_padrao,
            "erro_mensagem": erro_mensagem,
        }
    )


@app.post("/api/send")
def enviar_unico() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    numero = envio.normalizar_numero(str(payload.get("numero", "")))
    if not envio.numero_valido(numero):
        return jsonify({"error": "Numero invalido. Use +55DDDNnumero."}), 400

    try:
        mensagem = _carregar_mensagem(payload)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400

    temporizador_anterior = None
    try:
        temporizador_anterior = _ajustar_temporizadores(payload)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Parametros de tempo invalidos: {exc}"}), 400

    espera_usada = envio.WAIT_TIME
    intervalo_usado = envio.DELAY_ENTRE_MENSAGENS

    msg_hash = envio.hash_msg(mensagem)
    with envio_lock:
        try:
            envio.enviar_para_cliente(envio.Cliente(numero=numero), mensagem)
            if not payload.get("ignorar_log", False):
                envio.registrar_envio(numero, msg_hash)
        except Exception as exc:  # noqa: BLE001
            if temporizador_anterior:
                envio.WAIT_TIME, envio.DELAY_ENTRE_MENSAGENS = temporizador_anterior
            return jsonify({"error": str(exc)}), 500
        if temporizador_anterior:
            envio.WAIT_TIME, envio.DELAY_ENTRE_MENSAGENS = temporizador_anterior

    return jsonify(
        {
            "status": "ok",
            "numero": numero,
            "mensagem": mensagem,
            "espera": espera_usada,
            "intervalo": intervalo_usado,
        }
    )


@app.post("/api/send-batch")
def enviar_batch() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    numeros = payload.get("numeros")
    if not isinstance(numeros, list):
        return jsonify({"error": "Envie um array 'numeros' no corpo."}), 400

    try:
        mensagem = _carregar_mensagem(payload)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400

    try:
        temporizador_anterior = _ajustar_temporizadores(payload)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Parametros de tempo invalidos: {exc}"}), 400

    clientes, invalidos = _normalizar_lista(numeros)
    if not clientes:
        return jsonify({"error": "Nenhum numero valido enviado.", "invalidos": invalidos}), 400

    espera_usada = envio.WAIT_TIME
    intervalo_usado = envio.DELAY_ENTRE_MENSAGENS
    resultado: dict[str, list[Any]] = {"enviados": [], "pulados": [], "falhas": []}

    def registrar(numero: str, status: str) -> None:
        if status.startswith("enviado"):
            resultado["enviados"].append(numero)
            return
        if status.startswith("erro"):
            resultado["falhas"].append({"numero": numero, "motivo": status})
            return
        if status.startswith("pulado"):
            motivo = status.split(":", 1)[1].strip() if ":" in status else status
            resultado["pulados"].append({"numero": numero, "motivo": motivo})

    with envio_lock:
        try:
            envio.enviar_em_lote(
                clientes,
                mensagem,
                ignorar_log=bool(payload.get("ignorar_log", False)),
                ignorar_pywhatkit=bool(payload.get("ignorar_pywhatkit", False)),
                on_result=registrar,
            )
        except Exception as exc:  # noqa: BLE001
            if temporizador_anterior:
                envio.WAIT_TIME, envio.DELAY_ENTRE_MENSAGENS = temporizador_anterior
            return jsonify({"error": str(exc)}), 500
        if temporizador_anterior:
            envio.WAIT_TIME, envio.DELAY_ENTRE_MENSAGENS = temporizador_anterior

    return jsonify(
        {
            "status": "ok",
            "total_processados": len(clientes),
            "invalidos": invalidos,
            "resultado": resultado,
            "mensagem": mensagem,
            "espera": espera_usada,
            "intervalo": intervalo_usado,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
