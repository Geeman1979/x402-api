"""x402 transport adapter for httpx.

Wraps any httpx request in the x402 PaymentRoundTripper so that 402
responses are handled automatically: pay → retry → get data.
"""
import uuid

import httpx

from x402.http.x402_http_client import PaymentRoundTripper


class X402Transport(httpx.BaseTransport):
    """httpx transport that auto-pays x402 payment walls.

    Usage:
        client = httpx.Client(transport=X402Transport(round_tripper))
        # now plain client.get(...) / client.post(...) just work —
        # 402s are paid automatically and the request retried.
    """

    def __init__(self, round_tripper: PaymentRoundTripper):
        super().__init__()
        self._rt = round_tripper
        self._inner = httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self._inner.handle_request(request)
        response.read()  # materialize body so .content/.headers work

        if response.status_code != 402:
            return response

        def retry_with_headers(extra_headers: dict[str, str]) -> httpx.Response:
            headers = dict(request.headers)
            headers.update(extra_headers)
            body = request.read() if request.content else None
            retry = httpx.Request(
                method=request.method,
                url=str(request.url),
                headers=headers,
                content=body,
            )
            return self._inner.handle_request(retry)

        result = self._rt.handle_response(
            request_id=str(uuid.uuid4()),
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
            retry_func=retry_with_headers,
            request_url=str(request.url),
        )

        if result is None:
            return response  # not a payment wall after all
        return result


def make_paid_client(private_key: str, chain_id: int = 84532) -> httpx.Client:
    """Build an httpx.Client that auto-pays x402 walls from `private_key`.

    chain_id defaults to Base Sepolia testnet (84532) — the network the
    live community facilitator supports for the 'exact' scheme.
    """
    from eth_account import Account
    from x402.client import x402ClientSync
    from x402.http.x402_http_client import x402HTTPClientSync
    from x402.mechanisms.evm.exact import ExactEvmClientScheme

    signer = Account.from_key(private_key)
    evm_client = ExactEvmClientScheme(signer)
    base_client = x402ClientSync()
    base_client.register(f"eip155:{chain_id}", evm_client)

    http_client = x402HTTPClientSync(base_client)
    round_tripper = PaymentRoundTripper(http_client)
    return httpx.Client(transport=X402Transport(round_tripper)), signer.address
