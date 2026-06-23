from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Callable
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


@dataclass(frozen=True)
class AiStatus:
    mode: str
    provider: str
    available: bool
    label: str
    fallback_message: str


class AiGatewayError(Exception):
    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class OffProvider:
    def health_status(self) -> AiStatus:
        return AiStatus(
            mode="off",
            provider="off",
            available=False,
            label="ИИ-помощник отключён",
            fallback_message="Постарайтесь ответить максимально четко и полно на вопрос.",
        )

    def assess_profile_answer(self, payload: dict[str, object]) -> dict[str, object]:
        _ = payload
        raise AiGatewayError("ИИ-помощник отключён.", 409)


GenerateFn = Callable[[str, str, str], str]
ChatCompletionFn = Callable[[str, str, str, str, float], str]


class OllamaProvider:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        generate: GenerateFn | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self._generate = generate

    def health_status(self) -> AiStatus:
        return AiStatus(
            mode="local",
            provider="ollama",
            available=True,
            label=f"Ollama: {self.model_name}",
            fallback_message="Локальная модель подключена как советник, решения остаются за пользователем.",
        )

    def assess_profile_answer(self, payload: dict[str, object]) -> dict[str, object]:
        prompt = _assessment_prompt(payload)
        try:
            raw_response = (
                self._generate(self.base_url, self.model_name, prompt)
                if self._generate is not None
                else _ollama_generate(self.base_url, self.model_name, prompt)
            )
        except (OSError, URLError, TimeoutError) as exc:
            raise AiGatewayError("Ollama недоступна. Проверьте, что сервис запущен и модель загружена.") from exc
        parsed = _parse_structured_text(raw_response)
        return {
            "available": True,
            "provider": "ollama",
            "model": self.model_name,
            "clarity_percent": parsed["clarity_percent"],
            "status": parsed["status"],
            "explanation": parsed["explanation"] or raw_response.strip()[:1200],
            "followup_question": parsed["followup_question"],
            "raw_text": raw_response.strip()[:4000],
        }


class OpenAICompatibleProvider:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_token: str,
        timeout_seconds: float = 60,
        complete: ChatCompletionFn | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds
        self._complete = complete

    def health_status(self) -> AiStatus:
        return AiStatus(
            mode="token",
            provider="openai_compatible",
            available=True,
            label=f"OpenAI-compatible: {self.model_name}",
            fallback_message="Внешняя модель подключена как советник, решения остаются за пользователем.",
        )

    def assess_profile_answer(self, payload: dict[str, object]) -> dict[str, object]:
        prompt = _assessment_prompt(payload)
        try:
            raw_response = (
                self._complete(
                    self.base_url,
                    self.model_name,
                    self.api_token,
                    prompt,
                    self.timeout_seconds,
                )
                if self._complete is not None
                else _openai_compatible_chat_completion(
                    self.base_url,
                    self.model_name,
                    self.api_token,
                    prompt,
                    self.timeout_seconds,
                )
            )
        except HTTPError as exc:
            raise _openai_http_error(exc) from exc
        except (OSError, URLError, TimeoutError) as exc:
            raise AiGatewayError("LLM API недоступен. Проверьте сеть, VPN и base_url.") from exc
        parsed = _parse_structured_text(raw_response)
        return {
            "available": True,
            "provider": "openai_compatible",
            "model": self.model_name,
            "clarity_percent": parsed["clarity_percent"],
            "status": parsed["status"],
            "explanation": parsed["explanation"] or raw_response.strip()[:1200],
            "followup_question": parsed["followup_question"],
            "raw_text": raw_response.strip()[:4000],
        }


def build_ai_gateway(ai_mode: str, ai_provider: str) -> OffProvider:
    # The first MVP deliberately exposes only a no-model provider.
    _ = (ai_mode, ai_provider)
    return OffProvider()


def build_local_gateway_from_configuration(
    config: dict[str, object],
    generate: GenerateFn | None = None,
) -> OffProvider | OllamaProvider | OpenAICompatibleProvider:
    mode = config.get("effective_mode") or config.get("mode")
    provider = config.get("effective_provider") or config.get("provider")
    if (
        mode == "local"
        and provider == "ollama"
        and config.get("base_url")
        and config.get("model_name")
    ):
        return OllamaProvider(
            base_url=str(config["base_url"]),
            model_name=str(config["model_name"]),
            generate=generate,
        )
    if (
        mode == "token"
        and provider == "openai_compatible"
        and config.get("base_url")
        and config.get("model_name")
        and config.get("api_token")
    ):
        return OpenAICompatibleProvider(
            base_url=str(config["base_url"]),
            model_name=str(config["model_name"]),
            api_token=str(config["api_token"]),
            timeout_seconds=float(config.get("request_timeout_seconds", 60)),
        )
    return OffProvider()


