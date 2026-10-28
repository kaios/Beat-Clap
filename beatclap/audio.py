"""Microphone capture (Android AudioRecord, sounddevice, or pyaudio) and clap transient detection."""
import collections
import queue
import threading
import time

import numpy as np

from . import device

SPIKE_RATIO = 2.5         # clap when rms > ambient floor * 2.5 (adjustable: "mic sensitivity")
COOLDOWN_S = 0.150        # ignore re-triggers (echoes, reflections) for 150 ms
MIN_FLOOR = 0.0015        # keeps the floor from collapsing to 0 on digitally silent inputs
FLOOR_TAU_S = 0.75        # time constant of the ambient floor tracker
WARMUP_S = 0.25           # initial ambient measurement before detection is armed
VOICE_GUARD_RATIO = 1.2   # while the game is speaking, claps must beat its own voice by this much
SUSTAIN_S = 0.3           # a level held above threshold this long is new ambience, not a clap


def rms(block):
    block = np.asarray(block, dtype=np.float32)
    return float(np.sqrt(np.mean(block * block))) if block.size else 0.0


def hf_rms(block, prev=0.0):
    """RMS of the first difference: a gentle high-pass (+6 dB/octave). A clap's energy is
    broadband and reaches high up, while speech and music sit mostly low, so this is the
    level the detector works on. `prev` is the last sample of the previous block."""
    block = np.asarray(block, dtype=np.float32)
    return rms(np.diff(block, prepend=np.float32(prev))) if block.size else 0.0


class ClapDetector:
    """Feed it one RMS value per audio block; it reports spike onsets.

    A trigger needs rms > floor * SPIKE_RATIO, at least COOLDOWN_S since the last
    trigger, and the level must have dropped back under threshold since then
    (so one long loud sound can't fire repeatedly). The floor only adapts on
    quiet blocks so claps never inflate it, except when the level stays above
    threshold for SUSTAIN_S: no clap lasts that long, so that's the room getting
    louder (background music starting, a fan) and the floor follows it.

    The game's own speech can leak from speakers into the mic, so the detector also
    learns how loud that voice arrives: during a measure window (the spoken word
    preview) it records the peak level and doesn't trigger. During a guard window
    (a spoken syllable) a clap must also exceed VOICE_GUARD_RATIO times the
    smallest of the recent voice peaks; taking the smallest discards previews
    the player clapped over.
    """

    def __init__(self, ratio=SPIKE_RATIO, cooldown_s=COOLDOWN_S, min_floor=MIN_FLOOR,
                 tau_s=FLOOR_TAU_S, warmup_s=WARMUP_S):
        self.ratio = ratio
        self.cooldown_s = cooldown_s
        self.min_floor = min_floor
        self.tau_s = tau_s
        self.warmup_s = warmup_s
        self.floor = 0.0
        self.level = 0.0
        self._warm_elapsed = 0.0
        self._warm_sum = 0.0
        self._warm_n = 0
        self._last_trigger = float("-inf")
        self._armed = True
        self._above_since = None
        self._rewarm_request = None
        # Written from the game thread, read in the audio thread (plain float swaps).
        self.measure_from = self.measure_until = float("-inf")
        self.guard_from = self.guard_until = float("-inf")
        self._measure_peak = 0.0
        self.voice_peaks = collections.deque(maxlen=3)

    @property
    def ready(self):
        return self._warm_elapsed >= self.warmup_s

    @property
    def threshold(self):
        return max(self.floor, self.min_floor) * self.ratio

    @property
    def voice_threshold(self):
        return min(self.voice_peaks) * VOICE_GUARD_RATIO if self.voice_peaks else 0.0

    def measure_voice(self, start, end):
        self.measure_from, self.measure_until = start, end

    def guard_voice(self, start, end):
        self.guard_from, self.guard_until = start, end

    def rewarm(self, seconds=1.0):
        """Re-measure the ambient floor from scratch, e.g. when background music starts.
        Applied by the audio thread on its next block so the reset never races it."""
        self._rewarm_request = seconds

    def process(self, level, t, block_s):
        self.level = level
        if self._rewarm_request is not None:
            self.warmup_s, self._rewarm_request = self._rewarm_request, None
            self._warm_elapsed, self._warm_sum, self._warm_n = 0.0, 0.0, 0
            self._above_since = None
        if not self.ready:
            self._warm_elapsed += block_s
            self._warm_sum += level
            self._warm_n += 1
            self.floor = self._warm_sum / self._warm_n
            return False
        if self.measure_from <= t < self.measure_until:
            self._measure_peak = max(self._measure_peak, level)
            return False
        if self._measure_peak and t >= self.measure_until:
            self.voice_peaks.append(self._measure_peak)
            self._measure_peak = 0.0
        threshold = self.threshold
        guarded = self.guard_from <= t < self.guard_until
        if guarded:
            threshold = max(threshold, self.voice_threshold)
        if level > threshold:
            if self._above_since is None:
                self._above_since = t
            if not guarded and t - self._above_since >= SUSTAIN_S:
                self.floor += min(1.0, block_s / self.tau_s) * (level - self.floor)
            if self._armed and t - self._last_trigger >= self.cooldown_s:
                self._last_trigger = t
                self._armed = False
                return True
            return False
        self._armed = True
        self._above_since = None
        if not guarded:  # the game's own voice isn't room ambience
            self.floor += min(1.0, block_s / self.tau_s) * (level - self.floor)
        return False


