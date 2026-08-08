"""Certificado local para liberar o microfone no celular.

O navegador so entrega o microfone em "contexto seguro": HTTPS, ou localhost.
No computador, localhost resolve. No celular, o endereco e o IP da maquina na
rede local -- que nao e contexto seguro em HTTP.

Este modulo gera uma autoridade certificadora propria (a "ca.crt", que voce
instala no celular uma vez) e um certificado de servidor assinado por ela,
valido para os IPs desta maquina. Nada disso sai da sua rede.

Regenera automaticamente quando o IP da maquina muda.
"""

from __future__ import annotations

import datetime as dt
import ipaddress
import json
import socket
from pathlib import Path

PASTA = Path(__file__).resolve().parent / ".certs"
CA_CRT = PASTA / "ca.crt"
CA_KEY = PASTA / "ca.key"
SRV_CRT = PASTA / "servidor.crt"
SRV_KEY = PASTA / "servidor.key"
META = PASTA / "meta.json"

# Safari recusa certificado de servidor com validade acima de 398 dias.
DIAS_SERVIDOR = 365
DIAS_CA = 3650


class CertificadoIndisponivel(RuntimeError):
    """A biblioteca cryptography nao esta instalada."""


def disponivel() -> bool:
    try:
        import cryptography  # noqa: F401
    except ImportError:
        return False
    return True


def detectar_ips() -> list[str]:
    """IPs desta maquina na rede local, sem contar loopback."""
    ips: set[str] = set()

    # Truque do socket UDP: nao envia pacote, so revela qual interface o
    # sistema usaria para sair -- geralmente o Wi-Fi.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ips.add(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass

    return sorted(ip for ip in ips if not ip.startswith("127."))


def _nome(cn: str):
    from cryptography import x509
    from cryptography.x509.oid import NameOID

    return x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Gravador de Consulta"),
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
        ]
    )


def _chave():
    from cryptography.hazmat.primitives.asymmetric import rsa

    # RSA 2048: o que iOS e Android aceitam sem discussao.
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _salvar_chave(chave, destino: Path) -> None:
    from cryptography.hazmat.primitives import serialization

    destino.write_bytes(
        chave.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    destino.chmod(0o600)


def _salvar_cert(cert, destino: Path) -> None:
    from cryptography.hazmat.primitives import serialization

    destino.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _criar_ca():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    chave = _chave()
    agora = dt.datetime.now(dt.timezone.utc)
    nome = _nome("Gravador de Consulta - CA local")

    cert = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - dt.timedelta(minutes=5))
        .not_valid_after(agora + dt.timedelta(days=DIAS_CA))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(chave.public_key()), critical=False
        )
        .sign(chave, hashes.SHA256())
    )

    _salvar_chave(chave, CA_KEY)
    _salvar_cert(cert, CA_CRT)
    return chave, cert


def _carregar_ca():
    from cryptography.hazmat.primitives import serialization
    from cryptography import x509

    chave = serialization.load_pem_private_key(CA_KEY.read_bytes(), password=None)
    cert = x509.load_pem_x509_certificate(CA_CRT.read_bytes())
    return chave, cert


def _criar_servidor(ca_chave, ca_cert, ips: list[str]):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.x509.oid import ExtendedKeyUsageOID

    chave = _chave()
    agora = dt.datetime.now(dt.timezone.utc)

    # Navegador moderno ignora o Common Name: o que vale e o SAN.
    alternativos: list = [x509.DNSName("localhost")]
    alternativos.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))
    for ip in ips:
        try:
            alternativos.append(x509.IPAddress(ipaddress.ip_address(ip)))
        except ValueError:
            continue

    cert = (
        x509.CertificateBuilder()
        .subject_name(_nome("Gravador de Consulta"))
        .issuer_name(ca_cert.subject)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - dt.timedelta(minutes=5))
        .not_valid_after(agora + dt.timedelta(days=DIAS_SERVIDOR))
        .add_extension(x509.SubjectAlternativeName(alternativos), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(ca_chave, hashes.SHA256())
    )

    _salvar_chave(chave, SRV_KEY)
    _salvar_cert(cert, SRV_CRT)
    return cert


def _expiracao(cert) -> dt.datetime:
    """Validade do certificado, com fuso — compatível com cryptography < 42."""
    try:
        return cert.not_valid_after_utc
    except AttributeError:
        return cert.not_valid_after.replace(tzinfo=dt.timezone.utc)


def garantir(ips: list[str]) -> tuple[Path, Path, bool]:
    """Devolve (certificado, chave, foi_regenerado) para os IPs informados."""
    if not disponivel():
        raise CertificadoIndisponivel(
            "A biblioteca 'cryptography' não está instalada — ela é necessária "
            "para o modo celular. Rode:\n    pip install -r app/requirements.txt"
        )

    PASTA.mkdir(parents=True, exist_ok=True)

    anterior = {}
    if META.is_file():
        try:
            anterior = json.loads(META.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            anterior = {}

    completo = all(p.is_file() for p in (CA_CRT, CA_KEY, SRV_CRT, SRV_KEY))
    mesmos_ips = anterior.get("ips") == ips
    valido = False

    if completo:
        try:
            from cryptography import x509

            cert = x509.load_pem_x509_certificate(SRV_CRT.read_bytes())
            expira = _expiracao(cert)
            valido = expira > dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7)
        except Exception:  # noqa: BLE001
            valido = False

    if completo and mesmos_ips and valido:
        return SRV_CRT, SRV_KEY, False

    # A CA sobrevive a troca de IP: assim o celular não precisa reinstalar nada.
    if CA_CRT.is_file() and CA_KEY.is_file():
        try:
            ca_chave, ca_cert = _carregar_ca()
        except Exception:  # noqa: BLE001
            ca_chave, ca_cert = _criar_ca()
    else:
        ca_chave, ca_cert = _criar_ca()

    _criar_servidor(ca_chave, ca_cert, ips)
    META.write_text(json.dumps({"ips": ips}, indent=2), encoding="utf-8")

    return SRV_CRT, SRV_KEY, True