def _ollama_generate(base_url: str, model_name: str, prompt: str) -> str:
    body = json.dumps(
        {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 16384, "temperature": 0.1},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urlrequest.Request(
        f"{base_url}/api/generate",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("response", ""))


def _openai_compatible_chat_completion(
    base_url: str,
    model_name: str,
    api_token: str,
    prompt: str,
    timeout_seconds: float,
) -> str:
    endpoint = _chat_completions_url(base_url)
    body = json.dumps(
        {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты аккуратный HR-ассистент. Отвечай строго в запрошенном формате "
                        "и не запрашивай персональные данные."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urlrequest.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return _extract_chat_completion_text(payload)


def _chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/v1/chat/completions"


def _extract_chat_completion_text(payload: dict[str, object]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AiGatewayError("LLM API вернул пустой ответ.")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise AiGatewayError("LLM API вернул неожиданный формат ответа.")
    message = choice.get("message")
    if isinstance(message, dict) and message.get("content"):
        return str(message["content"])
    if choice.get("text"):
        return str(choice["text"])
    raise AiGatewayError("LLM API не вернул текст ответа.")


def _openai_http_error(exc: HTTPError) -> AiGatewayError:
    detail = _read_http_error_detail(exc)
    if exc.code in {401, 403}:
        return AiGatewayError("LLM API отклонил ключ доступа. Проверьте API token.", 502)
    if exc.code == 429:
        return AiGatewayError("LLM API вернул rate limit. Повторите позже или проверьте лимиты ключа.", 503)
    if 500 <= exc.code <= 599:
        return AiGatewayError("LLM API временно недоступен. Повторите позже.", 503)
    return AiGatewayError(f"LLM API вернул ошибку {exc.code}: {detail}", 502)


def _read_http_error_detail(exc: HTTPError) -> str:
    try:
        payload = exc.read().decode("utf-8")
    except Exception:
        return exc.reason if isinstance(exc.reason, str) else "без деталей"
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return payload[:500]
    error = parsed.get("error") if isinstance(parsed, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])[:500]
    return payload[:500]


def _assessment_prompt(payload: dict[str, object]) -> str:
    strictness = str(payload.get("followup_strictness", "balanced"))
    strictness_hint = {
        "soft": "Задавай уточнение только если ответ явно непонятен или не отвечает на вопрос.",
        "balanced": "Задавай одно практичное уточнение, если ответ можно сделать яснее или полнее.",
        "strict": "Будь требовательным: проверяй, отвечает ли текст на вопрос и достаточно ли он понятен для профиля должности.",
    }.get(strictness, "Задавай одно практичное уточнение, если ответ можно сделать яснее или полнее.")
    return (
        "Ты HR-ассистент, который проводит интервью по профилированию должности. "
        "Твоя задача - понять, достаточно ли ясен конкретный ответ человека на один вопрос анкеты. "
        "Не принимай решений по статусу профиля. Не проси ФИО, email, кадровые ID или другие персональные данные. "
        f"{strictness_hint}\n\n"
        "Оцени понятность ответа в процентах от 0 до 100. "
        "Если понятность ниже требуемого порога, сформулируй ровно один уточняющий вопрос человеку. "
        "Если ответ понятен, напиши, что уточнение не требуется.\n\n"
        "Ответь строго в такой структуре, без JSON и без markdown:\n"
        "ПОНЯТНОСТЬ: <число от 0 до 100>%\n"
        "СТАТУС: понятно или уточнить\n"
        "ПОЯСНЕНИЕ: <1-3 предложения почему>\n"
        "УТОЧНЯЮЩИЙ ВОПРОС: <один вопрос или 'не требуется'>\n\n"
        f"Данные для интервью:\n{_payload_as_text(payload)}"
    )


def _payload_as_text(payload: dict[str, object]) -> str:
    lines = [
        f"Порог понятности: {payload.get('clarity_threshold', 70)}%",
        f"Раздел: {payload.get('section', '')}",
        f"Вопрос: {payload.get('question', '')}",
        f"Пример хорошего ответа: {payload.get('example_answer', '')}",
    ]
    requirements = payload.get("requirements")
    if requirements:
        lines.append(f"Требования к ответу: {requirements}")
    bad_example = payload.get("bad_example")
    if bad_example:
        lines.append(f"Пример слабого ответа: {bad_example}")
    if payload.get("previous_answer"):
        lines.extend(
            [
                "",
                "Предыдущая итерация:",
                f"Предыдущий ответ: {payload.get('previous_answer')}",
                f"Предыдущий уточняющий вопрос: {payload.get('previous_followup_question')}",
                f"Предыдущая понятность: {payload.get('previous_clarity_percent')}%",
            ]
        )
    lines.extend(["", f"Текущий ответ: {payload.get('current_answer', '')}"])
    return "\n".join(lines)


def _parse_structured_text(text: str) -> dict[str, object]:
    clarity = _extract_percent(text)
    status = _extract_field(text, "СТАТУС").lower()
    explanation = _extract_field(text, "ПОЯСНЕНИЕ")
    followup = _extract_field(text, "УТОЧНЯЮЩИЙ ВОПРОС")
    if status not in {"понятно", "уточнить"}:
        status = "понятно" if clarity >= 70 else "уточнить"
    if followup.lower() in {"не требуется", "нет", "-"}:
        followup = ""
    return {
        "clarity_percent": clarity,
        "status": "accepted" if status == "понятно" else "needs_clarification",
        "explanation": explanation,
        "followup_question": followup,
    }


def _extract_percent(text: str) -> int:
    match = re.search(r"ПОНЯТНОСТЬ\s*:\s*(\d{1,3})\s*%?", text, re.IGNORECASE)
    if not match:
        return 50
    return max(0, min(100, int(match.group(1))))


def _extract_field(text: str, label: str) -> str:
    pattern = rf"{label}\s*:\s*(.*?)(?=\n[А-ЯЁA-Z ]+\s*:|\Z)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return " ".join(match.group(1).strip().split()) if match else ""
