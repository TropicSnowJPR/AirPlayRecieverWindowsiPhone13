import socket
import struct
import subprocess
import sys
import threading
import shutil

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QImage, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QWidget


VIDEO_PORT = 8765

HEADER = struct.Struct("<4sIII")
MAGIC = b"AVF1"


class FrameReceiver(QObject):
    frame_received = Signal(QImage)

    def __init__(self, port):
        super().__init__()

        self.port = port
        self.server = None
        self.running = True
        self.ready = threading.Event()

    def start(self):
        thread = threading.Thread(
            target=self.run,
            daemon=True,
        )

        thread.start()

    def run(self):
        self.server = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        self.server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        self.server.bind(
            ("127.0.0.1", self.port)
        )

        self.server.listen(1)

        self.ready.set()

        print(
            f"[viewer] Waiting for airplaya on "
            f"127.0.0.1:{self.port}"
        )

        while self.running:
            try:
                connection, address = self.server.accept()

            except OSError:
                break

            print(
                f"[viewer] airplaya connected from {address}"
            )

            with connection:
                self.receive_frames(connection)

            if self.running:
                print(
                    "[viewer] Video connection closed, "
                    "waiting for reconnect..."
                )

        print("[viewer] Frame receiver stopped")

    def receive_frames(self, connection):
        while self.running:
            header = self.recv_exact(
                connection,
                HEADER.size,
            )

            if not header:
                break

            magic, width, height, length = HEADER.unpack(
                header
            )

            if magic != MAGIC:
                print("[viewer] Invalid frame magic")
                break

            pixels = self.recv_exact(
                connection,
                length,
            )

            if not pixels:
                break

            image = QImage(
                pixels,
                width,
                height,
                width * 4,
                QImage.Format.Format_RGBA8888,
            ).copy()

            self.frame_received.emit(image)

    @staticmethod
    def recv_exact(connection, size):
        data = bytearray()

        while len(data) < size:
            try:
                chunk = connection.recv(
                    size - len(data)
                )

            except OSError:
                return None

            if not chunk:
                return None

            data.extend(chunk)

        return bytes(data)

    def stop(self):
        self.running = False

        if self.server:
            try:
                self.server.close()
            except OSError:
                pass


class IPhoneWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "Julian's Laptop"
        )

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        # Manual phone size.
        self.resize(390, 830)

        self.setMinimumSize(
            260,
            560,
        )

        self.image = None

        # Used for dragging the frameless window.
        self.drag_position = None

    def set_image(self, image):
        self.image = QPixmap.fromImage(image)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

            event.accept()

    def mouseMoveEvent(self, event):
        if (
            self.drag_position is not None
            and event.buttons()
            & Qt.MouseButton.LeftButton
        ):
            self.move(
                event.globalPosition().toPoint()
                - self.drag_position
            )

            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        outer_rect = self.rect().adjusted(
            2,
            2,
            -2,
            -2,
        )

        outer_path = QPainterPath()

        outer_path.addRoundedRect(
            outer_rect,
            42,
            42,
        )

        # Only the rounded phone itself is painted.
        # Everything outside it remains transparent.
        painter.fillPath(
            outer_path,
            Qt.GlobalColor.black,
        )

        painter.save()

        screen_rect = self.rect().adjusted(
            7,
            7,
            -7,
            -7,
        )

        screen_path = QPainterPath()

        screen_path.addRoundedRect(
            screen_rect,
            36,
            36,
        )

        painter.setClipPath(
            screen_path
        )

        if self.image:
            scaled = self.image.scaled(
                screen_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            x = (
                screen_rect.x()
                + (
                    screen_rect.width()
                    - scaled.width()
                ) // 2
            )

            y = (
                screen_rect.y()
                + (
                    screen_rect.height()
                    - scaled.height()
                ) // 2
            )

            painter.drawPixmap(
                x,
                y,
                scaled,
            )

        painter.restore()

        painter.setPen(
            Qt.GlobalColor.darkGray
        )

        painter.setBrush(
            Qt.BrushStyle.NoBrush
        )

        painter.drawPath(
            outer_path
        )

        painter.end()


def start_airplaya():
    airplaya = shutil.which(
        "airplaya"
    )

    if airplaya is None:
        print(
            "Could not find the 'airplaya' command.\n"
            "Make sure it was installed in this Python environment."
        )

        sys.exit(1)

    command = [
        airplaya,

        "--name",
        "My Laptop",

        "--sink",
        "app",

        "--video-port",
        str(VIDEO_PORT),

        "--video-max-side",
        "1920",

        "--resolution",
        "1170x2532",

        "--orientation",
        "portrait",

        "--max-fps",
        "30",
    ]

    print(
        "[airplaya] Starting receiver..."
    )

    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
    )


def main():
    app = QApplication(
        sys.argv
    )

    window = IPhoneWindow()
    window.show()

    receiver = FrameReceiver(
        VIDEO_PORT
    )

    receiver.frame_received.connect(
        window.set_image
    )

    receiver.start()

    # Wait until the TCP server is actually listening.
    if not receiver.ready.wait(
        timeout=5
    ):
        print(
            "[viewer] Failed to start video receiver."
        )

        receiver.stop()
        sys.exit(1)

    airplaya_process = start_airplaya()

    print(
        "[viewer] PySide window is running"
    )

    exit_code = app.exec()

    receiver.stop()

    if airplaya_process.poll() is None:
        airplaya_process.terminate()

        try:
            airplaya_process.wait(
                timeout=3
            )

        except subprocess.TimeoutExpired:
            airplaya_process.kill()

            try:
                airplaya_process.wait(
                    timeout=2
                )
            except subprocess.TimeoutExpired:
                pass

    sys.exit(
        exit_code
    )


if __name__ == "__main__":
    main()