import asyncio
import logging
import sys
from enum import Enum

logger = logging.getLogger("media_pipeline_win")
logger.setLevel(logging.INFO)

try:
    import gi
    gi.require_version("Gst", "1.0")
    gi.require_version("GstBase", "1.0")
    gi.require_version("GstVideo", "1.0")
    from gi.repository import Gst, GLib, GstBase, GstVideo
    Gst.init(None)
    GST_AVAILABLE = True
except (ImportError, ValueError):
    GST_AVAILABLE = False
    logger.warning("GStreamer Python bindings (gi) not available. Windows media pipeline will not work.")

from .media_pipeline import MediaPipeline, RateControlMode

class MediaPipelineGStreamer(MediaPipeline):
    def __init__(
        self,
        async_event_loop: asyncio.AbstractEventLoop,
        encoder: str = "nvh264enc",
        framerate: int = 30,
        video_bitrate: int = 8,
        audio_bitrate: int = 128000,
        width: int = 1920,
        height: int = 1080,
        audio_channels: int = 2,
        audio_enabled: bool = True,
        audio_device_name: str = "",
        crf: int = 23,
        rc_mode: RateControlMode = RateControlMode.CBR,
    ):
        if not GST_AVAILABLE:
            raise RuntimeError("GStreamer not available on this system")

        super().__init__()

        self.async_event_loop = async_event_loop
        self.encoder = encoder
        self.framerate = framerate
        self.video_bitrate = video_bitrate
        self.audio_bitrate = audio_bitrate
        self.width = width
        self.height = height
        self.audio_channels = audio_channels
        self.audio_enabled = audio_enabled
        self.audio_device_name = audio_device_name
        self.crf = crf
        self.rc_mode = rc_mode

        self._running = False
        self._video_pipeline = None
        self._audio_pipeline = None
        self._video_bus = None
        self._audio_bus = None
        self._video_appsrc = None
        self._audio_appsrc = None
        self._video_need_data_id = None
        self._audio_need_data_id = None
        self._video_enough_data_id = None
        self._audio_enough_data_id = None
        self._frame_count = 0

        self.produce_data = lambda buf, pts, kind: logger.warning("unhandled produce_data")
        self.send_data_channel_message = lambda msg: logger.warning("unhandled send_data_channel_message")

        self._capture_cursor = False
        self._last_resize_success = True

    async def set_pointer_visible(self, visible: bool):
        self._capture_cursor = visible
        logger.info(f"Set pointer visibility to: {visible}")

    async def set_framerate(self, framerate: int):
        if framerate <= 0 or self.framerate == framerate:
            return
        self.framerate = framerate
        logger.info(f"Updated framerate to: {self.framerate}")

    async def set_video_bitrate(self, bitrate: int):
        if bitrate <= 0 or self.video_bitrate == bitrate:
            return
        self.video_bitrate = bitrate
        if self._video_pipeline:
            enc = self._video_pipeline.get_by_name("encoder")
            if enc:
                enc.set_property("bitrate", bitrate * 1000)
                logger.info(f"Updated video bitrate: {bitrate}Mbps")

    async def set_audio_bitrate(self, bitrate: int):
        if bitrate <= 0 or self.audio_bitrate == bitrate:
            return
        self.audio_bitrate = bitrate
        if self._audio_pipeline:
            enc = self._audio_pipeline.get_by_name("opusenc")
            if enc:
                enc.set_property("bitrate", bitrate)
                logger.info(f"Updated audio bitrate: {bitrate}")

    async def dynamic_idr_frame(self):
        logger.info("IDR frame requested (not directly supported in GStreamer pipeline)")

    async def update_rate_control_mode(self, mode: RateControlMode):
        self.rc_mode = mode
        logger.info(f"Updated rate control mode to: {self.rc_mode}")

    async def set_crf(self, crf: int):
        self.crf = crf
        logger.info(f"Updated CRF to: {self.crf}")

    def _build_video_pipeline(self):
        if self.encoder == "nvh264enc":
            pipeline_str = (
                "d3d11screencapturesrc name=screencap "
                f"crop-width={self.width} crop-height={self.height} "
                f"show-cursor={'true' if self._capture_cursor else 'false'} ! "
                "d3d11download ! "
                "videoconvert ! "
                "video/x-raw,format=NV12 ! "
                "nvh264enc name=encoder "
                f"bitrate={self.video_bitrate * 1000} "
                "preset=low-latency "
                "zerolatency=true "
                "rc-mode=cbr "
                "aud=true ! "
                "h264parse config-interval=-1 ! "
                "appsink name=videoout emit-signals=false"
            )
        elif self.encoder == "x264enc":
            pipeline_str = (
                "d3d11screencapturesrc name=screencap "
                f"crop-width={self.width} crop-height={self.height} "
                f"show-cursor={'true' if self._capture_cursor else 'false'} ! "
                "d3d11download ! "
                "videoconvert ! "
                "x264enc name=encoder "
                f"bitrate={self.video_bitrate * 1000} "
                "tune=zerolatency "
                "speed-preset=ultrafast "
                "key-int-max=60 ! "
                "h264parse config-interval=-1 ! "
                "appsink name=videoout emit-signals=false"
            )
        else:
            raise MediaPipelineError(f"Unsupported encoder: {self.encoder}")

        return pipeline_str

    def _build_audio_pipeline(self):
        device_prop = ""
        if self.audio_device_name:
            device_prop = f"device={self.audio_device_name} "

        pipeline_str = (
            "wasapisrc name=audiosrc "
            f"{device_prop}"
            "low-latency=true "
            "loopback=true "
            "buffer-time=20000 "
            "latency-time=5000 ! "
            "audioconvert ! "
            "audioresample ! "
            "audio/x-raw,format=S16LE,rate=48000,channels=2 ! "
            "opusenc name=opusenc "
            f"bitrate={self.audio_bitrate} "
            "frame-size=10 "
            "bandwidth=fullband "
            "complexity=5 ! "
            "appsink name=audioout emit-signals=false"
        )
        return pipeline_str

    def _on_video_new_sample(self, appsink):
        sample = appsink.emit("pull-sample")
        if not sample:
            return Gst.FlowReturn.OK

        buffer = sample.get_buffer()
        if not buffer or buffer.get_size() == 0:
            return Gst.FlowReturn.OK

        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            return Gst.FlowReturn.OK

        try:
            data = bytes(map_info.data)
            pts = buffer.pts
            if pts == Gst.CLOCK_TIME_NONE:
                pts = 0

            asyncio.run_coroutine_threadsafe(
                self.produce_data(data, pts, "video"),
                self.async_event_loop,
            )
        finally:
            buffer.unmap(map_info)

        return Gst.FlowReturn.OK

    def _on_audio_new_sample(self, appsink):
        sample = appsink.emit("pull-sample")
        if not sample:
            return Gst.FlowReturn.OK

        buffer = sample.get_buffer()
        if not buffer or buffer.get_size() == 0:
            return Gst.FlowReturn.OK

        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            return Gst.FlowReturn.OK

        try:
            data = bytes(map_info.data)
            pts = buffer.pts
            if pts == Gst.CLOCK_TIME_NONE:
                pts = 0

            asyncio.run_coroutine_threadsafe(
                self.produce_data(data, pts, "audio"),
                self.async_event_loop,
            )
        finally:
            buffer.unmap(map_info)

        return Gst.FlowReturn.OK

    def _on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"GStreamer bus error: {err.message} - {debug}")
        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"GStreamer bus warning: {warn.message}")
        elif t == Gst.MessageType.EOS:
            logger.info("GStreamer pipeline received EOS")
        elif t == Gst.MessageType.STATE_CHANGED:
            if isinstance(message.src, Gst.Pipeline):
                old, new, pending = message.parse_state_changed()
                logger.debug(f"Pipeline state: {old} -> {new}")

    async def start_media_pipeline(self):
        if self._running:
            return

        logger.info("Starting Windows GStreamer media pipeline...")

        try:
            video_str = self._build_video_pipeline()
            self._video_pipeline = Gst.parse_launch(video_str)
            self._video_bus = self._video_pipeline.get_bus()
            self._video_bus.add_signal_watch()

            appsink = self._video_pipeline.get_by_name("videoout")
            if appsink:
                appsink.set_property("emit-signals", True)
                appsink.set_property("sync", False)
                appsink.set_property("max-buffers", 1)
                appsink.set_property("drop", True)
                appsink.set_property("caps", Gst.Caps.from_string("video/x-h264,stream-format=byte-stream,alignment=au"))
                appsink.connect("new-sample", self._on_video_new_sample)

            ret = self._video_pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error("Failed to start video pipeline")
                self._video_pipeline = None
                return

            if self.audio_enabled:
                try:
                    audio_str = self._build_audio_pipeline()
                    self._audio_pipeline = Gst.parse_launch(audio_str)
                    self._audio_bus = self._audio_pipeline.get_bus()
                    self._audio_bus.add_signal_watch()

                    audio_sink = self._audio_pipeline.get_by_name("audioout")
                    if audio_sink:
                        audio_sink.set_property("emit-signals", True)
                        audio_sink.set_property("sync", False)
                        audio_sink.set_property("max-buffers", 1)
                        audio_sink.set_property("drop", True)
                        audio_sink.set_property("caps", Gst.Caps.from_string("audio/x-opus"))
                        audio_sink.connect("new-sample", self._on_audio_new_sample)

                    ret = self._audio_pipeline.set_state(Gst.State.PLAYING)
                    if ret == Gst.StateChangeReturn.FAILURE:
                        logger.error("Failed to start audio pipeline, continuing without audio")
                        if self._audio_pipeline:
                            self._audio_pipeline.set_state(Gst.State.NULL)
                            self._audio_pipeline = None
                        self._audio_bus = None
                    else:
                        logger.info("Audio pipeline started successfully")
                except Exception as audio_err:
                    logger.error(f"Failed to start audio pipeline, continuing without audio: {audio_err}")
                    if self._audio_pipeline:
                        try: self._audio_pipeline.set_state(Gst.State.NULL)
                        except: pass
                        self._audio_pipeline = None
                    self._audio_bus = None

            self._running = True
            logger.info("Windows GStreamer media pipeline started successfully")

        except Exception as e:
            logger.error(f"Failed to start media pipeline: {e}", exc_info=True)
            await self.stop_media_pipeline()

    async def stop_media_pipeline(self):
        if not self._running:
            return

        logger.info("Stopping Windows GStreamer media pipeline...")

        if self._video_pipeline:
            self._video_pipeline.set_state(Gst.State.NULL)
            if self._video_bus:
                self._video_bus.remove_signal_watch()
            self._video_pipeline = None
            self._video_bus = None

        if self._audio_pipeline:
            self._audio_pipeline.set_state(Gst.State.NULL)
            if self._audio_bus:
                self._audio_bus.remove_signal_watch()
            self._audio_pipeline = None
            self._audio_bus = None

        self._running = False
        logger.info("Windows GStreamer media pipeline stopped")

    def is_media_pipeline_running(self):
        return self._running
