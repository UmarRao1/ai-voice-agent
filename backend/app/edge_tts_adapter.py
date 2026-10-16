import asyncio
import io
import re
import uuid

import av
import edge_tts
from livekit.agents import tts


def _decode_mp3_to_pcm(data: bytes, sample_rate: int) -> list[bytes]:
    """Decode MP3 bytes into mono, signed 16-bit PCM chunks."""
    chunks = []
    with av.open(io.BytesIO(data), format="mp3") as container:
        resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=sample_rate,
        )
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                chunks.append(converted.to_ndarray().tobytes())
        for converted in resampler.resample(None):
            chunks.append(converted.to_ndarray().tobytes())
    return chunks


class EdgeTTS(tts.TTS):
    """Edge TTS adapter for LiveKit Agents."""

    def __init__(
        self,
        voice: str = "en-US-AriaNeural",
        sample_rate: int = 24000,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self.voice = voice

    @property
    def model(self) -> str:
        return "edge-tts"

    @property
    def provider(self) -> str:
        return "microsoft-edge-tts"

    def _voice_for_text(self, text: str) -> str:
        # Select voices for text written in Urdu or Devanagari scripts.
        if re.search(r"[\u0600-\u06FF]", text):
            return "ur-PK-UzmaNeural"
        if re.search(r"[\u0900-\u097F]", text):
            return "hi-IN-SwaraNeural"
        return self.voice

    def synthesize(
        self,
        text: str,
        *,
        conn_options=tts.TTS.synthesize.__kwdefaults__["conn_options"],
    ) -> tts.ChunkedStream:
        return _EdgeChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )


class _EdgeChunkedStream(tts.ChunkedStream):
    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        request_id = str(uuid.uuid4())
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._tts.sample_rate,
            num_channels=1,
            mime_type="audio/pcm",
        )

        voice = self._tts._voice_for_text(self._input_text)
        communicate = edge_tts.Communicate(
            self._input_text,
            voice=voice,
        )

        audio_parts = []
        async for item in communicate.stream():
            if item.get("type") == "audio" and item.get("data"):
                audio_parts.append(item["data"])

        if not audio_parts:
            raise RuntimeError("Edge TTS returned no audio.")

        pcm_chunks = await asyncio.to_thread(
            _decode_mp3_to_pcm,
            b"".join(audio_parts),
            self._tts.sample_rate,
        )

        if not pcm_chunks:
            raise RuntimeError("Edge TTS audio decoding produced no PCM frames.")

        for chunk in pcm_chunks:
            output_emitter.push(chunk)

        output_emitter.end_input()