class MicListener:
    """Streams mic blocks into a ring buffer and pushes clap times (perf_counter seconds) to `claps`."""

    def __init__(self, device=None, samplerate=48000, blocksize=256, buffer_s=1.0):
        self.device = device
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.detector = ClapDetector()
        self.claps = queue.SimpleQueue()
        self.buffer = collections.deque(maxlen=max(1, int(buffer_s * samplerate / blocksize)))
        # (peak time, level) per block over the last ~12 s, for the mic check screen
        self.history = collections.deque(maxlen=int(12 * samplerate / blocksize))
        self._prev_sample = 0.0
        self.backend = None
        self.device_name = ""
        self.error = None
        self._stream = None
        self._pa = None
        self._thread = None
        self._running = False

    def start(self):
        errors = []
        starters = (self._start_android,) if device.ON_ANDROID else (self._start_sounddevice,
                                                                      self._start_pyaudio)
        for starter in starters:
            try:
                starter()
                return True
            except Exception as e:  # missing module, no device, permission denied...
                errors.append(f"{starter.__name__[7:]}: {e}")
        self.error = "; ".join(errors)
        return False

    def stop(self):
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._pa is not None:
            self._pa.terminate()

    def _ingest(self, mono, block_start):
        """Common path for both backends. mono: float32 in [-1, 1]; block_start: perf_counter of sample 0."""
        self.buffer.append(mono.copy())
        n = len(mono)
        level = hf_rms(mono, self._prev_sample)
        self._prev_sample = float(mono[-1]) if n else self._prev_sample
        # Refine timing to the loudest sample inside the block.
        peak_t = block_start + int(np.argmax(np.abs(mono))) / self.samplerate if n else block_start
        self.history.append((peak_t, level))
        if self.detector.process(level, block_start, n / self.samplerate):
            self.claps.put(peak_t)

    def _start_android(self):
        """AudioRecord through pyjnius. Opening waits for the RECORD_AUDIO permission, so it
        runs on the reader thread; `backend` is set once audio is actually flowing."""
        from android.permissions import Permission, check_permission, request_permissions
        from jnius import autoclass, detach

        self.samplerate = 44100  # the one rate every Android device must support
        if not check_permission(Permission.RECORD_AUDIO):
            request_permissions([Permission.RECORD_AUDIO])

        def reader():
            try:
                while self._running and not check_permission(Permission.RECORD_AUDIO):
                    time.sleep(0.25)
                if not self._running:
                    return
                AudioRecord = autoclass("android.media.AudioRecord")
                AudioFormat = autoclass("android.media.AudioFormat")
                Source = autoclass("android.media.MediaRecorder$AudioSource")
                mono, pcm16 = AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
                size = max(AudioRecord.getMinBufferSize(self.samplerate, mono, pcm16),
                           self.blocksize * 2 * 8)
                rec = None
                # UNPROCESSED / VOICE_RECOGNITION skip the gain control and noise suppression
                # that the plain MIC source applies, which squash short sharp sounds like claps.
                for source in (Source.UNPROCESSED, Source.VOICE_RECOGNITION, Source.MIC):
                    try:
                        r = AudioRecord(source, self.samplerate, mono, pcm16, size)
                        if r.getState() == AudioRecord.STATE_INITIALIZED:
                            rec = r
                            break
                        r.release()
                    except Exception:
                        pass
                if rec is None:
                    self.error = "could not open the microphone"
                    return
                rec.startRecording()
                self.backend, self.device_name = "android", "Microphone"
                latency = size / 2 / self.samplerate / 2  # rough; the mic check calibrates the rest
                buf = bytearray(self.blocksize * 2)
                while self._running:
                    n = rec.read(buf, 0, len(buf))  # pyjnius copies the Java byte[] back into buf
                    now = time.perf_counter()
                    if n > 0:
                        mono_block = np.frombuffer(bytes(buf[:n]), dtype="<i2").astype(np.float32) / 32768.0
                        self._ingest(mono_block, now - latency - len(mono_block) / self.samplerate)
                rec.stop()
                rec.release()
            finally:
                detach()

        self._running = True
        self._thread = threading.Thread(target=reader, name="mic-reader", daemon=True)
        self._thread.start()

    def _start_sounddevice(self):
        import sounddevice as sd

        def callback(indata, frames, tinfo, status):
            now = time.perf_counter()
            adc, cur = tinfo.inputBufferAdcTime, tinfo.currentTime
            if adc and cur:
                start = now - (cur - adc)
            else:  # some host APIs report zero timestamps
                start = now - latency[0] - frames / self.samplerate
            self._ingest(indata[:, 0], start)

        latency = [0.0]
        stream = sd.InputStream(samplerate=self.samplerate, blocksize=self.blocksize,
                                channels=1, dtype="float32", device=self.device,
                                latency="low", callback=callback)
        latency[0] = float(stream.latency)
        stream.start()
        self._stream = stream
        self.backend = "sounddevice"
        self.device_name = sd.query_devices(stream.device)["name"]

    def _start_pyaudio(self):
        import pyaudio

        pa = pyaudio.PyAudio()
        try:
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=self.samplerate,
                             input=True, frames_per_buffer=self.blocksize,
                             input_device_index=self.device)
        except Exception:
            pa.terminate()
            raise
        latency = stream.get_input_latency()
        info = (pa.get_device_info_by_index(self.device) if self.device is not None
                else pa.get_default_input_device_info())

        def reader():
            while self._running:
                data = stream.read(self.blocksize, exception_on_overflow=False)
                now = time.perf_counter()
                mono = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                self._ingest(mono, now - latency - len(mono) / self.samplerate)
            stream.stop_stream()
            stream.close()

        self._pa = pa
        self._running = True
        self._thread = threading.Thread(target=reader, name="mic-reader", daemon=True)
        self._thread.start()
        self.backend = "pyaudio"
        self.device_name = info["name"]


def list_devices():
    try:
        import sounddevice as sd
        return str(sd.query_devices())
    except ImportError:
        pass
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        lines = []
        for i in range(pa.get_device_count()):
            d = pa.get_device_info_by_index(i)
            if d["maxInputChannels"] > 0:
                lines.append(f"{i:3d} {d['name']} ({d['maxInputChannels']} in)")
        pa.terminate()
        return "\n".join(lines)
    except ImportError:
        return "Neither sounddevice nor pyaudio is installed."
