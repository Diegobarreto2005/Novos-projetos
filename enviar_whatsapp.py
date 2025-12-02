"""
Script simples para enviar mensagens para varios clientes usando o WhatsApp Web.

Requer:
    pip install pywhatkit

Execute antes do envio:
    1. Tenha o WhatsApp instalado no celular com conexao ativa.
    2. Faca login no WhatsApp Web no navegador padrao.
    3. Mantenha o computador ligado e desbloqueado durante o disparo.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import pywhatkit


# Mensagem padrao vem de mensagens/mensagem_padrao.txt
ARQUIVO_MENSAGEM_PADRAO = Path("mensagens/mensagem_padrao.txt")
ARQUIVO_NUMEROS_PADRAO = Path("dados/clientes.csv")
LOG_PATH = Path("logs/enviados.jsonl")
PYWHATKIT_DB_PATH = Path("PyWhatKit_DB.txt")

# Tempo (s) que o WhatsApp Web leva ate liberar a conversa.
WAIT_TIME = 12

# Pausa (s) entre cada envio para evitar bloqueios.
DELAY_ENTRE_MENSAGENS = 8


@dataclass
class Cliente:
    numero: str


def normalizar_numero(numero: str) -> str:
    """Padroniza numero removendo formatacao e aplicando prefixo +55 quando faltar."""
    digitos = "".join(ch for ch in numero if ch.isdigit())
    if not digitos:
        return ""
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if numero.strip().startswith("+"):
        return "+" + digitos
    if digitos.startswith("55"):
        return "+" + digitos
    if len(digitos) == 11:
        return "+55" + digitos
    return "+" + digitos


def numero_valido(numero: str) -> bool:
    """Aceita numeros com pelo menos 11 digitos ja normalizados com prefixo +."""
    if not numero.startswith("+"):
        return False
    return sum(ch.isdigit() for ch in numero) >= 11


def hash_msg(msg: str) -> str:
    return hashlib.sha256(msg.encode("utf-8")).hexdigest()


def carregar_enviados() -> set[str]:
    enviados: set[str] = set()
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                enviados.add(rec["numero"])
            except Exception:
                continue
    return enviados


def registrar_envio(numero: str, msg_hash: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"numero": numero, "msg_hash": msg_hash}) + "\n")


def carregar_enviados_pywhatkit() -> set[str]:
    enviados: set[str] = set()
    if PYWHATKIT_DB_PATH.exists():
        for line in PYWHATKIT_DB_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("Phone Number:"):
                numero = line.split(":", 1)[1].strip()
                if numero:
                    enviados.add(numero)
    return enviados


def carregar_clientes(caminho_csv: Path) -> list[Cliente]:
    if not caminho_csv.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_csv}")

    clientes: list[Cliente] = []
    with caminho_csv.open(encoding="utf-8", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for linha in reader:
            numero_bruto = (
                linha.get("numero")
                or linha.get("\ufeffnumero")
                or ""
            ).strip()
            numero = normalizar_numero(numero_bruto)
            if not numero:
                continue
            if not numero_valido(numero):
                print(
                    f"Ignorando numero invalido '{numero_bruto}'. "
                    "Informe DDD e numero (aceita com ou sem +55)."
                )
                continue
            clientes.append(Cliente(numero=numero))

    if not clientes:
        raise ValueError("Nenhum cliente valido encontrado no CSV.")
    return clientes


def preparar_mensagem(mensagem_base: str) -> str:
    return mensagem_base.strip()



def carregar_mensagem_base(mensagem_arquivo: Path | None) -> str:
    caminho = mensagem_arquivo or ARQUIVO_MENSAGEM_PADRAO
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo de mensagem nao encontrado: {caminho}. Crie ou aponte com --mensagem-arquivo"
        )
    texto = caminho.read_text(encoding="utf-8").strip()
    if not texto:
        raise ValueError("Arquivo de mensagem esta vazio.")
    return texto

def enviar_para_cliente(cliente: Cliente, mensagem_base: str) -> None:
    mensagem = preparar_mensagem(mensagem_base)
    print(f"Enviando para {cliente.numero}...")
    pywhatkit.sendwhatmsg_instantly(
        phone_no=cliente.numero,
        message=mensagem,
        wait_time=WAIT_TIME,
        tab_close=True,
        close_time=3,
    )
    time.sleep(DELAY_ENTRE_MENSAGENS)



def enviar_em_lote(
    clientes: Iterable[Cliente],
    mensagem_base: str,
    ignorar_log: bool = False,
    ignorar_pywhatkit: bool = False,
    on_result: Callable[[str, str], None] | None = None,
) -> None:
    enviados = set() if ignorar_log else carregar_enviados()
    enviados_pywhatkit = set() if ignorar_pywhatkit else carregar_enviados_pywhatkit()
    vistos_na_execucao: set[str] = set()
    msg_hash = hash_msg(mensagem_base)
    for cliente in clientes:
        if cliente.numero in vistos_na_execucao:
            print(f"Pulado (duplicado na lista): {cliente.numero}")
            if on_result:
                on_result(cliente.numero, "pulado: duplicado")
            continue
        vistos_na_execucao.add(cliente.numero)
        if not ignorar_pywhatkit and cliente.numero in enviados_pywhatkit:
            print(f"Pulado (PyWhatKit ja enviou): {cliente.numero}")
            if on_result:
                on_result(cliente.numero, "pulado: historico_pywhatkit")
            continue
        if not ignorar_log and cliente.numero in enviados:
            print(f"Pulado (ja enviado): {cliente.numero}")
            if on_result:
                on_result(cliente.numero, "pulado: log_local")
            continue
        try:
            enviar_para_cliente(cliente, mensagem_base)
            if not ignorar_log:
                registrar_envio(cliente.numero, msg_hash)
                enviados.add(cliente.numero)
            if on_result:
                on_result(cliente.numero, "enviado")
        except Exception as exc:  # noqa: BLE001 - queremos logar qualquer falha
            print(f"Falha ao enviar para {cliente.numero}: {exc}")
            if on_result:
                on_result(cliente.numero, f"erro: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dispara mensagens do WhatsApp Web para uma lista de clientes."
    )
    parser.add_argument(
        "--arquivo",
        default=str(ARQUIVO_NUMEROS_PADRAO),
        help=(
            "Caminho para o CSV apenas com a coluna numero. "
            "Por padrao usa dados/clientes.csv."
        ),
    )
    parser.add_argument(
        "--mensagem-arquivo",
        help=(
            "Arquivo .txt com a mensagem padrao. "
            "Quando omitido usamos mensagens/mensagem_padrao.txt se existir."
        ),
    )
    parser.add_argument(
        "--espera",
        type=int,
        default=WAIT_TIME,
        help="Tempo (s) que o WhatsApp precisa para abrir a conversa.",
    )
    parser.add_argument(
        "--intervalo",
        type=int,
        default=DELAY_ENTRE_MENSAGENS,
        help="Pausa (s) entre cada envio (importante para evitar bloqueio).",
    )
    parser.add_argument(
        "--numero-teste",
        help="Dispara apenas para este numero (formato +5511999999999) para validar o fluxo.",
    )
    parser.add_argument(
        "--forcar-reenvio",
        action="store_true",
        help=(
            "Ignora logs anteriores e registros do PyWhatKit, forcando reenviar mesmo para quem ja recebeu."
        ),
    )
    parser.add_argument(
        "--ignorar-pywhatkit",
        action="store_true",
        help="Ignora apenas o historico do PyWhatKit_DB.txt (mantem respeito ao log do script).",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    global WAIT_TIME, DELAY_ENTRE_MENSAGENS
    WAIT_TIME = max(5, args.espera)
    DELAY_ENTRE_MENSAGENS = max(3, args.intervalo)

    mensagem_arquivo = Path(args.mensagem_arquivo) if args.mensagem_arquivo else None
    mensagem_base = carregar_mensagem_base(mensagem_arquivo)

    if args.numero_teste:
        numero_teste = normalizar_numero(args.numero_teste)
        if not numero_valido(numero_teste):
            raise ValueError(
                "Numero de teste invalido. Informe no formato +5511999999999."
            )
        clientes = [Cliente(numero=numero_teste)]
    else:
        caminho = Path(args.arquivo)
        clientes = carregar_clientes(caminho)
    enviar_em_lote(
        clientes,
        mensagem_base,
        ignorar_log=args.forcar_reenvio,
        ignorar_pywhatkit=(args.forcar_reenvio or args.ignorar_pywhatkit),
    )


if __name__ == "__main__":
    main()
