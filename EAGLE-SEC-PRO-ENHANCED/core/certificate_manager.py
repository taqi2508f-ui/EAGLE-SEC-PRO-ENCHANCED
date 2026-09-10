import os
import datetime
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

from .logger import get_logger

logger = get_logger("cert_manager")
CERT_DIR = Path(__file__).resolve().parent.parent / "database" / "certs"
CERT_DIR.mkdir(parents=True, exist_ok=True)


class CertificateManager:
    CA_KEY_FILE = CERT_DIR / "eagle_ca.key"
    CA_CERT_FILE = CERT_DIR / "eagle_ca.crt"

    def __init__(self):
        self.ca_key = None
        self.ca_cert = None
        self._host_certs: dict[str, tuple] = {}

    def ensure_ca(self) -> bool:
        if self.CA_KEY_FILE.exists() and self.CA_CERT_FILE.exists():
            return self._load_ca()
        return self._generate_ca()

    def _generate_ca(self) -> bool:
        if not HAS_CRYPTO:
            logger.warning("cryptography package not available; skipping CA gen")
            return False
        try:
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "EAGLE-SEC PRO CA"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EAGLE-SEC PRO"),
            ])
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(key, hashes.SHA256())
            )
            self.CA_KEY_FILE.write_bytes(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                )
            )
            self.CA_CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            self.ca_key = key
            self.ca_cert = cert
            logger.info("CA certificate generated at %s", self.CA_CERT_FILE)
            return True
        except Exception as e:
            logger.error("CA generation failed: %s", e)
            return False

    def _load_ca(self) -> bool:
        if not HAS_CRYPTO:
            return False
        try:
            self.ca_key = serialization.load_pem_private_key(
                self.CA_KEY_FILE.read_bytes(), password=None
            )
            self.ca_cert = x509.load_pem_x509_certificate(self.CA_CERT_FILE.read_bytes())
            return True
        except Exception as e:
            logger.error("CA load failed: %s", e)
            return False

    def get_ca_cert_path(self) -> str:
        return str(self.CA_CERT_FILE)

    def get_ca_cert_pem(self) -> str:
        if self.CA_CERT_FILE.exists():
            return self.CA_CERT_FILE.read_text()
        return ""
