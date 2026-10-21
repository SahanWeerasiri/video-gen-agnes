"""Agnes AI API client with exponential backoff and rate-limit handling."""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Optional

import requests

from video_gen.config import PipelineConfig

logger = logging.getLogger(__name__)


class AgnesAPIError(Exception):
    """Exception raised for unrecoverable errors returned by Agnes AI API."""

    def __init__(self, status_code: int, message: str, payload: Optional[dict[str, Any]] = None) -> None:
        super().__init__(f"Agnes API Error (status={status_code}): {message}")
        self.status_code = status_code
        self.message = message
        self.payload = payload or {}


class AgnesRateLimitError(AgnesAPIError):
    """Exception raised when API rate limit (HTTP 429) retries are exhausted."""


class AgnesClient:
    """HTTP Client for communicating with Agnes AI endpoints."""

    def __init__(self, config: PipelineConfig, session: Optional[requests.Session] = None) -> None:
        self.config = config
        self.session = session or requests.Session()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "video-gen-agnes/0.1.0",
        }

    def _post_with_retry(self, endpoint_path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a POST request with exponential backoff on HTTP 429 and transient server errors."""
        url = f"{self.config.base_url}/{endpoint_path.lstrip('/')}"
        retries = 0

        while True:
            try:
                response = self.session.post(
                    url=url,
                    headers=self._headers,
                    json=payload,
                    timeout=self.config.timeout_sec,
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    retries += 1
                    if retries > self.config.max_retries:
                        raise AgnesRateLimitError(
                            status_code=429,
                            message=f"Rate limit exceeded after {self.config.max_retries} retries.",
                        )
                    sleep_time = self._calculate_backoff(retries)
                    logger.warning(
                        "Rate limit (429) encountered. Backing off for %.2f seconds (attempt %d/%d)...",
                        sleep_time,
                        retries,
                        self.config.max_retries,
                    )
                    time.sleep(sleep_time)
                    continue

                if response.status_code >= 500:
                    retries += 1
                    if retries > self.config.max_retries:
                        raise AgnesAPIError(
                            status_code=response.status_code,
                            message=f"Server error {response.status_code} persists after retries: {response.text}",
                        )
                    sleep_time = self._calculate_backoff(retries)
                    logger.warning(
                        "Server error (%d). Retrying in %.2f seconds (attempt %d/%d)...",
                        response.status_code,
                        sleep_time,
                        retries,
                        self.config.max_retries,
                    )
                    time.sleep(sleep_time)
                    continue

                # 4xx client errors (400, 401, 403, 404, etc.) are unrecoverable by retrying
                error_body: dict[str, Any] = {}
                try:
                    error_body = response.json()
                except Exception:
                    pass

                message = error_body.get("error", {}).get("message") or response.text
                raise AgnesAPIError(
                    status_code=response.status_code,
                    message=message,
                    payload=error_body,
                )

            except requests.RequestException as e:
                retries += 1
                if retries > self.config.max_retries:
                    raise AgnesAPIError(
                        status_code=0,
                        message=f"Network communication failed after {self.config.max_retries} retries: {e}",
                    )
                sleep_time = self._calculate_backoff(retries)
                logger.warning(
                    "Network error (%s). Retrying in %.2f seconds (attempt %d/%d)...",
                    e,
                    sleep_time,
                    retries,
                    self.config.max_retries,
                )
                time.sleep(sleep_time)

    def _get_with_retry(self, url: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Send a GET request with exponential backoff on HTTP 429 and transient server errors."""
        retries = 0

        while True:
            try:
                response = self.session.get(
                    url=url,
                    headers=self._headers,
                    params=params,
                    timeout=self.config.timeout_sec,
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    retries += 1
                    if retries > self.config.max_retries:
                        raise AgnesRateLimitError(
                            status_code=429,
                            message=f"Rate limit exceeded after {self.config.max_retries} retries.",
                        )
                    sleep_time = self._calculate_backoff(retries)
                    logger.warning(
                        "Rate limit (429) encountered on GET. Backing off for %.2f seconds (attempt %d/%d)...",
                        sleep_time,
                        retries,
                        self.config.max_retries,
                    )
                    time.sleep(sleep_time)
                    continue

                if response.status_code >= 500:
                    retries += 1
                    if retries > self.config.max_retries:
                        raise AgnesAPIError(
                            status_code=response.status_code,
                            message=f"Server error {response.status_code} persists after retries: {response.text}",
                        )
                    sleep_time = self._calculate_backoff(retries)
                    logger.warning(
                        "Server error (%d) on GET. Retrying in %.2f seconds (attempt %d/%d)...",
                        response.status_code,
                        sleep_time,
                        retries,
                        self.config.max_retries,
                    )
                    time.sleep(sleep_time)
                    continue

                error_body: dict[str, Any] = {}
                try:
                    error_body = response.json()
                except Exception:
                    pass

                message = error_body.get("error", {}).get("message") or response.text
                raise AgnesAPIError(
                    status_code=response.status_code,
                    message=message,
                    payload=error_body,
                )

            except requests.RequestException as e:
                retries += 1
                if retries > self.config.max_retries:
                    raise AgnesAPIError(
                        status_code=0,
                        message=f"Network communication failed after {self.config.max_retries} retries: {e}",
                    )
                sleep_time = self._calculate_backoff(retries)
                logger.warning(
                    "Network error on GET (%s). Retrying in %.2f seconds (attempt %d/%d)...",
                    e,
                    sleep_time,
                    retries,
                    self.config.max_retries,
                )
                time.sleep(sleep_time)

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with full jitter."""
        exponential = self.config.base_backoff_sec * (2 ** (attempt - 1))
        # Add jitter: between 50% and 100% of exponential
        return exponential * (0.5 + random.random() * 0.5)

    def create_chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> str:
        """Call Agnes Chat Completions API with agnes-2.5-flash ($0 promotional pricing)."""
        payload: dict[str, Any] = {
            "model": model or self.config.text_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        data = self._post_with_retry("chat/completions", payload)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as err:
            raise AgnesAPIError(
                status_code=200,
                message="Malformed chat completion response structure",
                payload=data,
            ) from err

    def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        reference_images: Optional[list[str]] = None,
        return_base64: bool = False,
        model: Optional[str] = None,
    ) -> str:
        """Generate an image using agnes-image-2.0-flash ($0 promotional pricing).

        Returns image URL or Base64 string based on parameters.
        """
        payload: dict[str, Any] = {
            "model": model or self.config.image_model,
            "prompt": prompt,
            "size": size or self.config.image_size,
        }

        extra_body: dict[str, Any] = {}
        if return_base64:
            payload["return_base64"] = True
            extra_body["response_format"] = "b64_json"
        else:
            extra_body["response_format"] = "url"

        if reference_images:
            # Per Agnes Image 2.0 Flash doc: image array goes inside extra_body.image
            extra_body["image"] = reference_images

        payload["extra_body"] = extra_body

        data = self._post_with_retry("images/generations", payload)
        try:
            image_item = data["data"][0]
            if return_base64:
                return image_item.get("b64_json") or image_item.get("url", "")
            return image_item.get("url") or image_item.get("b64_json", "")
        except (KeyError, IndexError) as err:
            raise AgnesAPIError(
                status_code=200,
                message="Malformed image generation response structure",
                payload=data,
            ) from err

    def create_video_task(
        self,
        prompt: str,
        mode: str = "text",
        seconds: str = "5",
        size: str = "720P",
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
        first_frame: Optional[str] = None,
        last_frame: Optional[str] = None,
        images: Optional[list[str]] = None,
        audios: Optional[list[str]] = None,
        videos: Optional[list[dict[str, Any]]] = None,
        model: Optional[str] = None,
        extra_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create an asynchronous video generation task via Agnes Video 2.5 API."""
        payload: dict[str, Any] = {
            "model": model or self.config.video_model,
            "prompt": prompt,
            "mode": mode,
            "seconds": str(seconds),
            "size": size,
            "aspect_ratio": aspect_ratio,
        }

        if seed is not None:
            payload["seed"] = seed

        if mode == "keyframe":
            if first_frame:
                payload["first_frame"] = first_frame
            if last_frame:
                payload["last_frame"] = last_frame
        elif mode == "reference":
            if images:
                payload["images"] = images
            if audios:
                payload["audios"] = audios
            if videos:
                payload["videos"] = videos

        if extra_body:
            payload["extra_body"] = extra_body

        data = self._post_with_retry("videos", payload)
        return {
            "id": data.get("id"),
            "task_id": data.get("task_id") or data.get("id"),
            "video_id": data.get("video_id") or data.get("id"),
            "status": data.get("status", "queued"),
        }

    def get_video_task(self, video_id: str, model_name: Optional[str] = None) -> dict[str, Any]:
        """Retrieve video generation task progress and result using GET /agnesapi."""
        base_root = self.config.base_url
        if base_root.endswith("/v1"):
            base_root = base_root[:-3]
        api_url = f"{base_root.rstrip('/')}/agnesapi"

        params = {
            "video_id": video_id,
            "model_name": model_name or self.config.video_model,
        }

        return self._get_with_retry(api_url, params=params)

    def wait_for_video(
        self,
        video_id: str,
        model_name: Optional[str] = None,
        poll_interval: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        status_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Poll the asynchronous video task until completion or failure."""
        interval = poll_interval or self.config.video_poll_interval
        timeout = timeout_seconds or self.config.video_timeout_sec
        start_time = time.time()

        while True:
            info = self.get_video_task(video_id=video_id, model_name=model_name)
            status = info.get("status")

            if status_callback:
                try:
                    status_callback(info)
                except Exception as cb_err:
                    logger.debug("Status callback error: %s", cb_err)

            if status == "completed":
                return info

            if status == "failed":
                err_msg = info.get("error", {}).get("message") if isinstance(info.get("error"), dict) else str(info.get("error"))
                raise AgnesAPIError(
                    status_code=500,
                    message=f"Video generation task failed: {err_msg or 'Unknown error'}",
                    payload=info,
                )

            if time.time() - start_time > timeout:
                raise AgnesAPIError(
                    status_code=408,
                    message=f"Video generation task {video_id} timed out after {timeout} seconds.",
                    payload=info,
                )

            time.sleep(interval)

    def download_video(self, url: str, output_path: str | Path) -> Path:
        """Download a generated video from URL to a local destination file."""
        from pathlib import Path
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with self.session.get(url, stream=True, timeout=self.config.timeout_sec) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        return dest
