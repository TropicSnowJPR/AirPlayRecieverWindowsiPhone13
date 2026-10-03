# iPhone AirPlay Viewer

A small Windows application that receives an iPhone screen via AirPlay and displays it in a frameless, phone-shaped PySide6 window.

The project is mainly designed around the **iPhone 13** and its `1170x2532` portrait resolution.

## Requirements

- Windows
- Python 3
- PySide6
- [airplaya](https://github.com/King5upah/airplaya)

Install the Python dependency with:

```bash
pip install PySide6
```

Install `airplaya` according to its documentation:

https://github.com/King5upah/airplaya

## Usage

Run the Python application:

```bash
python main.py
```

Then start **Screen Mirroring** on the iPhone and select:

```text
My Laptop
```

The application starts `airplaya` automatically and receives the video frames through a local TCP connection on port `8765`.

## Device Support

The receiver can work with Apple devices that support AirPlay screen mirroring.

However, the display configuration is currently optimized for the **iPhone 13**:

```text
Resolution: 1170x2532
Orientation: Portrait
Maximum FPS: 30
```

Other iPhone and iPad models may work, but their screen can be incorrectly scaled, positioned, or cropped because the current viewer uses a fixed phone size and resolution.

## How It Works

The application consists of two main parts:

- **airplaya** handles the AirPlay receiver functionality.
- **PySide6** receives the decoded frames and displays them in a custom phone-shaped window.

The video frames are transferred locally to:

```text
127.0.0.1:8765
```

The viewer then converts the received RGBA frames into `QImage` objects and renders them inside the window.

## Notes

This is currently a small experimental project rather than a complete AirPlay receiver implementation. Device-specific scaling and aspect-ratio handling may need further work for other Apple devices.