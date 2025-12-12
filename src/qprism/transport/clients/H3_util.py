import asyncio
from pathlib import Path
from typing import List, Optional, Tuple
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.h3.events import DataReceived, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import HandshakeCompleted

Headers = List[Tuple[bytes, bytes]]

def project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def build_client_config(cert_path: Optional[Path] = None) -> QuicConfiguration:
    root = project_root()
    cfg = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
    cfg.load_verify_locations(str(cert_path or (root / "certs" / "cert.pem")))
    return cfg

def make_h3_headers(server: str, path: str, extra: Optional[Headers] = None) -> Headers:
    hdrs: Headers = [
        (b":method", b"GET"),
        (b":scheme", b"https"),
        (b":authority", server.encode()),
        (b":path", path.encode()),
    ]
    if extra:
        hdrs.extend(extra)
    return hdrs

class H3BaseClient(QuicConnectionProtocol):
    def __init__(self, *args, request_headers: Headers, **kwargs):
        super().__init__(*args, **kwargs)
        self._h3 = H3Connection(self._quic)
        self._request_sent: bool = False
        self._req_headers = request_headers
        self._done = asyncio.Event()
        self._body = bytearray()
        self._status: Optional[int] = None
        self._stream_id: Optional[int] = None

    def connection_made(self, transport):
        super().connection_made(transport)
        self._stream_id = self._quic.get_next_available_stream_id(is_unidirectional=False)
        self._h3.send_headers(self._stream_id, self._req_headers, end_stream=True)

    def quic_event_received(self, event):
        if isinstance(event, HandshakeCompleted) and not self._request_sent:
            self._request_sent = True
            self._stream_id = self._quic.get_next_available_stream_id(is_unidirectional=False)
            self._h3.send_headers(self._stream_id, self._req_headers, end_stream=True)
            self.transmit()

        for http_event in self._h3.handle_event(event):
            if isinstance(http_event, HeadersReceived):
                for k, v in http_event.headers:
                    if k == b":status":
                        try:
                            self._status = int(v)
                        except Exception:
                            self._status = None
            elif isinstance(http_event, DataReceived):
                self._body += http_event.data
                if http_event.stream_ended:
                    self._done.set()

    async def wait_body(self) -> bytes:
        await self._done.wait()
        if self._status is not None and self._status >= 400:
            raise RuntimeError(f"H3 status {self._status}")
        return bytes(self._body)
