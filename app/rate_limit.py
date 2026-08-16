import ipaddress

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings


def get_client_ip(request: Request) -> str:
    """rate limit 카운팅 키로 쓸 클라이언트 IP를 구한다.

    X-Forwarded-For는 "클라이언트가 보낸 값, ..., 앞단 프록시가 붙인 값" 순으로 왼쪽부터 쌓인다.
    즉 **왼쪽일수록 위조 가능**하다. 클라이언트가 XFF 헤더를 임의로 붙여 보내면 그 값이 맨 앞에
    남기 때문에, 맨 앞 값을 신뢰하면 공격자가 헤더만 바꿔가며 제한을 무한히 우회할 수 있다.

    반대로 **오른쪽 끝은 우리 앞단의 신뢰할 수 있는 프록시가 직접 써 넣은 값**이라 위조가 불가능하다.
    (프록시는 자기가 받은 TCP 소켓의 상대 주소를 붙이지, 클라이언트 말을 믿지 않는다)

    그래서 오른쪽에서부터 신뢰 홉 수(settings.trusted_proxy_count)만큼 세어 들어간 위치를
    실제 클라이언트로 본다.

        client → GW → app  (trusted_proxy_count=1)
        XFF: "<위조 가능 구간>, client_ip"          → 뒤에서 1번째 = client_ip
        client → GW1 → GW2 → app  (trusted_proxy_count=2)
        XFF: "<위조 가능 구간>, client_ip, GW1_ip"  → 뒤에서 2번째 = client_ip

    헤더가 없거나(프록시를 안 거친 직접 호출), 홉 수가 설정보다 적거나, 값이 IP 형식이 아니면
    소켓 주소(get_remote_address)로 폴백한다. 폴백은 위조가 불가능한 값이라 안전한 기본값이다.
    """
    trusted_hops = settings.trusted_proxy_count

    # 0이면 XFF를 아예 무시한다(프록시 뒤가 아닌 환경 — 로컬 개발 등).
    if trusted_hops > 0:
        # XFF 헤더가 여러 줄로 올 수 있으므로(RFC상 콤마로 이어 붙인 것과 동일) 모두 합쳐서 본다.
        raw = ",".join(request.headers.getlist("x-forwarded-for"))
        forwarded = [ip.strip() for ip in raw.split(",") if ip.strip()]

        # 홉 수가 설정보다 적으면 프록시를 온전히 거치지 않은 요청이다 → 신뢰하지 않는다.
        if len(forwarded) >= trusted_hops:
            candidate = forwarded[-trusted_hops]
            try:
                # IP 형식이 아니면(쓰레기 값·호스트명 등) 키로 쓰지 않는다.
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass

    return get_remote_address(request)


# 앱 전역에서 공유하는 Limiter 인스턴스.
# key_func=get_client_ip → 위조에 강한 방식으로 뽑은 요청자 IP를 카운팅 키로 쓴다(IP당 제한).
# default_limits를 비워 둬서 데코레이터를 붙인 엔드포인트에만 제한이 걸린다
# (헬스체크 GET / 는 제한 없이 통과한다).
# NestJS의 ThrottlerModule + getTracker() 커스터마이징에 해당하는 역할.
limiter = Limiter(key_func=get_client_ip)

# 제한 수치는 config에서 가져온다(하드코딩하지 않는다).
# 라우터에서 @limiter.limit(TRANSCRIBE_RATE_LIMIT) 형태로 사용한다.
TRANSCRIBE_RATE_LIMIT: str = settings.transcribe_rate_limit
